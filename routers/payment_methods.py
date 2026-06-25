"""
routers/payment_methods.py
--------------------------
PAYMENT_METHODS entity'sinin tüm endpoint'leri.
DIFFICULTY_LEVELS şablonu ile aynı; benzersizlik 'code' üzerinden.

Uygulanan iş kuralları (kaynak notu):
  - [R1] code ve name boş olamaz   -> Pydantic (422)
  - [R2] code benzersiz olmalı     -> mükerrer code'da 409 (FR10 acc5)
  - [R3] olmayan id istenirse 404
  - [R4] (ERTELENDİ) PENDING/COMPLETED bir ödemede kullanılan yöntem pasife
         alınamaz -> PAYMENTS tablosu eklendiğinde uygulanacak (FR10 acc6).
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from auth_deps import rol_gerektir
from database import get_connection
from models.payment_method import (
    PaymentMethodCreate,
    PaymentMethodResponse,
    PaymentMethodUpdate,
)

router = APIRouter(prefix="/payment-methods", tags=["Payment Methods"])


def _satiri_cevir(row: sqlite3.Row) -> PaymentMethodResponse:
    """Veritabanı satırını PaymentMethodResponse'a çevirir; is_active 0/1 -> True/False."""
    return PaymentMethodResponse(
        id=row["id"],
        code=row["code"],
        name=row["name"],
        is_active=bool(row["is_active"]),
        created_date=row["created_date"],
    )


@router.post(
    "",
    dependencies=[Depends(rol_gerektir("Admin"))],
    response_model=PaymentMethodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni ödeme yöntemi oluştur",
    description=(
        "Yeni bir ödeme yöntemi kaydı oluşturur.\n\n"
        "**İş kuralları:**\n"
        "- [R1] `code` ve `name` boş olamaz (boşsa 422).\n"
        "- [R2] `code` benzersiz olmalı; aynı kod varsa **409 Conflict** (FR10 acc5)."
    ),
    responses={
        201: {"description": "Ödeme yöntemi başarıyla oluşturuldu."},
        409: {"description": "Aynı code'a sahip bir kayıt zaten var."},
        422: {"description": "Doğrulama hatası (örn. code/name boş)."},
    },
)
def yontem_olustur(payload: PaymentMethodCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        mevcut = cursor.execute(
            "SELECT id FROM payment_methods WHERE code = ?", (payload.code,)
        ).fetchone()
        if mevcut is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{payload.code}' kodlu bir ödeme yöntemi zaten var.",
            )

        try:
            cursor.execute(
                "INSERT INTO payment_methods (code, name) VALUES (?, ?)",
                (payload.code, payload.name),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{payload.code}' kodlu bir ödeme yöntemi zaten var.",
            )
        conn.commit()

        yeni_id = cursor.lastrowid
        row = cursor.execute(
            "SELECT * FROM payment_methods WHERE id = ?", (yeni_id,)
        ).fetchone()
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[PaymentMethodResponse],
    summary="Ödeme yöntemlerini listele",
    description=(
        "Tüm ödeme yöntemlerini listeler. `only_active=true` verilirse yalnızca "
        "aktif (is_active=1) kayıtlar döner."
    ),
)
def yontemleri_listele(only_active: bool = False):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if only_active:
            rows = cursor.execute(
                "SELECT * FROM payment_methods WHERE is_active = 1 ORDER BY id"
            ).fetchall()
        else:
            rows = cursor.execute(
                "SELECT * FROM payment_methods ORDER BY id"
            ).fetchall()
        return [_satiri_cevir(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{method_id}",
    response_model=PaymentMethodResponse,
    summary="Tek bir ödeme yöntemini getir",
    description="Verilen id'ye sahip kaydı döndürür.\n\n**İş kuralı:** [R3] Kayıt yoksa **404**.",
    responses={404: {"description": "Belirtilen id'li ödeme yöntemi bulunamadı."}},
)
def yontem_getir(method_id: int):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM payment_methods WHERE id = ?", (method_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{method_id} id'li ödeme yöntemi bulunamadı.",
            )
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.put(
    "/{method_id}",
    dependencies=[Depends(rol_gerektir("Admin"))],
    response_model=PaymentMethodResponse,
    summary="Ödeme yöntemini güncelle",
    description=(
        "Mevcut bir ödeme yönteminin code ve name değerini günceller.\n\n"
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
def yontem_guncelle(method_id: int, payload: PaymentMethodUpdate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        row = cursor.execute(
            "SELECT * FROM payment_methods WHERE id = ?", (method_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{method_id} id'li ödeme yöntemi bulunamadı.",
            )

        cakisma = cursor.execute(
            "SELECT id FROM payment_methods WHERE code = ? AND id <> ?",
            (payload.code, method_id),
        ).fetchone()
        if cakisma is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{payload.code}' kodu başka bir kayıtta kullanılıyor.",
            )

        cursor.execute(
            "UPDATE payment_methods SET code = ?, name = ? WHERE id = ?",
            (payload.code, payload.name, method_id),
        )
        conn.commit()

        guncel = cursor.execute(
            "SELECT * FROM payment_methods WHERE id = ?", (method_id,)
        ).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()


@router.patch(
    "/{method_id}/deactivate",
    dependencies=[Depends(rol_gerektir("Admin"))],
    response_model=PaymentMethodResponse,
    summary="Ödeme yöntemini pasife al",
    description=(
        "Kaydı silmek yerine **pasife alır** (is_active=0). Lookup kayıtları "
        "silinmez (FR10 acc7).\n\n"
        "**İş kuralı:** [R3] Kayıt yoksa **404**.\n\n"
        "_Not: [R4] 'PENDING/COMPLETED bir ödemede kullanılan yöntem pasife "
        "alınamaz' kuralı (FR10 acc6) PAYMENTS tablosu eklendiğinde eklenecektir._"
    ),
    responses={404: {"description": "Kayıt bulunamadı."}},
)
def yontem_pasiflestir(method_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM payment_methods WHERE id = ?", (method_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{method_id} id'li ödeme yöntemi bulunamadı.",
            )
        cursor.execute(
            "UPDATE payment_methods SET is_active = 0 WHERE id = ?", (method_id,)
        )
        conn.commit()
        guncel = cursor.execute(
            "SELECT * FROM payment_methods WHERE id = ?", (method_id,)
        ).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()


@router.patch(
    "/{method_id}/activate",
    dependencies=[Depends(rol_gerektir("Admin"))],
    response_model=PaymentMethodResponse,
    summary="Ödeme yöntemini yeniden aktifleştir",
    description="Pasif bir kaydı tekrar aktif eder (is_active=1).\n\n**İş kuralı:** [R3] Kayıt yoksa **404**.",
    responses={404: {"description": "Kayıt bulunamadı."}},
)
def yontem_aktiflestir(method_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM payment_methods WHERE id = ?", (method_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{method_id} id'li ödeme yöntemi bulunamadı.",
            )
        cursor.execute(
            "UPDATE payment_methods SET is_active = 1 WHERE id = ?", (method_id,)
        )
        conn.commit()
        guncel = cursor.execute(
            "SELECT * FROM payment_methods WHERE id = ?", (method_id,)
        ).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()
