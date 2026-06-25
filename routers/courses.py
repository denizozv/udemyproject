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

from fastapi import APIRouter, Depends, HTTPException, status

from auth_deps import rol_gerektir
from database import get_connection
from models.catalog import (
    CourseCard,
    CourseCatalogPage,
    CourseDetail,
    InstructorBrief,
    ReviewBrief,
)
from models.course import CourseCreate, CourseResponse, CourseUpdate
from routers.order_items import kurs_satin_alindi_mi

router = APIRouter(prefix="/courses", tags=["Courses"])

# FR4 acc8: sayfa başına kurs sayısı.
SAYFA_BOYUTU = 12

# FR4 acc6/acc7: geçerli sıralama seçenekleri (varsayılan popülerlik).
GECERLI_SIRALAMALAR = {"popularity", "price", "rating", "newest"}

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


def _aktif_egitmen_mi(cursor: sqlite3.Cursor, course_id: int, user_id: int) -> bool:
    """Kullanıcı bu kursun AKTİF (herhangi) eğitmeni mi? (FR9 acc6 içerik/fiyat düzenleme)"""
    return (
        cursor.execute(
            "SELECT 1 FROM course_instructors "
            "WHERE course_id = ? AND instructor_id = ? AND deleted_date IS NULL LIMIT 1",
            (course_id, user_id),
        ).fetchone()
        is not None
    )


