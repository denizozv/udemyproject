"""
routers/reviews.py
------------------
REVIEWS entity'sinin endpoint'leri. Kurs değerlendirmeleri.

Uygulanan iş kuralları (BİZ FR6):
  - [R1] rating zorunlu ve 1-5 arası      -> Pydantic (422) (acc4/acc5)
  - [R-fk] course_id ve user_id mevcut olmalı -> 400
  - [R-owned] (acc2) yalnızca kursu SATIN ALMIŞ (ödemesi COMPLETED) kullanıcı
              değerlendirebilir -> 403
  - [R-tek] bir kullanıcı bir kursa yalnızca 1 AKTİF değerlendirme yapabilir
            -> 409 (acc3)
  - [R3] olmayan id istenirse 404
  - Silme = soft-delete (deleted_date)

ERTELENEN:
  - [acc6] kursun ortalama puanına dahil etme (FR4/FR5 okuma/hesap) -> ileride.
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from auth_deps import aktif_kullanici
from database import get_connection
from models.review import ReviewCreate, ReviewResponse, ReviewUpdate
from routers.order_items import kurs_satin_alindi_mi

router = APIRouter(prefix="/reviews", tags=["Reviews"])


def _satiri_cevir(row: sqlite3.Row) -> ReviewResponse:
    """Satırı ReviewResponse'a çevirir. is_active = (deleted_date IS NULL)."""
    return ReviewResponse(
        id=row["id"],
        course_id=row["course_id"],
        user_id=row["user_id"],
        rating=row["rating"],
        comment=row["comment"],
        is_active=row["deleted_date"] is None,
        created_date=row["created_date"],
        deleted_date=row["deleted_date"],
    )


def _course_var_mi(cursor: sqlite3.Cursor, course_id: int) -> bool:
    return cursor.execute("SELECT 1 FROM courses WHERE id = ?", (course_id,)).fetchone() is not None


def _user_var_mi(cursor: sqlite3.Cursor, user_id: int) -> bool:
    return cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is not None


def _aktif_review_var_mi(cursor: sqlite3.Cursor, course_id: int, user_id: int) -> bool:
    """Bu kullanıcının bu kursa AKTİF bir değerlendirmesi var mı? (acc3)"""
    return (
        cursor.execute(
            "SELECT 1 FROM reviews "
            "WHERE course_id = ? AND user_id = ? AND deleted_date IS NULL",
            (course_id, user_id),
        ).fetchone()
        is not None
    )


