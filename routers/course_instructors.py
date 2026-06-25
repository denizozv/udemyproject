"""
routers/course_instructors.py
-----------------------------
COURSE_INSTRUCTORS entity'sinin endpoint'leri. Kursa eğitmen atama / kaldırma.

Uygulanan iş kuralları (BİZ FR9 + analist kararları):
  - [R-course] course_id mevcut olmalı                       -> 400
  - [R-instructor] instructor_id mevcut VE aktif 'Instructor'
        rolüne sahip olmalı (FR9 acc1)                        -> 400
  - [R-dup] aynı eğitmen aynı kursa iki kez AKTİF atanamaz    -> 409
  - [R-primary] kurs başına en fazla 1 aktif primary olabilir -> 409
  - [R3] olmayan id istenirse 404
  - Kaldırma = soft-delete: deleted_date yazılır (kayıt silinmez).
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from auth_deps import require_role
from database import get_connection
from models.course_instructor import CourseInstructorCreate, CourseInstructorResponse

router = APIRouter(prefix="/course-instructors", tags=["Course Instructors"])


def _row_to_response(row: sqlite3.Row) -> CourseInstructorResponse:
    """Satırı CourseInstructorResponse'a çevirir. is_active = (deleted_date IS NULL)."""
    return CourseInstructorResponse(
        id=row["id"],
        course_id=row["course_id"],
        instructor_id=row["instructor_id"],
        is_primary=bool(row["is_primary"]),
        is_active=row["deleted_date"] is None,
        created_date=row["created_date"],
        deleted_date=row["deleted_date"],
    )


def _course_exists(cursor: sqlite3.Cursor, course_id: int) -> bool:
    return cursor.execute("SELECT 1 FROM courses WHERE id = ?", (course_id,)).fetchone() is not None


def _user_exists(cursor: sqlite3.Cursor, user_id: int) -> bool:
    return cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is not None


def _has_instructor_role(cursor: sqlite3.Cursor, user_id: int) -> bool:
    """Kullanıcının AKTİF 'Instructor' rolü (USER_ROLES) var mı? (FR9 acc1)"""
    return (
        cursor.execute(
            "SELECT 1 FROM user_roles ur "
            "JOIN roles r ON ur.role_id = r.id "
            "WHERE ur.user_id = ? AND ur.deleted_date IS NULL "
            "  AND r.is_active = 1 AND lower(r.name) = 'instructor'",
            (user_id,),
        ).fetchone()
        is not None
    )


def _is_course_instructor(cursor: sqlite3.Cursor, course_id: int, user_id: int) -> bool:
    """Kullanıcı bu kursun AKTİF eğitmeni mi? (FR9 acc6 — yalnızca kendi kursunu yönetebilir)"""
    return (
        cursor.execute(
            "SELECT 1 FROM course_instructors "
            "WHERE course_id = ? AND instructor_id = ? AND deleted_date IS NULL LIMIT 1",
            (course_id, user_id),
        ).fetchone()
        is not None
    )


def _has_active_assignment(cursor: sqlite3.Cursor, course_id: int, instructor_id: int) -> bool:
    """Bu eğitmen bu kursa zaten AKTİF atanmış mı?"""
    return (
        cursor.execute(
            "SELECT 1 FROM course_instructors "
            "WHERE course_id = ? AND instructor_id = ? AND deleted_date IS NULL",
            (course_id, instructor_id),
        ).fetchone()
        is not None
    )


def _has_active_primary(cursor: sqlite3.Cursor, course_id: int, exclude_id: int | None = None) -> bool:
    """Bu kursta zaten AKTİF bir primary eğitmen var mı? (exclude_id kendini dışlamak için)"""
    sql = (
        "SELECT 1 FROM course_instructors "
        "WHERE course_id = ? AND is_primary = 1 AND deleted_date IS NULL"
    )
    params: list = [course_id]
    if exclude_id is not None:
        sql += " AND id <> ?"
        params.append(exclude_id)
    return cursor.execute(sql, params).fetchone() is not None


