"""
routers/orders.py
-----------------
ORDERS entity'sinin endpoint'leri. Kesinleşmiş sipariş (immutable).

Uygulanan iş kuralları (BİZ FR8):
  - [R1] total_price >= 0          -> Pydantic (422)
  - [R-user] user_id mevcut olmalı -> 400
  - [R3] olmayan id istenirse 404
  - Sipariş immutable: güncelleme/silme endpoint'i YOKTUR.

ERTELENEN (CHECKOUT adımında uygulanacak):
  - [acc6] total_price = OrderItem'ların unit_price toplamı.
  - "En az bir kalem" (boş sipariş yok). Bunlar sepetten checkout sırasında
    garanti edilecektir; manuel oluşturmada kontrol edilmez.
"""

import sqlite3

from fastapi import APIRouter, HTTPException, status

from database import get_connection
from models.order import OrderCreate, OrderResponse

router = APIRouter(prefix="/orders", tags=["Orders"])


def _satiri_cevir(row: sqlite3.Row) -> OrderResponse:
    return OrderResponse(
        id=row["id"],
        user_id=row["user_id"],
        total_price=row["total_price"],
        created_date=row["created_date"],
    )


def _user_var_mi(cursor: sqlite3.Cursor, user_id: int) -> bool:
    return cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is not None


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sipariş oluştur (manuel)",
    description=(
        "Bir sipariş kaydı oluşturur (temel CRUD).\n\n"
        "**İş kuralları:**\n"
        "- [R1] `total_price` >= 0 → 422.\n"
        "- [R-user] `user_id` mevcut olmalı → **400**.\n\n"
        "_Not: Gerçek siparişler CHECKOUT akışıyla üretilir; tutar/kalem tutarlılığı "
        "(FR8 acc6) orada garanti edilir._"
    ),
    responses={
        201: {"description": "Sipariş oluşturuldu."},
        400: {"description": "Geçersiz user_id."},
        422: {"description": "Doğrulama hatası (total_price < 0)."},
    },
)
def siparis_olustur(payload: OrderCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if not _user_var_mi(cursor, payload.user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.user_id} id'li kullanıcı bulunamadı.",
            )
        cursor.execute(
            "INSERT INTO orders (user_id, total_price) VALUES (?, ?)",
            (payload.user_id, payload.total_price),
        )
        conn.commit()
        yeni_id = cursor.lastrowid
        row = cursor.execute("SELECT * FROM orders WHERE id = ?", (yeni_id,)).fetchone()
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[OrderResponse],
    summary="Siparişleri listele",
    description="Siparişleri listeler. `user_id` verilirse o kullanıcının siparişleri.",
)
def siparisleri_listele(user_id: int | None = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if user_id is not None:
            rows = cursor.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY id", (user_id,)
            ).fetchall()
        else:
            rows = cursor.execute("SELECT * FROM orders ORDER BY id").fetchall()
        return [_satiri_cevir(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Tek bir siparişi getir",
    description="Verilen id'ye sahip siparişi döndürür.\n\n**İş kuralı:** [R3] Sipariş yoksa **404**.",
    responses={404: {"description": "Sipariş bulunamadı."}},
)
def siparis_getir(order_id: int):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{order_id} id'li sipariş bulunamadı.",
            )
        return _satiri_cevir(row)
    finally:
        conn.close()
