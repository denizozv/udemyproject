"""
routers/courses.py
------------------
COURSES entity'sinin endpoint'leri.

Uygulanan iş kuralları:
  - [R1] course_name boş olamaz, price > 0      -> Pydantic (422)  (FR9 acc2/acc3)
  - [R-fk] category_id/language_id/difficulty_id mevcut VE AKTİF olmalı
           -> 400 (FR9 acc4/acc5)
  - [R-price-range] listede min_price > max_price ise -> 400 (FR4 acc4)
  - [R3] olmayan id istenirse 404
  - Soft-delete: is_active=0 + deleted_date (FR9 acc7 listede gizleme için)

ERTELENEN: eğitmen-özel yetki (FR9 acc1/acc6/acc8), ortalama puan / eğitmen adıyla
arama (FR4/FR5) -> COURSE_INSTRUCTORS / REVIEWS adımlarında.
"""

import sqlite3

from fastapi import APIRouter, HTTPException, status

from database import get_connection
from models.course import CourseCreate, CourseResponse, CourseUpdate

router = APIRouter(prefix="/courses", tags=["Courses"])

# Hangi alanın hangi lookup tablosuna baktığı (mevcut+aktif kontrolü için).
_LOOKUP_TABLOLARI = {
    "category_id": ("categories", "kategori"),
    "language_id": ("languages", "dil"),
    "difficulty_id": ("difficulty_levels", "zorluk seviyesi"),
}


def _satiri_cevir(row: sqlite3.Row) -> CourseResponse:
    """Veritabanı satırını CourseResponse'a çevirir."""
    return CourseResponse(
        id=row["id"],
        category_id=row["category_id"],
        language_id=row["language_id"],
        course_name=row["course_name"],
        price=row["price"],
        description=row["description"],
        difficulty_id=row["difficulty_id"],
        is_active=bool(row["is_active"]),
        created_date=row["created_date"],
        deleted_date=row["deleted_date"],
    )


def _aktif_mi(cursor: sqlite3.Cursor, tablo: str, kayit_id: int) -> bool:
    """Verilen lookup tablosunda kayıt var VE aktif (is_active=1) mi?"""
    return (
        cursor.execute(
            f"SELECT 1 FROM {tablo} WHERE id = ? AND is_active = 1", (kayit_id,)
        ).fetchone()
        is not None
    )


def _fk_kontrol(cursor: sqlite3.Cursor, category_id: int, language_id: int, difficulty_id: int) -> None:
    """
    [R-fk] category_id/language_id/difficulty_id'nin mevcut VE aktif olduğunu
    doğrular; biri geçersizse 400 fırlatır. (FR9 acc4/acc5)
    """
    degerler = {
        "category_id": category_id,
        "language_id": language_id,
        "difficulty_id": difficulty_id,
    }
    for alan, deger in degerler.items():
        tablo, etiket = _LOOKUP_TABLOLARI[alan]
        if not _aktif_mi(cursor, tablo, deger):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{deger} id'li aktif bir {etiket} bulunamadı.",
            )


