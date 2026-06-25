"""
routers/user_roles.py
----------------------
USER_ROLES entity'sinin endpoint'leri. Kullanıcıya rol atama / kaldırma.

Uygulanan iş kuralları (BİZ FR11):
  - [R-user] user_id mevcut bir kullanıcı olmalı            -> 400
  - [R-role] role_id mevcut ve AKTİF bir rol olmalı (acc2)  -> 400
  - [R-dup]  aynı rol aynı kullanıcıya iki kez AKTİF atanamaz (acc4) -> 409
  - [R3]     olmayan id istenirse 404
  - [R-last] kullanıcının son aktif rolü kaldırılamaz (acc5) -> 409
  - Rol kaldırma = soft-delete: deleted_date yazılır, kayıt silinmez (acc6)

ERTELENEN:
  - [acc1] Yalnızca Admin yetkisi, [acc8] audit log -> auth adımına.
"""

import sqlite3

from fastapi import APIRouter, HTTPException, status

from database import get_connection
from models.user_role import UserRoleCreate, UserRoleResponse

router = APIRouter(prefix="/user-roles", tags=["User Roles"])


def _row_to_response(row: sqlite3.Row) -> UserRoleResponse:
    """Satırı UserRoleResponse'a çevirir. is_active = (deleted_date IS NULL)."""
    return UserRoleResponse(
        id=row["id"],
        user_id=row["user_id"],
        role_id=row["role_id"],
        is_active=row["deleted_date"] is None,
        created_date=row["created_date"],
        deleted_date=row["deleted_date"],
    )


def _user_exists(cursor: sqlite3.Cursor, user_id: int) -> bool:
    """Verilen id'li kullanıcı var mı?"""
    return cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is not None


def _is_role_active(cursor: sqlite3.Cursor, role_id: int) -> bool:
    """Verilen id'li rol var VE aktif (is_active=1) mi?"""
    return (
        cursor.execute(
            "SELECT 1 FROM roles WHERE id = ? AND is_active = 1", (role_id,)
        ).fetchone()
        is not None
    )


def _has_active_assignment(cursor: sqlite3.Cursor, user_id: int, role_id: int) -> bool:
    """Bu kullanıcıya bu rol zaten AKTİF (deleted_date IS NULL) atanmış mı?"""
    return (
        cursor.execute(
            "SELECT 1 FROM user_roles "
            "WHERE user_id = ? AND role_id = ? AND deleted_date IS NULL",
            (user_id, role_id),
        ).fetchone()
        is not None
    )


def _active_role_count(cursor: sqlite3.Cursor, user_id: int) -> int:
    """Kullanıcının kaç aktif rolü var? (son aktif rol kontrolü için)"""
    row = cursor.execute(
        "SELECT COUNT(*) AS cnt FROM user_roles "
        "WHERE user_id = ? AND deleted_date IS NULL",
        (user_id,),
    ).fetchone()
    return row["cnt"]


@router.post(
    "",
    response_model=UserRoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Kullanıcıya rol ata",
    description=(
        "Bir kullanıcıya rol atar (USER_ROLES kaydı oluşturur).\n\n"
        "**İş kuralları:**\n"
        "- [R-user] `user_id` mevcut olmalı → **400**.\n"
        "- [R-role] `role_id` mevcut ve **aktif** olmalı → **400** (FR11 acc2).\n"
        "- [R-dup] Aynı rol kullanıcıya zaten aktif atanmışsa → **409** (FR11 acc4)."
    ),
    responses={
        201: {"description": "Rol atandı."},
        400: {"description": "Geçersiz user_id veya role_id (yok / rol pasif)."},
        409: {"description": "Bu rol bu kullanıcıya zaten aktif atanmış."},
    },
)
def assign_role(payload: UserRoleCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # [R-user]
        if not _user_exists(cursor, payload.user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.user_id} id'li kullanıcı bulunamadı.",
            )
        # [R-role] (var + aktif)
        if not _is_role_active(cursor, payload.role_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.role_id} id'li aktif bir rol bulunamadı.",
            )
        # [R-dup]
        if _has_active_assignment(cursor, payload.user_id, payload.role_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu rol bu kullanıcıya zaten aktif olarak atanmış.",
            )

        cursor.execute(
            "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
            (payload.user_id, payload.role_id),
        )
        conn.commit()

        new_id = cursor.lastrowid
        row = cursor.execute(
            "SELECT * FROM user_roles WHERE id = ?", (new_id,)
        ).fetchone()
        return _row_to_response(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[UserRoleResponse],
    summary="Rol atamalarını listele",
    description=(
        "USER_ROLES kayıtlarını listeler.\n\n"
        "- `user_id` → yalnızca o kullanıcının atamaları.\n"
        "- `only_active=true` → yalnızca aktif (deleted_date IS NULL) atamalar."
    ),
)
def list_assignments(user_id: int | None = None, only_active: bool = False):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        conditions = []
        params: list = []
        if user_id is not None:
            conditions.append("user_id = ?")
            params.append(user_id)
        if only_active:
            conditions.append("deleted_date IS NULL")

        sql = "SELECT * FROM user_roles"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY id"

        rows = cursor.execute(sql, params).fetchall()
        return [_row_to_response(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{user_role_id}",
    response_model=UserRoleResponse,
    summary="Tek bir rol atamasını getir",
    description="Verilen id'ye sahip atamayı döndürür.\n\n**İş kuralı:** [R3] Kayıt yoksa **404**.",
    responses={404: {"description": "Atama bulunamadı."}},
)
def get_assignment(user_role_id: int):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM user_roles WHERE id = ?", (user_role_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{user_role_id} id'li rol ataması bulunamadı.",
            )
        return _row_to_response(row)
    finally:
        conn.close()


@router.delete(
    "/{user_role_id}",
    response_model=UserRoleResponse,
    summary="Rol atamasını kaldır (soft-delete)",
    description=(
        "Rol atamasını fiziksel silmez; **pasife alır** (deleted_date=now). "
        "FR11 acc6.\n\n"
        "**İş kuralları:**\n"
        "- [R3] Kayıt yoksa **404**.\n"
        "- [R-last] Bu, kullanıcının son aktif rolü ise kaldırılamaz → **409** (FR11 acc5).\n\n"
        "_Not: Zaten kaldırılmış (pasif) bir kayda tekrar istek atılırsa kayıt "
        "değiştirilmeden döner (idempotent)._"
    ),
    responses={
        404: {"description": "Atama bulunamadı."},
        409: {"description": "Kullanıcının son aktif rolü kaldırılamaz."},
    },
)
def remove_role(user_role_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM user_roles WHERE id = ?", (user_role_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{user_role_id} id'li rol ataması bulunamadı.",
            )

        # Zaten kaldırılmışsa (idempotent): değiştirmeden döndür.
        if row["deleted_date"] is not None:
            return _row_to_response(row)

        # [R-last] Bu kullanıcının son aktif rolü mü?
        if _active_role_count(cursor, row["user_id"]) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Kullanıcının en az bir aktif rolü kalmalı; son aktif rol kaldırılamaz.",
            )

        cursor.execute(
            "UPDATE user_roles SET deleted_date = datetime('now','localtime') WHERE id = ?",
            (user_role_id,),
        )
        conn.commit()

        updated = cursor.execute(
            "SELECT * FROM user_roles WHERE id = ?", (user_role_id,)
        ).fetchone()
        return _row_to_response(updated)
    finally:
        conn.close()
