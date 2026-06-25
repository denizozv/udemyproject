"""
routers/payments.py
-------------------
PAYMENTS entity'sinin endpoint'leri. Sipariş ödemesi (Order ile 1:1).

Uygulanan iş kuralları (BİZ FR8):
  - [R1] address zorunlu                              -> Pydantic (422) (acc3)
  - [R-order] order_id mevcut olmalı                  -> 400
  - [R-tek] bir Order'a en fazla bir Payment (§3.11)  -> 409
  - [R-method] payment_method_id aktif olmalı (acc2)  -> 400
  - [acc7] yeni ödeme otomatik PENDING başlar
  - [R3] olmayan id istenirse 404
  - Durum değişimi: PATCH /payments/{id}/status (yeni durum aktif olmalı).

ERTELENEN (CHECKOUT / ödeme işleme adımında):
  - acc8-acc11 durum geçişlerinin yan etkileri (sepeti pasife alma, kurs erişimi,
    iade ile erişim kaldırma) -> checkout/erişim akışında ele alınacak.
"""

import sqlite3

from fastapi import APIRouter, HTTPException, status

from database import get_connection
from models.payment import PaymentCreate, PaymentResponse, PaymentStatusChange

router = APIRouter(prefix="/payments", tags=["Payments"])

# FR8 acc7: yeni ödemenin başlangıç durumunun kodu.
BASLANGIC_DURUM_KODU = "PENDING"


def _satiri_cevir(row: sqlite3.Row) -> PaymentResponse:
    return PaymentResponse(
        id=row["id"],
        order_id=row["order_id"],
        payment_method_id=row["payment_method_id"],
        payment_status_id=row["payment_status_id"],
        payment_date=row["payment_date"],
        address=row["address"],
        created_date=row["created_date"],
    )


def _order_var_mi(cursor: sqlite3.Cursor, order_id: int) -> bool:
    return cursor.execute("SELECT 1 FROM orders WHERE id = ?", (order_id,)).fetchone() is not None


def _method_aktif_mi(cursor: sqlite3.Cursor, method_id: int) -> bool:
    return (
        cursor.execute(
            "SELECT 1 FROM payment_methods WHERE id = ? AND is_active = 1", (method_id,)
        ).fetchone()
        is not None
    )