@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni kurs oluştur",
    description=(
        "Yeni bir kurs oluşturur.\n\n"
        "**İş kuralları:**\n"
        "- [R1] `course_name` boş olamaz, `price` > 0 → 422 (FR9 acc2/acc3).\n"
        "- [R-fk] `category_id`/`language_id`/`difficulty_id` mevcut ve **aktif** "
        "olmalı → **400** (FR9 acc4/acc5)."
    ),
    responses={
        201: {"description": "Kurs oluşturuldu."},
        400: {"description": "Geçersiz/pasif kategori, dil veya zorluk seviyesi."},
        422: {"description": "Doğrulama hatası (örn. price<=0, course_name boş)."},
    },
)
def kurs_olustur(payload: CourseCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        _fk_kontrol(cursor, payload.category_id, payload.language_id, payload.difficulty_id)

        cursor.execute(
            "INSERT INTO courses (category_id, language_id, course_name, price, description, difficulty_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                payload.category_id,
                payload.language_id,
                payload.course_name,
                payload.price,
                payload.description,
                payload.difficulty_id,
            ),
        )
        conn.commit()

        yeni_id = cursor.lastrowid
        row = cursor.execute("SELECT * FROM courses WHERE id = ?", (yeni_id,)).fetchone()
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[CourseResponse],
    summary="Kursları listele / filtrele",
    description=(
        "Kursları listeler. Filtreler (hepsi opsiyonel, AND ile birleşir):\n"
        "- `q` → kurs adında geçen ifade (FR4 acc2, tam eşleşme gerekmez).\n"
        "- `category_id`, `language_id`, `difficulty_id` → ilgili filtreler.\n"
        "- `min_price`, `max_price` → fiyat aralığı (alt > üst ise **400**, FR4 acc4).\n"
        "- `only_active=true` → yalnızca aktif kurslar (FR4 acc5 / FR9 acc7)."
    ),
    responses={400: {"description": "Fiyat aralığı geçersiz (min_price > max_price)."}},
)
def kurslari_listele(
    q: str | None = None,
    category_id: int | None = None,
    language_id: int | None = None,
    difficulty_id: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    only_active: bool = False,
):
    # [R-price-range] alt sınır üst sınırdan büyük olamaz (FR4 acc4).
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiyat aralığında alt sınır üst sınırdan büyük olamaz.",
        )

    conn = get_connection()
    try:
        cursor = conn.cursor()
        kosullar = []
        parametreler: list = []
        if q:
            kosullar.append("course_name LIKE ?")
            parametreler.append(f"%{q}%")
        if category_id is not None:
            kosullar.append("category_id = ?")
            parametreler.append(category_id)
        if language_id is not None:
            kosullar.append("language_id = ?")
            parametreler.append(language_id)
        if difficulty_id is not None:
            kosullar.append("difficulty_id = ?")
            parametreler.append(difficulty_id)
        if min_price is not None:
            kosullar.append("price >= ?")
            parametreler.append(min_price)
        if max_price is not None:
            kosullar.append("price <= ?")
            parametreler.append(max_price)
        if only_active:
            kosullar.append("is_active = 1")

        sql = "SELECT * FROM courses"
        if kosullar:
            sql += " WHERE " + " AND ".join(kosullar)
        sql += " ORDER BY id"

        rows = cursor.execute(sql, parametreler).fetchall()
        return [_satiri_cevir(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{course_id}",
    response_model=CourseResponse,
    summary="Tek bir kursu getir",
    description="Verilen id'ye sahip kursu döndürür.\n\n**İş kuralı:** [R3] Kurs yoksa **404**.",
    responses={404: {"description": "Kurs bulunamadı."}},
)
def kurs_getir(course_id: int):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{course_id} id'li kurs bulunamadı.",
            )
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.put(
    "/{course_id}",
    response_model=CourseResponse,
    summary="Kursu güncelle",
    description=(
        "Kurs bilgilerini günceller.\n\n"
        "**İş kuralları:**\n"
        "- [R3] Kurs yoksa **404**.\n"
        "- [R1] course_name boş olamaz, price>0 → 422.\n"
        "- [R-fk] category/language/difficulty mevcut+aktif → **400**."
    ),
    responses={
        404: {"description": "Güncellenecek kurs bulunamadı."},
        400: {"description": "Geçersiz/pasif kategori, dil veya zorluk seviyesi."},
        422: {"description": "Doğrulama hatası."},
    },
)
def kurs_guncelle(course_id: int, payload: CourseUpdate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        row = cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{course_id} id'li kurs bulunamadı.",
            )

        _fk_kontrol(cursor, payload.category_id, payload.language_id, payload.difficulty_id)

        cursor.execute(
            "UPDATE courses SET category_id = ?, language_id = ?, course_name = ?, "
            "price = ?, description = ?, difficulty_id = ? WHERE id = ?",
            (
                payload.category_id,
                payload.language_id,
                payload.course_name,
                payload.price,
                payload.description,
                payload.difficulty_id,
                course_id,
            ),
        )
        conn.commit()

        guncel = cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()


@router.patch(
    "/{course_id}/deactivate",
    response_model=CourseResponse,
    summary="Kursu pasife al",
    description=(
        "Kursu silmek yerine **pasife alır** (is_active=0, deleted_date=now). "
        "Pasif kurs öğrenci listelemesinde görünmez (FR9 acc7).\n\n"
        "**İş kuralı:** [R3] Kurs yoksa **404**."
    ),
    responses={404: {"description": "Kurs bulunamadı."}},
)
def kurs_pasiflestir(course_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{course_id} id'li kurs bulunamadı.",
            )
        cursor.execute(
            "UPDATE courses SET is_active = 0, deleted_date = datetime('now','localtime') WHERE id = ?",
            (course_id,),
        )
        conn.commit()
        guncel = cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()


@router.patch(
    "/{course_id}/activate",
    response_model=CourseResponse,
    summary="Kursu yeniden aktifleştir",
    description="Pasif bir kursu tekrar aktif eder (is_active=1, deleted_date=NULL).\n\n**İş kuralı:** [R3] Kurs yoksa **404**.",
    responses={404: {"description": "Kurs bulunamadı."}},
)
def kurs_aktiflestir(course_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{course_id} id'li kurs bulunamadı.",
            )
        cursor.execute(
            "UPDATE courses SET is_active = 1, deleted_date = NULL WHERE id = ?",
            (course_id,),
        )
        conn.commit()
        guncel = cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()
