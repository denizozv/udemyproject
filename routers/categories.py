"""
routers/categories.py
----------------------
CATEGORIES entity'sinin tüm endpoint'leri. İlk self-referencing entity.

Uygulanan iş kuralları (kaynak: BİZ FR10 + referans bütünlüğü):
  - [R1] name boş olamaz                 -> Pydantic (422)
  - [R-parent] parent_id verilirse mevcut bir kategori olmalı -> 400 (FR10 acc3 + FK)
  - [R-self] parent_id, kategorinin KENDİ id'sine eşit olamaz -> 400 (FR10 acc4)
  - [R3] olmayan id istenirse 404
  - [R4] (ERTELENDİ) aktif kursta kullanılan kategori pasife alınamaz
         -> COURSES tablosu eklendiğinde uygulanacak (FR10 acc6).

KAPSAM NOTU (BİZ seti): CATEGORIES için isim benzersizliği ve çok-düzeyli
döngü (A->B->A) / maksimum derinlik kuralları BİZ setinde YOKTUR (bunlar CLAUDE
setine aittir, kullanılmıyor). Bu yüzden uygulanmadı; yalnızca self-loop (acc4)
engellenir.
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from auth_deps import require_role
from database import get_connection
from models.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["Categories"])


def _row_to_response(row: sqlite3.Row) -> CategoryResponse:
    """Veritabanı satırını CategoryResponse'a çevirir. parent_id None olabilir."""
    return CategoryResponse(
        id=row["id"],
        parent_id=row["parent_id"],
        name=row["name"],
        is_active=bool(row["is_active"]),
        created_date=row["created_date"],
    )


def _parent_exists(cursor: sqlite3.Cursor, parent_id: int) -> bool:
    """Verilen parent_id'ye sahip bir kategori var mı? (referans bütünlüğü kontrolü)"""
    return (
        cursor.execute(
            "SELECT 1 FROM categories WHERE id = ?", (parent_id,)
        ).fetchone()
        is not None
    )


@router.post(
    "",
    dependencies=[Depends(require_role("Admin"))],
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni kategori oluştur",
    description=(
        "Yeni bir kategori oluşturur. `parent_id` verilmezse kök kategori olur.\n\n"
        "**İş kuralları:**\n"
        "- [R1] `name` boş olamaz (422).\n"
        "- [R-parent] `parent_id` verilirse mevcut bir kategoriyi işaret etmeli; "
        "aksi halde **400** (FR10 acc3)."
    ),
    responses={
        201: {"description": "Kategori başarıyla oluşturuldu."},
        400: {"description": "Belirtilen parent_id'li üst kategori bulunamadı."},
        422: {"description": "Doğrulama hatası (örn. name boş)."},
    },
)
def create_category(payload: CategoryCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # [R-parent] parent_id verildiyse var olmalı.
        if payload.parent_id is not None and not _parent_exists(
            cursor, payload.parent_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.parent_id} id'li üst kategori bulunamadı.",
            )

        cursor.execute(
            "INSERT INTO categories (parent_id, name) VALUES (?, ?)",
            (payload.parent_id, payload.name),
        )
        conn.commit()

        new_id = cursor.lastrowid
        row = cursor.execute(
            "SELECT * FROM categories WHERE id = ?", (new_id,)
        ).fetchone()
        return _row_to_response(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[CategoryResponse],
    summary="Kategorileri listele",
    description=(
        "Tüm kategorileri listeler.\n\n"
        "- `only_active=true` → yalnızca aktif kategoriler.\n"
        "- `parent_id` → yalnızca o üst kategorinin doğrudan çocukları "
        "(0 verilirse kök kategoriler listelenir)."
    ),
)
def list_categories(only_active: bool = False, parent_id: int | None = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        conditions = []
        params: list = []
        if only_active:
            conditions.append("is_active = 1")
        if parent_id is not None:
            if parent_id == 0:
                # 0 = kök kategoriler (parent_id NULL olanlar)
                conditions.append("parent_id IS NULL")
            else:
                conditions.append("parent_id = ?")
                params.append(parent_id)

        sql = "SELECT * FROM categories"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY id"

        rows = cursor.execute(sql, params).fetchall()
        return [_row_to_response(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Tek bir kategoriyi getir",
    description="Verilen id'ye sahip kategoriyi döndürür.\n\n**İş kuralı:** [R3] Kategori yoksa **404**.",
    responses={404: {"description": "Belirtilen id'li kategori bulunamadı."}},
)
def get_category(category_id: int):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{category_id} id'li kategori bulunamadı.",
            )
        return _row_to_response(row)
    finally:
        conn.close()


@router.put(
    "/{category_id}",
    dependencies=[Depends(require_role("Admin"))],
    response_model=CategoryResponse,
    summary="Kategoriyi güncelle",
    description=(
        "Kategorinin adını ve üst kategorisini (parent_id) günceller.\n\n"
        "**İş kuralları:**\n"
        "- [R3] Kategori yoksa **404**.\n"
        "- [R-self] `parent_id` kategorinin kendi id'sine eşit olamaz → **400** (FR10 acc4).\n"
        "- [R-parent] `parent_id` verilirse mevcut bir kategoriyi işaret etmeli → **400**."
    ),
    responses={
        404: {"description": "Güncellenecek kategori bulunamadı."},
        400: {"description": "Geçersiz parent_id (kendine referans veya mevcut değil)."},
        422: {"description": "Doğrulama hatası (örn. name boş)."},
    },
)
def update_category(category_id: int, payload: CategoryUpdate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # [R3] Önce kategori var mı?
        row = cursor.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{category_id} id'li kategori bulunamadı.",
            )

        if payload.parent_id is not None:
            # [R-self] Kategori kendi kendisinin üstü olamaz.
            if payload.parent_id == category_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bir kategori kendi kendisinin üst kategorisi olamaz.",
                )
            # [R-parent] Belirtilen üst kategori var olmalı.
            if not _parent_exists(cursor, payload.parent_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{payload.parent_id} id'li üst kategori bulunamadı.",
                )

        cursor.execute(
            "UPDATE categories SET parent_id = ?, name = ? WHERE id = ?",
            (payload.parent_id, payload.name, category_id),
        )
        conn.commit()

        updated = cursor.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        return _row_to_response(updated)
    finally:
        conn.close()


