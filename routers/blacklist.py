"""
routers/blacklist.py
--------------------
BLACKLIST entity'sinin endpoint'leri. Kullanıcıyı kara listeye alma / kaldırma.

Uygulanan iş kuralları (BİZ FR12):
  - [R1] reason zorunlu                              -> Pydantic (422) (acc3)
  - [R-user] user_id ve banned_by mevcut olmalı      -> 400 (acc2 + FK)
  - [R-active] kullanıcının zaten GEÇERLİ bir yasağı varsa yeni eklenemez
               -> 409 (acc5). Geçerli = is_active=1 VE süresi geçmemiş (acc6).
  - [R3] olmayan id istenirse 404
  - Yasak kaldırma = soft: is_active=0, kayıt silinmez (acc7)

NOT (kapsam): Admin yetkisi (acc1) ve "kendini/başka admini yasaklayamama" gibi
rol-bağımlı kurallar BİZ FR12'de yoktur; uygulanmadı.
"""

import sqlite3
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from database import get_connection
from models.blacklist import BlacklistCreate, BlacklistResponse

router = APIRouter(prefix="/blacklist", tags=["Blacklist"])


def _is_ban_valid(is_active: int, ban_until: str | None) -> bool:
    """
    Yasak ŞU AN geçerli mi? (acc5/acc6 için türetilmiş bilgi)
    Geçerli = aktif (is_active=1) VE (süresiz VEYA bitiş tarihi gelecekte).
    """
    if not is_active:
        return False
    if ban_until is None:
        return True
    try:
        end_time = datetime.strptime(ban_until, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        # Beklenmeyen biçim: güvenli tarafta kal, geçerli say.
        return True
    return end_time > datetime.now()


def _row_to_response(row: sqlite3.Row) -> BlacklistResponse:
    """Satırı BlacklistResponse'a çevirir; is_valid türetilir."""
    is_active = bool(row["is_active"])
    return BlacklistResponse(
        id=row["id"],
        user_id=row["user_id"],
        banned_by=row["banned_by"],
        reason=row["reason"],
        ban_until=row["ban_until"],
        is_active=is_active,
        is_valid=_is_ban_valid(row["is_active"], row["ban_until"]),
        created_date=row["created_date"],
    )


def _user_exists(cursor: sqlite3.Cursor, user_id: int) -> bool:
    return cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is not None


def _has_active_ban(cursor: sqlite3.Cursor, user_id: int) -> bool:
    """Kullanıcının ŞU AN geçerli (aktif + süresi geçmemiş) bir yasağı var mı? (acc5)"""
    return (
        cursor.execute(
            "SELECT 1 FROM blacklist "
            "WHERE user_id = ? AND is_active = 1 "
            "  AND (ban_until IS NULL OR ban_until > datetime('now','localtime'))",
            (user_id,),
        ).fetchone()
        is not None
    )


@router.post(
    "",
    response_model=BlacklistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Kullanıcıyı kara listeye al",
    description=(
        "Bir kullanıcıyı kara listeye alır.\n\n"
        "**İş kuralları:**\n"
        "- [R1] `reason` zorunlu (422) (acc3).\n"
        "- [R-user] `user_id` ve `banned_by` mevcut olmalı → **400** (acc2).\n"
        "- [R-active] Kullanıcının zaten geçerli bir yasağı varsa → **409** (acc5).\n"
        "- `ban_until` boş ise süresiz, dolu ise süreli yasak (acc4)."
    ),
    responses={
        201: {"description": "Kullanıcı kara listeye alındı."},
        400: {"description": "Geçersiz user_id veya banned_by."},
        409: {"description": "Kullanıcının zaten geçerli bir yasağı var."},
        422: {"description": "Doğrulama hatası (örn. reason boş)."},
    },
)
def ban_user(payload: BlacklistCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # [R-user] yasaklanan ve yasağı uygulayan mevcut olmalı.
        if not _user_exists(cursor, payload.user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.user_id} id'li (yasaklanacak) kullanıcı bulunamadı.",
            )
        if not _user_exists(cursor, payload.banned_by):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.banned_by} id'li (yasağı uygulayan) kullanıcı bulunamadı.",
            )

        # [R-active] zaten geçerli yasak var mı?
        if _has_active_ban(cursor, payload.user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu kullanıcının zaten geçerli bir kara liste kaydı var.",
            )

        cursor.execute(
            "INSERT INTO blacklist (user_id, banned_by, reason, ban_until) VALUES (?, ?, ?, ?)",
            (payload.user_id, payload.banned_by, payload.reason, payload.ban_until),
        )
        conn.commit()

        new_id = cursor.lastrowid
        row = cursor.execute(
            "SELECT * FROM blacklist WHERE id = ?", (new_id,)
        ).fetchone()
        return _row_to_response(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[BlacklistResponse],
    summary="Kara liste kayıtlarını listele",
    description=(
        "Kara liste kayıtlarını listeler.\n\n"
        "- `user_id` → yalnızca o kullanıcının kayıtları.\n"
        "- `only_active=true` → yalnızca is_active=1 olan kayıtlar.\n"
        "- `only_valid=true` → yalnızca ŞU AN geçerli (aktif + süresi geçmemiş) yasaklar."
    ),
)
def list_bans(
    user_id: int | None = None, only_active: bool = False, only_valid: bool = False
):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        conditions = []
        params: list = []
        if user_id is not None:
            conditions.append("user_id = ?")
            params.append(user_id)
        if only_active:
            conditions.append("is_active = 1")
        if only_valid:
            conditions.append(
                "is_active = 1 AND (ban_until IS NULL OR ban_until > datetime('now','localtime'))"
            )

        sql = "SELECT * FROM blacklist"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY id"

        rows = cursor.execute(sql, params).fetchall()
        return [_row_to_response(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{blacklist_id}",
    response_model=BlacklistResponse,
    summary="Tek bir kara liste kaydını getir",
    description="Verilen id'ye sahip kaydı döndürür.\n\n**İş kuralı:** [R3] Kayıt yoksa **404**.",
    responses={404: {"description": "Kara liste kaydı bulunamadı."}},
)
def get_ban(blacklist_id: int):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM blacklist WHERE id = ?", (blacklist_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{blacklist_id} id'li kara liste kaydı bulunamadı.",
            )
        return _row_to_response(row)
    finally:
        conn.close()


@router.patch(
    "/{blacklist_id}/lift",
    response_model=BlacklistResponse,
    summary="Yasağı kaldır (soft)",
    description=(
        "Yasağı fiziksel silmez; **pasife alır** (is_active=0). FR12 acc7.\n\n"
        "**İş kuralı:** [R3] Kayıt yoksa **404**.\n\n"
        "_Zaten pasif bir kayda tekrar istek atılırsa kayıt değişmeden döner (idempotent)._"
    ),
    responses={404: {"description": "Kara liste kaydı bulunamadı."}},
)
def lift_ban(blacklist_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT * FROM blacklist WHERE id = ?", (blacklist_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{blacklist_id} id'li kara liste kaydı bulunamadı.",
            )

        # Zaten pasifse idempotent.
        if not row["is_active"]:
            return _row_to_response(row)

        cursor.execute(
            "UPDATE blacklist SET is_active = 0 WHERE id = ?", (blacklist_id,)
        )
        conn.commit()
        updated = cursor.execute(
            "SELECT * FROM blacklist WHERE id = ?", (blacklist_id,)
        ).fetchone()
        return _row_to_response(updated)
    finally:
        conn.close()
