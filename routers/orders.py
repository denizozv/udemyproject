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
from models.checkout import CheckoutRequest, CheckoutResult
from models.order import OrderCreate, OrderResponse
from models.order_item import OrderItemResponse
from models.payment import PaymentResponse

router = APIRouter(prefix="/orders", tags=["Orders"])

# Checkout'ta oluşturulan ödemenin başlangıç durum kodu (FR8 acc7).
CHECKOUT_PENDING_CODE = "PENDING"


def _row_to_response(row: sqlite3.Row) -> OrderResponse:
    return OrderResponse(
        id=row["id"],
        user_id=row["user_id"],
        total_price=row["total_price"],
        created_date=row["created_date"],
    )


def _user_exists(cursor: sqlite3.Cursor, user_id: int) -> bool:
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
def create_order(payload: OrderCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if not _user_exists(cursor, payload.user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.user_id} id'li kullanıcı bulunamadı.",
            )
        cursor.execute(
            "INSERT INTO orders (user_id, total_price) VALUES (?, ?)",
            (payload.user_id, payload.total_price),
        )
        conn.commit()
        new_id = cursor.lastrowid
        row = cursor.execute("SELECT * FROM orders WHERE id = ?", (new_id,)).fetchone()
        return _row_to_response(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[OrderResponse],
    summary="Siparişleri listele",
    description="Siparişleri listeler. `user_id` verilirse o kullanıcının siparişleri.",
)
def list_orders(user_id: int | None = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if user_id is not None:
            rows = cursor.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY id", (user_id,)
            ).fetchall()
        else:
            rows = cursor.execute("SELECT * FROM orders ORDER BY id").fetchall()
        return [_row_to_response(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Tek bir siparişi getir",
    description="Verilen id'ye sahip siparişi döndürür.\n\n**İş kuralı:** [R3] Sipariş yoksa **404**.",
    responses={404: {"description": "Sipariş bulunamadı."}},
)
def get_order(order_id: int):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{order_id} id'li sipariş bulunamadı.",
            )
        return _row_to_response(row)
    finally:
        conn.close()


@router.post(
    "/checkout",
    response_model=CheckoutResult,
    status_code=status.HTTP_201_CREATED,
    summary="Checkout — sepeti siparişe dönüştür (FR8)",
    description=(
        "Kullanıcının sepetini tek transaction'da siparişe dönüştürür:\n"
        "1) ORDER oluşturulur, sepetteki her kurs için ORDER_ITEM açılır "
        "(`unit_price` = kursun o anki fiyatı — snapshot, acc5).\n"
        "2) `total_price` = kalemlerin toplamı (acc6).\n"
        "3) PENDING durumunda PAYMENT oluşturulur (acc7).\n"
        "4) Sepet bu aşamada TEMİZLENMEZ; ödeme COMPLETED olunca temizlenir "
        "(acc8), FAILED olursa korunur (acc9).\n\n"
        "**İş kuralları:**\n"
        "- [R1] `address` zorunlu → 422 (acc3).\n"
        "- [R-user] `user_id` mevcut olmalı → **400**.\n"
        "- [R-method] `payment_method_id` aktif olmalı → **400** (acc2).\n"
        "- [R-empty] Sepet yok veya boşsa checkout yapılamaz → **409**.\n"
        "- Aktif 'PENDING' ödeme durumu tanımlı değilse → **409**."
    ),
    responses={
        201: {"description": "Sipariş + kalemler + PENDING ödeme oluşturuldu, sepet temizlendi."},
        400: {"description": "Geçersiz user_id veya pasif/geçersiz ödeme yöntemi."},
        409: {"description": "Sepet boş VEYA aktif 'PENDING' durumu tanımlı değil."},
        422: {"description": "Doğrulama hatası (address boş)."},
    },
)
def checkout(payload: CheckoutRequest):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # [R-user]
        if not _user_exists(cursor, payload.user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.user_id} id'li kullanıcı bulunamadı.",
            )
        # [R-method] aktif ödeme yöntemi
        if cursor.execute(
            "SELECT 1 FROM payment_methods WHERE id = ? AND is_active = 1",
            (payload.payment_method_id,),
        ).fetchone() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.payment_method_id} id'li aktif bir ödeme yöntemi bulunamadı.",
            )
        # Aktif PENDING durumu (acc7)
        pending = cursor.execute(
            "SELECT id FROM payment_statuses WHERE lower(code) = lower(?) AND is_active = 1",
            (CHECKOUT_PENDING_CODE,),
        ).fetchone()
        if pending is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Aktif '{CHECKOUT_PENDING_CODE}' ödeme durumu tanımlı değil.",
            )

        # [R-empty] Kullanıcının sepeti ve kalemleri
        cart = cursor.execute(
            "SELECT id FROM carts WHERE user_id = ?", (payload.user_id,)
        ).fetchone()
        if cart is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Sepet boş; ödeme adımına geçilemez.",
            )
        cart_id = cart["id"]
        items = cursor.execute(
            "SELECT ci.course_id, c.price "
            "FROM cart_items ci JOIN courses c ON ci.course_id = c.id "
            "WHERE ci.cart_id = ? ORDER BY ci.id",
            (cart_id,),
        ).fetchall()
        if not items:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Sepet boş; ödeme adımına geçilemez.",
            )

        # 1) total = kalemlerin güncel fiyat toplamı (acc6)
        total = round(sum(k["price"] for k in items), 2)

        # 2) ORDER
        cursor.execute(
            "INSERT INTO orders (user_id, total_price) VALUES (?, ?)",
            (payload.user_id, total),
        )
        order_id = cursor.lastrowid

        # 3) ORDER_ITEM'lar (fiyat snapshot)
        for k in items:
            cursor.execute(
                "INSERT INTO order_items (order_id, course_id, unit_price) VALUES (?, ?, ?)",
                (order_id, k["course_id"], k["price"]),
            )

        # 4) PAYMENT (PENDING)
        cursor.execute(
            "INSERT INTO payments (order_id, payment_method_id, payment_status_id, payment_date, address) "
            "VALUES (?, ?, ?, datetime('now','localtime'), ?)",
            (order_id, payload.payment_method_id, pending["id"], payload.address),
        )

        # NOT: Sepet checkout'ta TEMİZLENMEZ. FR8 acc8 gereği sepet, ödeme
        # COMPLETED'a geçtiğinde temizlenir; acc9 gereği ödeme FAILED olursa
        # sepet korunur. Bu mantık PATCH /payments/{id}/status içindedir.
        conn.commit()

        # Sonuç: oluşan kayıtları topla
        order_row = cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        item_rows = cursor.execute(
            "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)
        ).fetchall()
        pay_row = cursor.execute(
            "SELECT * FROM payments WHERE order_id = ?", (order_id,)
        ).fetchone()

        return CheckoutResult(
            order=_row_to_response(order_row),
            items=[
                OrderItemResponse(
                    id=r["id"],
                    order_id=r["order_id"],
                    course_id=r["course_id"],
                    unit_price=r["unit_price"],
                    created_date=r["created_date"],
                )
                for r in item_rows
            ],
            payment=PaymentResponse(
                id=pay_row["id"],
                order_id=pay_row["order_id"],
                payment_method_id=pay_row["payment_method_id"],
                payment_status_id=pay_row["payment_status_id"],
                payment_date=pay_row["payment_date"],
                address=pay_row["address"],
                created_date=pay_row["created_date"],
            ),
            item_count=len(item_rows),
            total_price=total,
        )
    finally:
        conn.close()
