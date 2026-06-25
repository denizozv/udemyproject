"""
routers/difficulty_levels.py
----------------------------
DIFFICULTY_LEVELS entity'sinin tüm endpoint'leri.
ROLES/LANGUAGES şablonu; farkı: benzersizlik 'code' üzerinden kontrol edilir.

Uygulanan iş kuralları (kaynak notu):
  - [R1] code ve name boş olamaz   -> Pydantic (422)
  - [R2] code benzersiz olmalı     -> mükerrer code'da 409 (FR10 acc5)
  - [R3] olmayan id istenirse 404
  - [R4] (ERTELENDİ) aktif bir kursta kullanılan seviye pasife alınamaz
         -> COURSES tablosu eklendiğinde uygulanacak (FR10 acc6).
"""

import sqlite3

from fastapi import APIRouter, HTTPException, status

from database import get_connection
from models.difficulty_level import (
    DifficultyLevelCreate,
    DifficultyLevelResponse,
    DifficultyLevelUpdate,
)

router = APIRouter(prefix="/difficulty-levels", tags=["Difficulty Levels"])


def _satiri_cevir(row: sqlite3.Row) -> DifficultyLevelResponse:
    """Veritabanı satırını DifficultyLevelResponse'a çevirir; is_active 0/1 -> True/False."""
    return DifficultyLevelResponse(
        id=row["id"],
        code=row["code"],
        name=row["name"],
        is_active=bool(row["is_active"]),
        created_date=row["created_date"],
    )


