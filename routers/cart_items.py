"""
routers/cart_items.py
---------------------
CART_ITEMS entity'sinin endpoint'leri. Sepete kurs ekleme/çıkarma.

Uygulanan iş kuralları (BİZ FR7):
  - [R-user] user_id mevcut olmalı                          -> 400
  - [R-course] course_id mevcut olmalı                      -> 400
  - Lazy sepet: kullanıcının sepeti yoksa eklemede otomatik oluşturulur (acc1/acc2)
  - [R-dup] aynı kurs aynı sepette iki kez bulunamaz        -> 409 (acc3)
  - [R3] olmayan id istenirse 404
  - Sepetten çıkarma = KALICI silme (acc6; Excel'de deleted_date yok)
  - Özet (FR7 acc5): kurs adı + fiyat + toplam tutar

ERTELENEN:
  - [acc4] zaten satın alınmış kurs sepete eklenemez -> ORDER_ITEMS gelince bağlanır.
"""

import sqlite3

from fastapi import APIRouter, HTTPException, status

from database import get_connection
from models.cart_item import (
    CartItemCreate,
    CartItemResponse,
    CartSummary,
    CartSummaryItem,
)
from routers.carts import sepet_getir_veya_olustur
from routers.order_items import kurs_satin_alindi_mi

router = APIRouter(prefix="/cart-items", tags=["Cart Items"])


def _satiri_cevir(row: sqlite3.Row) -> CartItemResponse:
    return CartItemResponse(
        id=row["id"],
        cart_id=row["cart_id"],
        course_id=row["course_id"],
        created_date=row["created_date"],
    )


def _user_var_mi(cursor: sqlite3.Cursor, user_id: int) -> bool:
    return cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is not None


def _course_var_mi(cursor: sqlite3.Cursor, course_id: int) -> bool:
    return cursor.execute("SELECT 1 FROM courses WHERE id = ?", (course_id,)).fetchone() is not None