def _primary_egitmen_mi(cursor: sqlite3.Cursor, course_id: int, user_id: int) -> bool:
    """Kullanıcı bu kursun AKTİF PRIMARY eğitmeni mi? (FR9 acc6 pasife alma)"""
    return (
        cursor.execute(
            "SELECT 1 FROM course_instructors "
            "WHERE course_id = ? AND instructor_id = ? AND is_primary = 1 AND deleted_date IS NULL LIMIT 1",
            (course_id, user_id),
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
        201: {"description": "Kurs oluşturuldu; oluşturan eğitmen primary olarak atandı."},
        400: {"description": "Geçersiz/pasif kategori, dil veya zorluk seviyesi."},
        401: {"description": "Giriş gerekli."},
        403: {"description": "Instructor rolü gerekli (FR9 acc1)."},
        422: {"description": "Doğrulama hatası (örn. price<=0, course_name boş)."},
    },
)
def kurs_olustur(payload: CourseCreate, kullanici: dict = Depends(rol_gerektir("Instructor"))):
    # FR9 acc1: yalnızca Instructor rolündeki kullanıcı kurs ekleyebilir (Depends ile).
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
        yeni_id = cursor.lastrowid

        # Kursu oluşturan eğitmen otomatik PRIMARY eğitmen olarak atanır.
        # (Sahiplik kurallarının — FR9 acc6 — tutarlı çalışması için.)
        cursor.execute(
            "INSERT INTO course_instructors (course_id, instructor_id, is_primary) VALUES (?, ?, 1)",
            (yeni_id, kullanici["id"]),
        )
        conn.commit()

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
    "/catalog",
    response_model=CourseCatalogPage,
    summary="Kurs kataloğu (FR4: filtre + arama + sıralama + sayfalama)",
    description=(
        "Öğrenciye yönelik kurs kataloğu. Yalnızca **aktif** kurslar (acc5).\n\n"
        "**Filtreler:** `q` (kurs adı VEYA eğitmen adında geçen ifade — acc2), "
        "`category_id`, `language_id`, `difficulty_id`, `min_price`, `max_price` "
        "(alt > üst ise **400** — acc4).\n\n"
        "**Sıralama (`sort`)**: `popularity` (varsayılan; son 30 günde COMPLETED "
        "satın alma adedi — acc7), `price`, `rating` (aktif değerlendirme ortalaması; "
        "puanı olmayanlar sona — acc10), `newest`.\n\n"
        "**Sayfalama:** `page` (1'den başlar), sayfa başına 12 (acc8)."
    ),
    responses={400: {"description": "Geçersiz fiyat aralığı veya sıralama değeri."}},
)
def kurs_katalogu(
    q: str | None = None,
    category_id: int | None = None,
    language_id: int | None = None,
    difficulty_id: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str = "popularity",
    page: int = 1,
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fiyat aralığında alt sınır üst sınırdan büyük olamaz.",
        )
    if sort not in GECERLI_SIRALAMALAR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Geçersiz sıralama. Seçenekler: {', '.join(sorted(GECERLI_SIRALAMALAR))}.",
        )
    if page < 1:
        page = 1

    conn = get_connection()
    try:
        cursor = conn.cursor()
        kosullar = ["c.is_active = 1"]  # acc5: yalnızca aktif kurslar
        parametreler: list = []
        if q:
            kosullar.append(
                "(c.course_name LIKE ? OR EXISTS ("
                " SELECT 1 FROM course_instructors ci2 JOIN users u2 ON ci2.instructor_id = u2.id"
                " WHERE ci2.course_id = c.id AND ci2.deleted_date IS NULL AND u2.full_name LIKE ?))"
            )
            parametreler += [f"%{q}%", f"%{q}%"]
        if category_id is not None:
            kosullar.append("c.category_id = ?")
            parametreler.append(category_id)
        if language_id is not None:
            kosullar.append("c.language_id = ?")
            parametreler.append(language_id)
        if difficulty_id is not None:
            kosullar.append("c.difficulty_id = ?")
            parametreler.append(difficulty_id)
        if min_price is not None:
            kosullar.append("c.price >= ?")
            parametreler.append(min_price)
        if max_price is not None:
            kosullar.append("c.price <= ?")
            parametreler.append(max_price)

        sql = (
            "SELECT c.*, "
            "(SELECT ROUND(AVG(r.rating),2) FROM reviews r WHERE r.course_id=c.id AND r.deleted_date IS NULL) AS avg_rating, "
            "(SELECT COUNT(*) FROM reviews r WHERE r.course_id=c.id AND r.deleted_date IS NULL) AS review_count, "
            "(SELECT u.full_name FROM course_instructors ci JOIN users u ON ci.instructor_id=u.id "
            " WHERE ci.course_id=c.id AND ci.is_primary=1 AND ci.deleted_date IS NULL LIMIT 1) AS primary_instructor, "
            "(SELECT COUNT(*) FROM order_items oi JOIN orders o ON oi.order_id=o.id "
            " JOIN payments p ON p.order_id=o.id JOIN payment_statuses ps ON p.payment_status_id=ps.id "
            " WHERE oi.course_id=c.id AND lower(ps.code)='completed' "
            "   AND o.created_date >= datetime('now','localtime','-30 days')) AS popularity "
            "FROM courses c WHERE " + " AND ".join(kosullar)
        )
        rows = cursor.execute(sql, parametreler).fetchall()

        # Sıralama (Python; stable sort ile ikincil ölçütler).
        if sort == "price":
            rows.sort(key=lambda r: r["price"])
        elif sort == "newest":
            rows.sort(key=lambda r: (r["created_date"], r["id"]), reverse=True)
        elif sort == "rating":
            # Puanı olmayanlar (None) en sona; sonra puan azalan.
            rows.sort(key=lambda r: (r["avg_rating"] is None, -(r["avg_rating"] or 0.0)))
        else:  # popularity (varsayılan); eşitlikte en yeni
            rows.sort(key=lambda r: (r["created_date"], r["id"]), reverse=True)
            rows.sort(key=lambda r: r["popularity"], reverse=True)

        total = len(rows)
        total_pages = (total + SAYFA_BOYUTU - 1) // SAYFA_BOYUTU
        bas = (page - 1) * SAYFA_BOYUTU
        sayfa_satirlari = rows[bas : bas + SAYFA_BOYUTU]

        items = [
            CourseCard(
                id=r["id"],
                course_name=r["course_name"],
                category_id=r["category_id"],
                language_id=r["language_id"],
                difficulty_id=r["difficulty_id"],
                price=r["price"],
                primary_instructor=r["primary_instructor"],
                average_rating=r["avg_rating"],
                review_count=r["review_count"],
            )
            for r in sayfa_satirlari
        ]
        return CourseCatalogPage(
            items=items,
            page=page,
            page_size=SAYFA_BOYUTU,
            total=total,
            total_pages=total_pages,
            sort=sort,
        )
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


