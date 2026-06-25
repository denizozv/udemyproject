"""
routers/payment_statuses.py
---------------------------
PAYMENT_STATUSES entity'sinin tüm endpoint'leri.
DIFFICULTY_LEVELS / PAYMENT_METHODS şablonu ile aynı; benzersizlik 'code' üzerinden.

Uygulanan iş kuralları (kaynak notu):
  - [R1] code ve name boş olamaz   -> Pydantic (422)
  - [R2] code benzersiz olmalı     -> mükerrer code'da 409 (FR10 acc5)
  - [R3] olmayan id istenirse 404
  - [R4] (ERTELENDİ) PENDING/COMPLETED bir ödemede kullanılan durum pasife
         alınamaz -> PAYMENTS tablosu eklendiğinde uygulanacak (FR10 acc6).
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from auth_deps import require_role
from database import get_connection
from models.payment_status import (
    PaymentStatusCreate,
    PaymentStatusResponse,
    PaymentStatusUpdate,
)

router = APIRouter(prefix="/payment-statuses", tags=["Payment Statuses"])


def _row_to_response(row: sqlite3.Row) -> PaymentStatusResponse:
    """Veritabanı satırını PaymentStatusResponse'a çevirir; is_active 0/1 -> True/False."""
    return PaymentStatusResponse(
        id=row["id"],
        code=row["code"],
        name=row["name"],
        is_active=bool(row["is_active"]),
        created_date=row["created_date"],
    )


@router.post(
    "",
    dependencies=[Depends(require_role("Admin"))],
    response_model=PaymentStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni ödeme durumu oluştur",
    description=(
        "Yeni bir ödeme durumu kaydı oluşturur.\n\n"
        "**İş kuralları:**\n"
        "- [R1] `code` ve `name` boş olamaz (boşsa 422).\n"
        "- [R2] `code` benzersiz olmalı; aynı kod varsa **409 Conflict** (FR10 acc5)."
    ),
    responses={
        201: {"description": "Ödeme durumu başarıyla oluşturuldu."},
        409: {"description": "Aynı code'a sahip bir kayıt zaten var."},
        422: {"description": "Doğrulama hatası (örn. code/name boş)."},
    },
)
def create_status(payload: PaymentStatusCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        existing = cursor.execute(
            "SELECT id FROM payment_statuses WHERE code = ?", (payload.code,)
        ).fetchone()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{payload.code}' kodlu bir ödeme durumu zaten var.",
            )

        try:
            cursor.execute(
                "INSERT INTO payment_statuses (code, name) VALUES (?, ?)",
                (payload.code, payload.name),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{payload.code}' kodlu bir ödeme durumu zaten var.",
            )
        conn.commit()

        new_id = cursor.lastrowid
        row = cursor.execute(
            "SELECT * FROM payment_statuses WHERE id = ?", (new_id,)
        ).fetchone()
        return _row_to_response(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[PaymentStatusResponse],
    summary="Ödeme durumlarını listele",
    description=(
        "Tüm ödeme durumlarını listeler. `only_active=true` verilirse yalnızca "
        "aktif (is_active=1) kayıtlar döner."
    ),
)
def list_statuses(only_active: bool = False):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if only_active:
            rows = cursor.execute(
                "SELECT * FROM payment_statuses WHERE is_active = 1 ORDER BY id"
            ).fetchall()
        else:
            rows = cursor.execute(
                "SELECT * FROM payment_statuses ORDER BY id"
            ).fetchall()
        return [_row_to_response(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{status_id}",
    response_model=PaymentStatusResponse,
    summary="Tek bir ödeme durumunu getir",
    description="Verilen id'ye sahip kaydı döndürür.\n\n**İş kuralı:** [R3] Kayıt yoksa **404**.",
    responses={404: {"description": "Belirtilen id'li ödeme durumu bulunamadı."}},
)
def get_status(status_id: int):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM payment_statuses WHERE id = ?", (status_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{status_id} id'li ödeme durumu bulunamadı.",
            )
        return _row_to_response(row)
    finally:
        conn.close()