@router.post(
    "",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Kursa değerlendirme yap",
    description=(
        "Bir kursa değerlendirme (puan + opsiyonel yorum) ekler.\n\n"
        "**İş kuralları:**\n"
        "- [R1] `rating` zorunlu ve 1-5 arası → 422 (acc4/acc5).\n"
        "- [R-fk] `course_id` ve `user_id` mevcut olmalı → **400**.\n"
        "- [R-owned] Kullanıcı kursu satın almış (ödemesi COMPLETED) olmalı → "
        "**403** (acc2).\n"
        "- [R-tek] Kullanıcının bu kursa zaten aktif bir değerlendirmesi varsa → "
        "**409** (acc3)."
    ),
    responses={
        201: {"description": "Değerlendirme eklendi."},
        400: {"description": "Geçersiz course_id veya user_id."},
        403: {"description": "Kullanıcı bu kursu satın almamış (değerlendiremez)."},
        409: {"description": "Kullanıcının bu kursa zaten aktif değerlendirmesi var."},
        422: {"description": "Doğrulama hatası (rating eksik/aralık dışı)."},
    },
)
def degerlendirme_yap(payload: ReviewCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        if not _course_var_mi(cursor, payload.course_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.course_id} id'li kurs bulunamadı.",
            )
        if not _user_var_mi(cursor, payload.user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.user_id} id'li kullanıcı bulunamadı.",
            )
        # [R-owned] (acc2) Yalnızca kursu satın almış (ödeme COMPLETED) kullanıcı.
        if not kurs_satin_alindi_mi(cursor, payload.user_id, payload.course_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu kursu değerlendirebilmek için satın almış olmalısınız.",
            )
        if _aktif_review_var_mi(cursor, payload.course_id, payload.user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu kullanıcının bu kursa zaten aktif bir değerlendirmesi var.",
            )

        cursor.execute(
            "INSERT INTO reviews (course_id, user_id, rating, comment) VALUES (?, ?, ?, ?)",
            (payload.course_id, payload.user_id, payload.rating, payload.comment),
        )
        conn.commit()

        yeni_id = cursor.lastrowid
        row = cursor.execute("SELECT * FROM reviews WHERE id = ?", (yeni_id,)).fetchone()
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[ReviewResponse],
    summary="Değerlendirmeleri listele",
    description=(
        "Değerlendirmeleri listeler.\n\n"
        "- `course_id` → o kursun değerlendirmeleri.\n"
        "- `user_id` → o kullanıcının değerlendirmeleri.\n"
        "- `only_active=true` → yalnızca aktif (deleted_date IS NULL)."
    ),
)
def degerlendirmeleri_listele(
    course_id: int | None = None,
    user_id: int | None = None,
    only_active: bool = False,
):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        kosullar = []
        parametreler: list = []
        if course_id is not None:
            kosullar.append("course_id = ?")
            parametreler.append(course_id)
        if user_id is not None:
            kosullar.append("user_id = ?")
            parametreler.append(user_id)
        if only_active:
            kosullar.append("deleted_date IS NULL")

        sql = "SELECT * FROM reviews"
        if kosullar:
            sql += " WHERE " + " AND ".join(kosullar)
        sql += " ORDER BY id"

        rows = cursor.execute(sql, parametreler).fetchall()
        return [_satiri_cevir(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{review_id}",
    response_model=ReviewResponse,
    summary="Tek bir değerlendirmeyi getir",
    description="Verilen id'ye sahip değerlendirmeyi döndürür.\n\n**İş kuralı:** [R3] Kayıt yoksa **404**.",
    responses={404: {"description": "Değerlendirme bulunamadı."}},
)
def degerlendirme_getir(review_id: int):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{review_id} id'li değerlendirme bulunamadı.",
            )
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.put(
    "/{review_id}",
    response_model=ReviewResponse,
    summary="Değerlendirmeyi güncelle",
    description=(
        "Değerlendirmenin puan ve yorumunu günceller (FR6 acc7 — kendi "
        "değerlendirmesini düzenleme).\n\n"
        "**İş kuralları:** [R3] Kayıt yoksa **404**; [R1] rating 1-5 → 422."
    ),
    responses={
        404: {"description": "Değerlendirme bulunamadı."},
        422: {"description": "Doğrulama hatası (rating aralık dışı)."},
    },
)
def degerlendirme_guncelle(
    review_id: int,
    payload: ReviewUpdate,
    kullanici: dict = Depends(aktif_kullanici),
):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{review_id} id'li değerlendirme bulunamadı.",
            )
        # FR6 acc7: kullanıcı yalnızca KENDİ değerlendirmesini düzenleyebilir.
        if row["user_id"] != kullanici["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Yalnızca kendi değerlendirmenizi düzenleyebilirsiniz.",
            )
        cursor.execute(
            "UPDATE reviews SET rating = ?, comment = ? WHERE id = ?",
            (payload.rating, payload.comment, review_id),
        )
        conn.commit()
        guncel = cursor.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()


@router.delete(
    "/{review_id}",
    response_model=ReviewResponse,
    summary="Değerlendirmeyi kaldır (soft-delete)",
    description=(
        "Değerlendirmeyi fiziksel silmez; **pasife alır** (deleted_date=now, "
        "FR6 acc7). Kaldırıldıktan sonra kullanıcı kursa yeniden değerlendirme "
        "yapabilir.\n\n"
        "**İş kuralı:** [R3] Kayıt yoksa **404**. Zaten pasifse idempotent."
    ),
    responses={404: {"description": "Değerlendirme bulunamadı."}},
)
def degerlendirme_kaldir(review_id: int, kullanici: dict = Depends(aktif_kullanici)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{review_id} id'li değerlendirme bulunamadı.",
            )
        # FR6 acc7: değerlendirmeyi sahibi VEYA bir Admin (uygunsuz içerik) kaldırabilir.
        if row["user_id"] != kullanici["id"] and "Admin" not in kullanici["roles"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu değerlendirmeyi yalnızca sahibi veya bir Admin kaldırabilir.",
            )
        if row["deleted_date"] is not None:
            return _satiri_cevir(row)  # zaten kaldırılmış, idempotent
        cursor.execute(
            "UPDATE reviews SET deleted_date = datetime('now','localtime') WHERE id = ?",
            (review_id,),
        )
        conn.commit()
        guncel = cursor.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()