@router.patch(
    "/{category_id}/deactivate",
    dependencies=[Depends(require_role("Admin"))],
    response_model=CategoryResponse,
    summary="Kategoriyi pasife al",
    description=(
        "Kategoriyi silmek yerine **pasife alır** (is_active=0).\n\n"
        "**İş kuralları:**\n"
        "- [R3] Kategori yoksa **404**.\n"
        "- [R4] Bu kategori **aktif bir kursta** kullanılıyorsa pasife alınamaz → "
        "**409** (FR10 acc6)."
    ),
    responses={
        404: {"description": "Kategori bulunamadı."},
        409: {"description": "Kategori aktif bir kursta kullanılıyor; pasife alınamaz."},
    },
)
def deactivate_category(category_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{category_id} id'li kategori bulunamadı.",
            )
        # [R4] Aktif bir kurs bu kategoriyi kullanıyorsa pasife alınamaz (FR10 acc6).
        in_use = cursor.execute(
            "SELECT 1 FROM courses WHERE category_id = ? AND is_active = 1", (category_id,)
        ).fetchone()
        if in_use is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu kategori aktif bir kursta kullanılıyor; pasife alınamaz.",
            )
        cursor.execute(
            "UPDATE categories SET is_active = 0 WHERE id = ?", (category_id,)
        )
        conn.commit()
        updated = cursor.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        return _row_to_response(updated)
    finally:
        conn.close()


@router.patch(
    "/{category_id}/activate",
    dependencies=[Depends(require_role("Admin"))],
    response_model=CategoryResponse,
    summary="Kategoriyi yeniden aktifleştir",
    description="Pasif bir kategoriyi tekrar aktif eder (is_active=1).\n\n**İş kuralı:** [R3] Kategori yoksa **404**.",
    responses={404: {"description": "Kategori bulunamadı."}},
)
def activate_category(category_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{category_id} id'li kategori bulunamadı.",
            )
        cursor.execute(
            "UPDATE categories SET is_active = 1 WHERE id = ?", (category_id,)
        )
        conn.commit()
        updated = cursor.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        return _row_to_response(updated)
    finally:
        conn.close()
