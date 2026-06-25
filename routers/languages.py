"""
routers/languages.py
---------------------
LANGUAGES entity'sinin tüm endpoint'leri. ROLES ile aynı şablon.

Uygulanan iş kuralları (kaynak notu):
  - [R1] language_name boş olamaz  -> Pydantic (422)
  - [R2] language_name benzersiz   -> mükerrer isimde 409
  - [R3] olmayan id istenirse 404
  - [R4] (ERTELENDİ) bir dile bağlı aktif kurs varken pasife alınamaz
         -> COURSES tablosu eklendiğinde uygulanacak.
"""

import sqlite3

from fastapi import APIRouter, HTTPException, status

from database import get_connection
from models.language import LanguageCreate, LanguageResponse, LanguageUpdate

router = APIRouter(prefix="/languages", tags=["Languages"])


def _satiri_language_cevir(row: sqlite3.Row) -> LanguageResponse:
    """Veritabanı satırını LanguageResponse'a çevirir; is_active 0/1 -> True/False."""
    return LanguageResponse(
        id=row["id"],
        language_name=row["language_name"],
        is_active=bool(row["is_active"]),
        created_date=row["created_date"],
    )


@router.post(
    "",
    response_model=LanguageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni dil oluştur",
    description=(
        "Yeni bir dil kaydı oluşturur.\n\n"
        "**İş kuralları:**\n"
        "- [R1] `language_name` boş olamaz (boşsa 422).\n"
        "- [R2] `language_name` benzersiz olmalı; aynı isimde dil varsa **409 Conflict**."
    ),
    responses={
        201: {"description": "Dil başarıyla oluşturuldu."},
        409: {"description": "Aynı isimde bir dil zaten var."},
        422: {"description": "Doğrulama hatası (örn. language_name boş)."},
    },
)
def dil_olustur(payload: LanguageCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # [R2] Benzersizlik ön kontrolü.
        mevcut = cursor.execute(
            "SELECT id FROM languages WHERE language_name = ?", (payload.language_name,)
        ).fetchone()
        if mevcut is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{payload.language_name}' adında bir dil zaten var.",
            )

        try:
            cursor.execute(
                "INSERT INTO languages (language_name) VALUES (?)",
                (payload.language_name,),
            )
        except sqlite3.IntegrityError:
            # UNIQUE kısıtı için güvenlik ağı.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{payload.language_name}' adında bir dil zaten var.",
            )
        conn.commit()

        yeni_id = cursor.lastrowid
        row = cursor.execute(
            "SELECT * FROM languages WHERE id = ?", (yeni_id,)
        ).fetchone()
        return _satiri_language_cevir(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[LanguageResponse],
    summary="Dilleri listele",
    description=(
        "Tüm dilleri listeler. `only_active=true` verilirse yalnızca aktif "
        "(is_active=1) diller döner."
    ),
)
def dilleri_listele(only_active: bool = False):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if only_active:
            rows = cursor.execute(
                "SELECT * FROM languages WHERE is_active = 1 ORDER BY id"
            ).fetchall()
        else:
            rows = cursor.execute("SELECT * FROM languages ORDER BY id").fetchall()
        return [_satiri_language_cevir(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{language_id}",
    response_model=LanguageResponse,
    summary="Tek bir dili getir",
    description="Verilen id'ye sahip dili döndürür.\n\n**İş kuralı:** [R3] Dil yoksa **404**.",
    responses={404: {"description": "Belirtilen id'li dil bulunamadı."}},
)
def dil_getir(language_id: int):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM languages WHERE id = ?", (language_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{language_id} id'li dil bulunamadı.",
            )
        return _satiri_language_cevir(row)
    finally:
        conn.close()


@router.put(
    "/{language_id}",
    response_model=LanguageResponse,
    summary="Dili güncelle",
    description=(
        "Mevcut bir dilin adını günceller.\n\n"
        "**İş kuralları:**\n"
        "- [R3] Dil yoksa **404**.\n"
        "- [R2] Yeni isim başka bir dilde kullanılıyorsa **409 Conflict**."
    ),
    responses={
        404: {"description": "Güncellenecek dil bulunamadı."},
        409: {"description": "Bu isim başka bir dilde kullanılıyor."},
        422: {"description": "Doğrulama hatası (örn. language_name boş)."},
    },
)
def dil_guncelle(language_id: int, payload: LanguageUpdate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # [R3] Önce dil var mı?
        row = cursor.execute(
            "SELECT * FROM languages WHERE id = ?", (language_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{language_id} id'li dil bulunamadı.",
            )

        # [R2] Yeni isim KENDİSİ DIŞINDA bir dilde var mı?
        cakisma = cursor.execute(
            "SELECT id FROM languages WHERE language_name = ? AND id <> ?",
            (payload.language_name, language_id),
        ).fetchone()
        if cakisma is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{payload.language_name}' adı başka bir dilde kullanılıyor.",
            )

        cursor.execute(
            "UPDATE languages SET language_name = ? WHERE id = ?",
            (payload.language_name, language_id),
        )
        conn.commit()

        guncel = cursor.execute(
            "SELECT * FROM languages WHERE id = ?", (language_id,)
        ).fetchone()
        return _satiri_language_cevir(guncel)
    finally:
        conn.close()


@router.patch(
    "/{language_id}/deactivate",
    response_model=LanguageResponse,
    summary="Dili pasife al",
    description=(
        "Dili silmek yerine **pasife alır** (is_active=0).\n\n"
        "**İş kuralları:**\n"
        "- [R3] Dil yoksa **404**.\n"
        "- [R4] Bu dil **aktif bir kursta** kullanılıyorsa pasife alınamaz → "
        "**409** (FR10 acc6)."
    ),
    responses={
        404: {"description": "Dil bulunamadı."},
        409: {"description": "Dil aktif bir kursta kullanılıyor; pasife alınamaz."},
    },
)
def dil_pasiflestir(language_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM languages WHERE id = ?", (language_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{language_id} id'li dil bulunamadı.",
            )
        # [R4] Aktif bir kurs bu dili kullanıyorsa pasife alınamaz (FR10 acc6).
        kullaniliyor = cursor.execute(
            "SELECT 1 FROM courses WHERE language_id = ? AND is_active = 1", (language_id,)
        ).fetchone()
        if kullaniliyor is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu dil aktif bir kursta kullanılıyor; pasife alınamaz.",
            )
        cursor.execute(
            "UPDATE languages SET is_active = 0 WHERE id = ?", (language_id,)
        )
        conn.commit()
        guncel = cursor.execute(
            "SELECT * FROM languages WHERE id = ?", (language_id,)
        ).fetchone()
        return _satiri_language_cevir(guncel)
    finally:
        conn.close()


@router.patch(
    "/{language_id}/activate",
    response_model=LanguageResponse,
    summary="Dili yeniden aktifleştir",
    description="Pasif bir dili tekrar aktif eder (is_active=1).\n\n**İş kuralı:** [R3] Dil yoksa **404**.",
    responses={404: {"description": "Dil bulunamadı."}},
)
def dil_aktiflestir(language_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM languages WHERE id = ?", (language_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{language_id} id'li dil bulunamadı.",
            )
        cursor.execute(
            "UPDATE languages SET is_active = 1 WHERE id = ?", (language_id,)
        )
        conn.commit()
        guncel = cursor.execute(
            "SELECT * FROM languages WHERE id = ?", (language_id,)
        ).fetchone()
        return _satiri_language_cevir(guncel)
    finally:
        conn.close()