@router.post(
    "",
    response_model=CourseInstructorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Kursa eğitmen ata",
    description=(
        "Bir kursa eğitmen atar.\n\n"
        "**İş kuralları:**\n"
        "- [R-course] `course_id` mevcut olmalı → **400**.\n"
        "- [R-instructor] `instructor_id` mevcut ve **aktif 'Instructor' rolüne** "
        "sahip olmalı → **400** (FR9 acc1).\n"
        "- [R-dup] Eğitmen bu kursa zaten aktif atanmışsa → **409**.\n"
        "- [R-primary] `is_primary=true` ve kursta zaten aktif bir primary varsa → **409**."
    ),
    responses={
        201: {"description": "Eğitmen kursa atandı."},
        400: {"description": "Geçersiz course_id veya instructor_id (yok / Instructor rolü yok)."},
        409: {"description": "Zaten atanmış veya kursta zaten bir primary var."},
    },
)
def assign_instructor(
    payload: CourseInstructorCreate,
    user: dict = Depends(require_role("Instructor")),
):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # [R-course]
        if not _course_exists(cursor, payload.course_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.course_id} id'li kurs bulunamadı.",
            )
        # FR9 acc6: yalnızca kursun mevcut bir eğitmeni yeni eğitmen ekleyebilir.
        if not _is_course_instructor(cursor, payload.course_id, user["id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu kursa yalnızca mevcut eğitmenleri yeni eğitmen ekleyebilir.",
            )
        # [R-instructor] (var + aktif Instructor rolü)
        if not _user_exists(cursor, payload.instructor_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.instructor_id} id'li kullanıcı bulunamadı.",
            )
        if not _has_instructor_role(cursor, payload.instructor_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.instructor_id} id'li kullanıcının aktif 'Instructor' rolü yok.",
            )
        # [R-dup]
        if _has_active_assignment(cursor, payload.course_id, payload.instructor_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu eğitmen bu kursa zaten aktif olarak atanmış.",
            )
        # [R-primary]
        if payload.is_primary and _has_active_primary(cursor, payload.course_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu kursun zaten aktif bir birincil (primary) eğitmeni var.",
            )

        cursor.execute(
            "INSERT INTO course_instructors (course_id, instructor_id, is_primary) VALUES (?, ?, ?)",
            (payload.course_id, payload.instructor_id, 1 if payload.is_primary else 0),
        )
        conn.commit()

        new_id = cursor.lastrowid
        row = cursor.execute(
            "SELECT * FROM course_instructors WHERE id = ?", (new_id,)
        ).fetchone()
        return _row_to_response(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[CourseInstructorResponse],
    summary="Kurs-eğitmen atamalarını listele",
    description=(
        "Atamaları listeler.\n\n"
        "- `course_id` → o kursun eğitmenleri.\n"
        "- `instructor_id` → o eğitmenin kursları.\n"
        "- `only_active=true` → yalnızca aktif (deleted_date IS NULL) atamalar."
    ),
)
def list_assignments(
    course_id: int | None = None,
    instructor_id: int | None = None,
    only_active: bool = False,
):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        conditions = []
        params: list = []
        if course_id is not None:
            conditions.append("course_id = ?")
            params.append(course_id)
        if instructor_id is not None:
            conditions.append("instructor_id = ?")
            params.append(instructor_id)
        if only_active:
            conditions.append("deleted_date IS NULL")

        sql = "SELECT * FROM course_instructors"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY id"

        rows = cursor.execute(sql, params).fetchall()
        return [_row_to_response(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{ci_id}",
    response_model=CourseInstructorResponse,
    summary="Tek bir atamayı getir",
    description="Verilen id'ye sahip atamayı döndürür.\n\n**İş kuralı:** [R3] Kayıt yoksa **404**.",
    responses={404: {"description": "Atama bulunamadı."}},
)
def get_assignment(ci_id: int):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM course_instructors WHERE id = ?", (ci_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{ci_id} id'li kurs-eğitmen ataması bulunamadı.",
            )
        return _row_to_response(row)
    finally:
        conn.close()