@router.post(
    "",
    response_model=DifficultyLevelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni zorluk seviyesi oluştur",
    description=(
        "Yeni bir zorluk seviyesi kaydı oluşturur.\n\n"
        "**İş kuralları:**\n"
        "- [R1] `code` ve `name` boş olamaz (boşsa 422).\n"
        "- [R2] `code` benzersiz olmalı; aynı kod varsa **409 Conflict** (FR10 acc5)."
    ),
    responses={
        201: {"description": "Zorluk seviyesi başarıyla oluşturuldu."},
        409: {"description": "Aynı code'a sahip bir kayıt zaten var."},
        422: {"description": "Doğrulama hatası (örn. code/name boş)."},
    },
)
def seviye_olustur(payload: DifficultyLevelCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # [R2] code benzersizlik ön kontrolü.
        mevcut = cursor.execute(
            "SELECT id FROM difficulty_levels WHERE code = ?", (payload.code,)
        ).fetchone()
        if mevcut is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{payload.code}' kodlu bir zorluk seviyesi zaten var.",
            )

        try:
            cursor.execute(
                "INSERT INTO difficulty_levels (code, name) VALUES (?, ?)",
                (payload.code, payload.name),
            )
        except sqlite3.IntegrityError:
            # UNIQUE(code) için güvenlik ağı.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{payload.code}' kodlu bir zorluk seviyesi zaten var.",
            )
        conn.commit()

        yeni_id = cursor.lastrowid
        row = cursor.execute(
            "SELECT * FROM difficulty_levels WHERE id = ?", (yeni_id,)
        ).fetchone()
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[DifficultyLevelResponse],
    summary="Zorluk seviyelerini listele",
    description=(
        "Tüm zorluk seviyelerini listeler. `only_active=true` verilirse yalnızca "
        "aktif (is_active=1) kayıtlar döner."
    ),
)
def seviyeleri_listele(only_active: bool = False):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if only_active:
            rows = cursor.execute(
                "SELECT * FROM difficulty_levels WHERE is_active = 1 ORDER BY id"
            ).fetchall()
        else:
            rows = cursor.execute(
                "SELECT * FROM difficulty_levels ORDER BY id"
            ).fetchall()
        return [_satiri_cevir(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{level_id}",
    response_model=DifficultyLevelResponse,
    summary="Tek bir zorluk seviyesini getir",
    description="Verilen id'ye sahip kaydı döndürür.\n\n**İş kuralı:** [R3] Kayıt yoksa **404**.",
    responses={404: {"description": "Belirtilen id'li zorluk seviyesi bulunamadı."}},
)
def seviye_getir(level_id: int):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM difficulty_levels WHERE id = ?", (level_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{level_id} id'li zorluk seviyesi bulunamadı.",
            )
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.put(
    "/{level_id}",
    response_model=DifficultyLevelResponse,
    summary="Zorluk seviyesini güncelle",
    description=(
        "Mevcut bir zorluk seviyesinin code ve name değerini günceller.\n\n"
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
def seviye_guncelle(level_id: int, payload: DifficultyLevelUpdate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # [R3] Önce kayıt var mı?
        row = cursor.execute(
            "SELECT * FROM difficulty_levels WHERE id = ?", (level_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{level_id} id'li zorluk seviyesi bulunamadı.",
            )

        # [R2] Yeni code KENDİSİ DIŞINDA bir kayıtta var mı?
        cakisma = cursor.execute(
            "SELECT id FROM difficulty_levels WHERE code = ? AND id <> ?",
            (payload.code, level_id),
        ).fetchone()
        if cakisma is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{payload.code}' kodu başka bir kayıtta kullanılıyor.",
            )

        cursor.execute(
            "UPDATE difficulty_levels SET code = ?, name = ? WHERE id = ?",
            (payload.code, payload.name, level_id),
        )
        conn.commit()

        guncel = cursor.execute(
            "SELECT * FROM difficulty_levels WHERE id = ?", (level_id,)
        ).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()


@router.patch(
    "/{level_id}/deactivate",
    response_model=DifficultyLevelResponse,
    summary="Zorluk seviyesini pasife al",
    description=(
        "Kaydı silmek yerine **pasife alır** (is_active=0). Lookup kayıtları "
        "silinmez (FR10 acc7).\n\n"
        "**İş kuralları:**\n"
        "- [R3] Kayıt yoksa **404**.\n"
        "- [R4] Bu seviye **aktif bir kursta** kullanılıyorsa pasife alınamaz → "
        "**409** (FR10 acc6)."
    ),
    responses={
        404: {"description": "Kayıt bulunamadı."},
        409: {"description": "Seviye aktif bir kursta kullanılıyor; pasife alınamaz."},
    },
)
def seviye_pasiflestir(level_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM difficulty_levels WHERE id = ?", (level_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{level_id} id'li zorluk seviyesi bulunamadı.",
            )
        # [R4] Aktif bir kurs bu seviyeyi kullanıyorsa pasife alınamaz (FR10 acc6).
        kullaniliyor = cursor.execute(
            "SELECT 1 FROM courses WHERE difficulty_id = ? AND is_active = 1", (level_id,)
        ).fetchone()
        if kullaniliyor is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu seviye aktif bir kursta kullanılıyor; pasife alınamaz.",
            )
        cursor.execute(
            "UPDATE difficulty_levels SET is_active = 0 WHERE id = ?", (level_id,)
        )
        conn.commit()
        guncel = cursor.execute(
            "SELECT * FROM difficulty_levels WHERE id = ?", (level_id,)
        ).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()


@router.patch(
    "/{level_id}/activate",
    response_model=DifficultyLevelResponse,
    summary="Zorluk seviyesini yeniden aktifleştir",
    description="Pasif bir kaydı tekrar aktif eder (is_active=1).\n\n**İş kuralı:** [R3] Kayıt yoksa **404**.",
    responses={404: {"description": "Kayıt bulunamadı."}},
)
def seviye_aktiflestir(level_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM difficulty_levels WHERE id = ?", (level_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{level_id} id'li zorluk seviyesi bulunamadı.",
            )
        cursor.execute(
            "UPDATE difficulty_levels SET is_active = 1 WHERE id = ?", (level_id,)
        )
        conn.commit()
        guncel = cursor.execute(
            "SELECT * FROM difficulty_levels WHERE id = ?", (level_id,)
        ).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()