def _status_aktif_mi(cursor: sqlite3.Cursor, status_id: int) -> bool:
    return (
        cursor.execute(
            "SELECT 1 FROM payment_statuses WHERE id = ? AND is_active = 1", (status_id,)
        ).fetchone()
        is not None
    )


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ödeme oluştur (otomatik PENDING)",
    description=(
        "Bir sipariş için ödeme kaydı oluşturur. Durum otomatik **PENDING** "
        "atanır (FR8 acc7); payment_date o ana set edilir.\n\n"
        "**İş kuralları:**\n"
        "- [R1] `address` zorunlu → 422 (acc3).\n"
        "- [R-order] `order_id` mevcut olmalı → **400**.\n"
        "- [R-tek] Siparişin zaten bir ödemesi varsa → **409** (§3.11).\n"
        "- [R-method] `payment_method_id` aktif olmalı → **400** (acc2)."
    ),
    responses={
        201: {"description": "Ödeme oluşturuldu (PENDING)."},
        400: {"description": "Geçersiz order_id / pasif veya geçersiz ödeme yöntemi."},
        409: {"description": "Siparişin zaten bir ödemesi var VEYA aktif 'PENDING' durumu tanımlı değil."},
        422: {"description": "Doğrulama hatası (address boş)."},
    },
)
def odeme_olustur(payload: PaymentCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        if not _order_var_mi(cursor, payload.order_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.order_id} id'li sipariş bulunamadı.",
            )
        # [R-tek] Siparişin zaten ödemesi var mı?
        mevcut = cursor.execute(
            "SELECT id FROM payments WHERE order_id = ?", (payload.order_id,)
        ).fetchone()
        if mevcut is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu siparişin zaten bir ödemesi var.",
            )
        # [R-method]
        if not _method_aktif_mi(cursor, payload.payment_method_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.payment_method_id} id'li aktif bir ödeme yöntemi bulunamadı.",
            )
        # [acc7] Aktif PENDING durumunu bul.
        pending = cursor.execute(
            "SELECT id FROM payment_statuses WHERE lower(code) = lower(?) AND is_active = 1",
            (BASLANGIC_DURUM_KODU,),
        ).fetchone()
        if pending is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Ödeme oluşturulamadı: sistemde aktif '{BASLANGIC_DURUM_KODU}' "
                    "ödeme durumu tanımlı değil. Önce POST /payment-statuses ile ekleyin."
                ),
            )

        try:
            cursor.execute(
                "INSERT INTO payments (order_id, payment_method_id, payment_status_id, payment_date, address) "
                "VALUES (?, ?, ?, datetime('now','localtime'), ?)",
                (payload.order_id, payload.payment_method_id, pending["id"], payload.address),
            )
        except sqlite3.IntegrityError:
            # UNIQUE(order_id) güvenlik ağı.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu siparişin zaten bir ödemesi var.",
            )
        conn.commit()

        yeni_id = cursor.lastrowid
        row = cursor.execute("SELECT * FROM payments WHERE id = ?", (yeni_id,)).fetchone()
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[PaymentResponse],
    summary="Ödemeleri listele",
    description="Ödemeleri listeler. `order_id` verilirse o siparişin ödemesi.",
)
def odemeleri_listele(order_id: int | None = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if order_id is not None:
            rows = cursor.execute(
                "SELECT * FROM payments WHERE order_id = ? ORDER BY id", (order_id,)
            ).fetchall()
        else:
            rows = cursor.execute("SELECT * FROM payments ORDER BY id").fetchall()
        return [_satiri_cevir(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Tek bir ödemeyi getir",
    description="Verilen id'ye sahip ödemeyi döndürür.\n\n**İş kuralı:** [R3] Ödeme yoksa **404**.",
    responses={404: {"description": "Ödeme bulunamadı."}},
)
def odeme_getir(payment_id: int):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{payment_id} id'li ödeme bulunamadı.",
            )
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.patch(
    "/{payment_id}/status",
    response_model=PaymentResponse,
    summary="Ödeme durumunu değiştir",
    description=(
        "Ödemenin durumunu günceller (örn. PENDING → COMPLETED/FAILED/REFUNDED).\n\n"
        "**İş kuralları + yan etkiler (FR8 acc8/9/11):**\n"
        "- [R3] Ödeme yoksa **404**.\n"
        "- [R-status] Yeni `payment_status_id` aktif bir durum olmalı → **400**.\n"
        "- **COMPLETED** olunca kullanıcının sepeti temizlenir ve kurslara erişim "
        "doğar (acc8).\n"
        "- **FAILED** olunca sepet korunur (acc9).\n"
        "- **REFUNDED** olunca ilgili kurslara erişim otomatik kalkar (acc11; erişim "
        "yalnızca COMPLETED'dan türetildiği için)."
    ),
    responses={
        404: {"description": "Ödeme bulunamadı."},
        400: {"description": "Geçersiz/pasif ödeme durumu."},
    },
)
def odeme_durumu_degistir(payment_id: int, payload: PaymentStatusChange):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{payment_id} id'li ödeme bulunamadı.",
            )
        if not _status_aktif_mi(cursor, payload.payment_status_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.payment_status_id} id'li aktif bir ödeme durumu bulunamadı.",
            )
        cursor.execute(
            "UPDATE payments SET payment_status_id = ? WHERE id = ?",
            (payload.payment_status_id, payment_id),
        )

        # FR8 acc8: ödeme COMPLETED'a geçtiyse, siparişi veren kullanıcının sepeti
        # temizlenir. (FAILED'da hiçbir şey yapılmaz -> sepet korunur, acc9.)
        yeni_kod = cursor.execute(
            "SELECT code FROM payment_statuses WHERE id = ?", (payload.payment_status_id,)
        ).fetchone()["code"]
        if yeni_kod.upper() == "COMPLETED":
            cursor.execute(
                "DELETE FROM cart_items WHERE cart_id IN ("
                "  SELECT id FROM carts WHERE user_id = (SELECT user_id FROM orders WHERE id = ?))",
                (row["order_id"],),
            )

        conn.commit()
        guncel = cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()