@router.get(
    "/{course_id}/detail",
    response_model=CourseDetail,
    summary="Kurs detayı (FR5: puan + eğitmenler + yorumlar)",
    description=(
        "Kurs detayını döndürür: bilgiler, ortalama puan + değerlendirme sayısı "
        "(acc2), aktif eğitmenler, aktif değerlendirmeler (acc3).\n\n"
        "**İş kuralları:**\n"
        "- [R3] Kurs yoksa **404**.\n"
        "- [acc4] Pasif kursun detayı, **erişim sahibi olmayan** kullanıcıya "
        "açılmaz → **404**. Erişim sahibi (`viewer_user_id` satın almış) ise açılır."
    ),
    responses={404: {"description": "Kurs bulunamadı veya pasif (erişim yok)."}},
)
def kurs_detay(course_id: int, viewer_user_id: int | None = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        c = cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        if c is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{course_id} id'li kurs bulunamadı.",
            )
        # [acc4] Pasif kurs: yalnızca erişim sahibi (satın almış) görebilir.
        if not c["is_active"]:
            erisim = (
                viewer_user_id is not None
                and kurs_satin_alindi_mi(cursor, viewer_user_id, course_id)
            )
            if not erisim:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Kurs pasif; bu kursun detayına erişiminiz yok.",
                )

        ozet = cursor.execute(
            "SELECT ROUND(AVG(rating),2) AS avg_rating, COUNT(*) AS n "
            "FROM reviews WHERE course_id = ? AND deleted_date IS NULL",
            (course_id,),
        ).fetchone()

        egitmen_rows = cursor.execute(
            "SELECT ci.instructor_id, u.full_name, ci.is_primary "
            "FROM course_instructors ci JOIN users u ON ci.instructor_id = u.id "
            "WHERE ci.course_id = ? AND ci.deleted_date IS NULL "
            "ORDER BY ci.is_primary DESC, ci.id",
            (course_id,),
        ).fetchall()

        review_rows = cursor.execute(
            "SELECT id, user_id, rating, comment, created_date "
            "FROM reviews WHERE course_id = ? AND deleted_date IS NULL ORDER BY id",
            (course_id,),
        ).fetchall()

        return CourseDetail(
            id=c["id"],
            course_name=c["course_name"],
            description=c["description"],
            price=c["price"],
            category_id=c["category_id"],
            language_id=c["language_id"],
            difficulty_id=c["difficulty_id"],
            is_active=bool(c["is_active"]),
            average_rating=ozet["avg_rating"],
            review_count=ozet["n"],
            instructors=[
                InstructorBrief(
                    instructor_id=r["instructor_id"],
                    full_name=r["full_name"],
                    is_primary=bool(r["is_primary"]),
                )
                for r in egitmen_rows
            ],
            reviews=[
                ReviewBrief(
                    id=r["id"],
                    user_id=r["user_id"],
                    rating=r["rating"],
                    comment=r["comment"],
                    created_date=r["created_date"],
                )
                for r in review_rows
            ],
        )
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
        401: {"description": "Giriş gerekli."},
        403: {"description": "Instructor değil veya bu kursun eğitmeni değil (FR9 acc6/acc8)."},
        422: {"description": "Doğrulama hatası."},
    },
)
def kurs_guncelle(
    course_id: int,
    payload: CourseUpdate,
    kullanici: dict = Depends(rol_gerektir("Instructor")),
):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        row = cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{course_id} id'li kurs bulunamadı.",
            )

        # FR9 acc6/acc8: yalnızca kursun aktif eğitmeni içerik/fiyat düzenleyebilir.
        if not _aktif_egitmen_mi(cursor, course_id, kullanici["id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu kursu yalnızca kendi eğitmenleri düzenleyebilir.",
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
def kurs_pasiflestir(course_id: int, kullanici: dict = Depends(rol_gerektir("Instructor"))):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{course_id} id'li kurs bulunamadı.",
            )
        # FR9 acc6 (BİZ): kursu yalnızca kendi (aktif) eğitmeni pasife alabilir.
        if not _aktif_egitmen_mi(cursor, course_id, kullanici["id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu kursu yalnızca kendi eğitmenleri pasife alabilir.",
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
def kurs_aktiflestir(course_id: int, kullanici: dict = Depends(rol_gerektir("Instructor"))):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{course_id} id'li kurs bulunamadı.",
            )
        # FR9 acc6 (BİZ): kursu yalnızca kendi (aktif) eğitmeni yeniden aktifleştirebilir.
        if not _aktif_egitmen_mi(cursor, course_id, kullanici["id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu kursu yalnızca kendi eğitmenleri aktifleştirebilir.",
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
