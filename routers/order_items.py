"""
routers/order_items.py
----------------------
ORDER_ITEMS entity'sinin endpoint'leri. Sipariş kalemleri (immutable).

Uygulanan iş kuralları (BİZ FR8):
  - [R1] unit_price >= 0                          -> Pydantic (422)
  - [R-order] order_id mevcut olmalı              -> 400
  - [R-course] course_id mevcut olmalı            -> 400
  - [R-dup] aynı kurs aynı siparişte iki kez olamaz (veri bütünlüğü) -> 409
  - [R3] olmayan id istenirse 404
  - Kalem immutable: güncelleme/silme endpoint'i YOKTUR.
"""

import sqlite3

from fastapi import APIRouter, HTTPException, status

from database import get_connection
from models.order_item import OrderItemCreate, OrderItemResponse

router = APIRouter(prefix="/order-items", tags=["Order Items"])


def _satiri_cevir(row: sqlite3.Row) -> OrderItemResponse:
    return OrderItemResponse(
        id=row["id"],
        order_id=row["order_id"],
        course_id=row["course_id"],
        unit_price=row["unit_price"],
        created_date=row["created_date"],
    )


def _order_var_mi(cursor: sqlite3.Cursor, order_id: int) -> bool:
    return cursor.execute("SELECT 1 FROM orders WHERE id = ?", (order_id,)).fetchone() is not None


def _course_var_mi(cursor: sqlite3.Cursor, course_id: int) -> bool:
    return cursor.execute("SELECT 1 FROM courses WHERE id = ?", (course_id,)).fetchone() is not None


def kurs_satin_alindi_mi(cursor: sqlite3.Cursor, user_id: int, course_id: int) -> bool:
    """
    Kullanıcı bu kursu SATIN ALMIŞ mı? (paylaşılan kural — REVIEWS acc2, CART_ITEMS acc4)

    Tanım (analist kararı): Kurs, kullanıcının ödemesi **COMPLETED** olan bir
    siparişinde (ORDER_ITEM) yer alıyorsa satın alınmış sayılır. PENDING/FAILED/
    REFUNDED ödemeler erişim/satın alma saymaz (FR8 acc8/acc10/acc11 ile tutarlı).
    """
    return (
        cursor.execute(
            "SELECT 1 FROM order_items oi "
            "JOIN orders o ON oi.order_id = o.id "
            "JOIN payments p ON p.order_id = o.id "
            "JOIN payment_statuses ps ON p.payment_status_id = ps.id "
            "WHERE o.user_id = ? AND oi.course_id = ? AND lower(ps.code) = 'completed' "
            "LIMIT 1",
            (user_id, course_id),
        ).fetchone()
        is not None
    )


@router.post(
    "",
    response_model=OrderItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sipariş kalemi oluştur (manuel)",
    description=(
        "Bir siparişe kalem ekler (temel CRUD).\n\n"
        "**İş kuralları:**\n"
        "- [R1] `unit_price` >= 0 → 422.\n"
        "- [R-order] `order_id` mevcut olmalı → **400**.\n"
        "- [R-course] `course_id` mevcut olmalı → **400**.\n"
        "- [R-dup] Aynı kurs aynı siparişte zaten varsa → **409**.\n\n"
        "_unit_price kursun sipariş anındaki fiyatını yansıtır (snapshot, FR8 acc5)._"
    ),
    responses={
        201: {"description": "Sipariş kalemi oluşturuldu."},
        400: {"description": "Geçersiz order_id veya course_id."},
        409: {"description": "Bu kurs bu siparişte zaten var."},
        422: {"description": "Doğrulama hatası (unit_price < 0)."},
    },
)
def kalem_olustur(payload: OrderItemCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if not _order_var_mi(cursor, payload.order_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.order_id} id'li sipariş bulunamadı.",
            )
        if not _course_var_mi(cursor, payload.course_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.course_id} id'li kurs bulunamadı.",
            )
        var = cursor.execute(
            "SELECT 1 FROM order_items WHERE order_id = ? AND course_id = ?",
            (payload.order_id, payload.course_id),
        ).fetchone()
        if var is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu kurs bu siparişte zaten var.",
            )

        cursor.execute(
            "INSERT INTO order_items (order_id, course_id, unit_price) VALUES (?, ?, ?)",
            (payload.order_id, payload.course_id, payload.unit_price),
        )
        conn.commit()
        yeni_id = cursor.lastrowid
        row = cursor.execute("SELECT * FROM order_items WHERE id = ?", (yeni_id,)).fetchone()
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[OrderItemResponse],
    summary="Sipariş kalemlerini listele",
    description="Sipariş kalemlerini listeler. `order_id` / `course_id` ile filtrelenebilir.",
)
def kalemleri_listele(order_id: int | None = None, course_id: int | None = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        kosullar = []
        parametreler: list = []
        if order_id is not None:
            kosullar.append("order_id = ?")
            parametreler.append(order_id)
        if course_id is not None:
            kosullar.append("course_id = ?")
            parametreler.append(course_id)

        sql = "SELECT * FROM order_items"
        if kosullar:
            sql += " WHERE " + " AND ".join(kosullar)
        sql += " ORDER BY id"

        rows = cursor.execute(sql, parametreler).fetchall()
        return [_satiri_cevir(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{item_id}",
    response_model=OrderItemResponse,
    summary="Tek bir sipariş kalemini getir",
    description="Verilen id'ye sahip kalemi döndürür.\n\n**İş kuralı:** [R3] Kalem yoksa **404**.",
    responses={404: {"description": "Sipariş kalemi bulunamadı."}},
)
def kalem_getir(item_id: int):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM order_items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{item_id} id'li sipariş kalemi bulunamadı.",
            )
        return _satiri_cevir(row)
    finally:
        conn.close()