@router.patch(
    "/{ci_id}/make-primary",
    response_model=CourseInstructorResponse,
    summary="Atamayı birincil (primary) yap",
    description=(
        "Bu (aktif) atamayı kursun birincil eğitmeni yapar.\n\n"
        "**İş kuralları:**\n"
        "- [R3] Kayıt yoksa **404**.\n"
        "- Atama pasifse (kaldırılmışsa) → **409**.\n"
        "- Kursta zaten BAŞKA bir aktif primary varsa → **409** (önce o kaldırılmalı).\n"
        "- Zaten primary ise kayıt değişmeden döner (idempotent)."
    ),
    responses={
        404: {"description": "Atama bulunamadı."},
        409: {"description": "Pasif atama veya kursta zaten başka bir primary var."},
    },
)
def make_primary(ci_id: int, user: dict = Depends(require_role("Instructor"))):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM course_instructors WHERE id = ?", (ci_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{ci_id} id'li kurs-eğitmen ataması bulunamadı.",
            )
        # FR9 acc6: yalnızca kursun mevcut bir eğitmeni primary değişikliği yapabilir.
        if not _is_course_instructor(cursor, row["course_id"], user["id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu işlemi yalnızca kursun mevcut eğitmenleri yapabilir.",
            )
        if row["deleted_date"] is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Pasif (kaldırılmış) bir atama primary yapılamaz.",
            )
        if row["is_primary"]:
            return _row_to_response(row)  # zaten primary, idempotent
        # Kursta başka aktif primary var mı?
        if _has_active_primary(cursor, row["course_id"], exclude_id=ci_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu kursun zaten aktif bir birincil (primary) eğitmeni var.",
            )
        cursor.execute(
            "UPDATE course_instructors SET is_primary = 1 WHERE id = ?", (ci_id,)
        )
        conn.commit()
        updated = cursor.execute(
            "SELECT * FROM course_instructors WHERE id = ?", (ci_id,)
        ).fetchone()
        return _row_to_response(updated)
    finally:
        conn.close()


@router.delete(
    "/{ci_id}",
    response_model=CourseInstructorResponse,
    summary="Atamayı kaldır (soft-delete)",
    description=(
        "Atamayı fiziksel silmez; **pasife alır** (deleted_date=now).\n\n"
        "**İş kuralı:** [R3] Kayıt yoksa **404**. Zaten pasifse idempotent.\n\n"
        "_Not: Bir kursun primary eğitmeni kaldırılırsa kurs primary'siz kalabilir; "
        "BİZ setinde bunu engelleyen bir kural yoktur._"
    ),
    responses={404: {"description": "Atama bulunamadı."}},
)
def remove_instructor(ci_id: int, user: dict = Depends(require_role("Instructor"))):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM course_instructors WHERE id = ?", (ci_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{ci_id} id'li kurs-eğitmen ataması bulunamadı.",
            )
        # FR9 acc6: yalnızca kursun mevcut bir eğitmeni eğitmen çıkarabilir.
        if not _is_course_instructor(cursor, row["course_id"], user["id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu kurstan yalnızca mevcut eğitmenleri eğitmen çıkarabilir.",
            )
        if row["deleted_date"] is not None:
            return _row_to_response(row)  # zaten kaldırılmış, idempotent
        cursor.execute(
            "UPDATE course_instructors SET deleted_date = datetime('now','localtime') WHERE id = ?",
            (ci_id,),
        )
        conn.commit()
        updated = cursor.execute(
            "SELECT * FROM course_instructors WHERE id = ?", (ci_id,)
        ).fetchone()
        return _row_to_response(updated)
    finally:
        conn.close()