@router.put(
    "/{status_id}",
    dependencies=[Depends(require_role("Admin"))],
    response_model=PaymentStatusResponse,
    summary="Ödeme durumunu güncelle",
    description=(
        "Mevcut bir ödeme durumunun code ve name değerini günceller.\n\n"
        "**İş kuralları:**\n"
        "- [R3] Kayıt yoksa **404**.\n"
        "- [R2] Yeni `code` başka bir kayıtta kullanılıyorsa **409 Conflict**."
    ),
    responses={
        404: {"description": "Güncellenecek kayıt bulunamadı."},
        409: {"description": "Bu code başka bir kayıtta kullanılıyor."},
        422: {"description": "Doğrulama hatası (örn. code/name boş)."},
    },
)
def update_status(status_id: int, payload: PaymentStatusUpdate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        row = cursor.execute(
            "SELECT * FROM payment_statuses WHERE id = ?", (status_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{status_id} id'li ödeme durumu bulunamadı.",
            )

        conflict = cursor.execute(
            "SELECT id FROM payment_statuses WHERE code = ? AND id <> ?",
            (payload.code, status_id),
        ).fetchone()
        if conflict is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{payload.code}' kodu başka bir kayıtta kullanılıyor.",
            )

        cursor.execute(
            "UPDATE payment_statuses SET code = ?, name = ? WHERE id = ?",
            (payload.code, payload.name, status_id),
        )
        conn.commit()

        updated = cursor.execute(
            "SELECT * FROM payment_statuses WHERE id = ?", (status_id,)
        ).fetchone()
        return _row_to_response(updated)
    finally:
        conn.close()


@router.patch(
    "/{status_id}/deactivate",
    dependencies=[Depends(require_role("Admin"))],
    response_model=PaymentStatusResponse,
    summary="Ödeme durumunu pasife al",
    description=(
        "Kaydı silmek yerine **pasife alır** (is_active=0). Lookup kayıtları "
        "silinmez (FR10 acc7).\n\n"
        "**İş kuralı:** [R3] Kayıt yoksa **404**.\n\n"
        "_Not: [R4] 'PENDING/COMPLETED bir ödemede kullanılan durum pasife "
        "alınamaz' kuralı (FR10 acc6) PAYMENTS tablosu eklendiğinde eklenecektir._"
    ),
    responses={404: {"description": "Kayıt bulunamadı."}},
)
def deactivate_status(status_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM payment_statuses WHERE id = ?", (status_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{status_id} id'li ödeme durumu bulunamadı.",
            )
        cursor.execute(
            "UPDATE payment_statuses SET is_active = 0 WHERE id = ?", (status_id,)
        )
        conn.commit()
        updated = cursor.execute(
            "SELECT * FROM payment_statuses WHERE id = ?", (status_id,)
        ).fetchone()
        return _row_to_response(updated)
    finally:
        conn.close()


@router.patch(
    "/{status_id}/activate",
    dependencies=[Depends(require_role("Admin"))],
    response_model=PaymentStatusResponse,
    summary="Ödeme durumunu yeniden aktifleştir",
    description="Pasif bir kaydı tekrar aktif eder (is_active=1).\n\n**İş kuralı:** [R3] Kayıt yoksa **404**.",
    responses={404: {"description": "Kayıt bulunamadı."}},
)
def activate_status(status_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM payment_statuses WHERE id = ?", (status_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{status_id} id'li ödeme durumu bulunamadı.",
            )
        cursor.execute(
            "UPDATE payment_statuses SET is_active = 1 WHERE id = ?", (status_id,)
        )
        conn.commit()
        updated = cursor.execute(
            "SELECT * FROM payment_statuses WHERE id = ?", (status_id,)
        ).fetchone()
        return _row_to_response(updated)
    finally:
        conn.close()