@router.post(
    "",
    response_model=CartItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sepete kurs ekle",
    description=(
        "Kullanıcının sepetine kurs ekler. Kullanıcının sepeti yoksa otomatik "
        "(lazy) oluşturulur (FR7 acc1/acc2).\n\n"
        "**İş kuralları:**\n"
        "- [R-user] `user_id` mevcut olmalı → **400**.\n"
        "- [R-course] `course_id` mevcut olmalı → **400**.\n"
        "- [R-dup] Aynı kurs sepette zaten varsa → **409** (acc3).\n"
        "- [R-owned] Kullanıcı bu kursu zaten satın aldıysa (ödemesi COMPLETED) → "
        "**409** (acc4)."
    ),
    responses={
        201: {"description": "Kurs sepete eklendi."},
        400: {"description": "Geçersiz user_id veya course_id."},
        409: {"description": "Bu kurs sepette zaten var VEYA zaten satın alınmış."},
    },
)
def sepete_ekle(payload: CartItemCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        if not _user_var_mi(cursor, payload.user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.user_id} id'li kullanıcı bulunamadı.",
            )
        if not _course_var_mi(cursor, payload.course_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.course_id} id'li kurs bulunamadı.",
            )

        # [R-owned] (acc4) Zaten satın alınmış (ödeme COMPLETED) kurs sepete eklenemez.
        if kurs_satin_alindi_mi(cursor, payload.user_id, payload.course_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu kursu zaten satın aldınız; sepete eklenemez.",
            )

        # Lazy: kullanıcının sepetini al, yoksa oluştur (commit etmez).
        cart = sepet_getir_veya_olustur(cursor, payload.user_id)
        cart_id = cart["id"]

        # [R-dup] Aynı kurs sepette var mı?
        var = cursor.execute(
            "SELECT 1 FROM cart_items WHERE cart_id = ? AND course_id = ?",
            (cart_id, payload.course_id),
        ).fetchone()
        if var is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu kurs sepette zaten var.",
            )

        cursor.execute(
            "INSERT INTO cart_items (cart_id, course_id) VALUES (?, ?)",
            (cart_id, payload.course_id),
        )
        conn.commit()  # lazy sepet (varsa) + kalem birlikte kalıcı olur

        yeni_id = cursor.lastrowid
        row = cursor.execute("SELECT * FROM cart_items WHERE id = ?", (yeni_id,)).fetchone()
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[CartItemResponse],
    summary="Sepet kalemlerini listele",
    description=(
        "Sepet kalemlerini listeler.\n\n"
        "- `cart_id` → o sepetin kalemleri.\n"
        "- `user_id` → o kullanıcının sepetindeki kalemler."
    ),
)
def kalemleri_listele(cart_id: int | None = None, user_id: int | None = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        kosullar = []
        parametreler: list = []
        if cart_id is not None:
            kosullar.append("cart_id = ?")
            parametreler.append(cart_id)
        if user_id is not None:
            # user_id cart_items'ta yok; kullanıcının sepeti üzerinden filtrele.
            kosullar.append("cart_id IN (SELECT id FROM carts WHERE user_id = ?)")
            parametreler.append(user_id)

        sql = "SELECT * FROM cart_items"
        if kosullar:
            sql += " WHERE " + " AND ".join(kosullar)
        sql += " ORDER BY id"

        rows = cursor.execute(sql, parametreler).fetchall()
        return [_satiri_cevir(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/summary",
    response_model=CartSummary,
    summary="Sepet özeti (kurs adı + fiyat + toplam)",
    description=(
        "Kullanıcının sepetini özetler (FR7 acc5): her kalemde kurs adı ve fiyatı, "
        "ayrıca toplam tutar. Sepet yoksa boş özet döner.\n\n"
        "**İş kuralı:** [R-user] `user_id` mevcut olmalı → **400**."
    ),
    responses={400: {"description": "Geçersiz user_id."}},
)
def sepet_ozeti(user_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if not _user_var_mi(cursor, user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{user_id} id'li kullanıcı bulunamadı.",
            )

        cart = cursor.execute(
            "SELECT id FROM carts WHERE user_id = ?", (user_id,)
        ).fetchone()
        if cart is None:
            # Sepet yok -> boş özet.
            return CartSummary(user_id=user_id, cart_id=None, items=[], item_count=0, total_price=0.0)

        cart_id = cart["id"]
        rows = cursor.execute(
            "SELECT ci.course_id, c.course_name, c.price "
            "FROM cart_items ci JOIN courses c ON ci.course_id = c.id "
            "WHERE ci.cart_id = ? ORDER BY ci.id",
            (cart_id,),
        ).fetchall()

        items = [
            CartSummaryItem(course_id=r["course_id"], course_name=r["course_name"], price=r["price"])
            for r in rows
        ]
        toplam = round(sum(it.price for it in items), 2)
        return CartSummary(
            user_id=user_id,
            cart_id=cart_id,
            items=items,
            item_count=len(items),
            total_price=toplam,
        )
    finally:
        conn.close()


@router.get(
    "/{item_id}",
    response_model=CartItemResponse,
    summary="Tek bir sepet kalemini getir",
    description="Verilen id'ye sahip kalemi döndürür.\n\n**İş kuralı:** [R3] Kalem yoksa **404**.",
    responses={404: {"description": "Sepet kalemi bulunamadı."}},
)
def kalem_getir(item_id: int):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM cart_items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{item_id} id'li sepet kalemi bulunamadı.",
            )
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.delete(
    "/{item_id}",
    response_model=CartItemResponse,
    summary="Sepetten kurs çıkar",
    description=(
        "Sepet kalemini **kalıcı olarak** siler (FR7 acc6; Excel'de soft-delete "
        "kolonu yoktur).\n\n"
        "**İş kuralı:** [R3] Kalem yoksa **404**. (Silinen kalem son hali ile döner.)"
    ),
    responses={404: {"description": "Sepet kalemi bulunamadı."}},
)
def sepetten_cikar(item_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM cart_items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{item_id} id'li sepet kalemi bulunamadı.",
            )
        silinen = _satiri_cevir(row)  # silmeden önce döndürülecek hali sakla
        cursor.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))
        conn.commit()
        return silinen
    finally:
        conn.close()
