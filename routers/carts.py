"""
routers/carts.py
----------------
CARTS entity'sinin endpoint'leri. Kullanıcı sepeti (kullanıcı başına tek sepet).

Uygulanan iş kuralları (BİZ FR7):
  - [R-user] user_id mevcut bir kullanıcı olmalı   -> 400
  - [R-tek] kullanıcının yalnızca bir sepeti olur   -> ikinci POST 409 (acc1)
  - [R3] olmayan id istenirse 404

Ayrıca `get_or_create_cart` yardımcı fonksiyonu CART_ITEMS adımında
"sepete ekle" sırasında LAZY (otomatik) sepet oluşturmak için kullanılacaktır.
"""

import sqlite3

from fastapi import APIRouter, HTTPException, status

from database import get_connection
from models.cart import CartCreate, CartResponse

router = APIRouter(prefix="/carts", tags=["Carts"])


def _row_to_response(row: sqlite3.Row) -> CartResponse:
    """Satırı CartResponse'a çevirir."""
    return CartResponse(
        id=row["id"],
        user_id=row["user_id"],
        created_date=row["created_date"],
    )


def _user_exists(cursor: sqlite3.Cursor, user_id: int) -> bool:
    return cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is not None


def get_or_create_cart(cursor: sqlite3.Cursor, user_id: int) -> sqlite3.Row:
    """
    Kullanıcının sepetini döndürür; yoksa oluşturup döndürür (LAZY).
    NOT: commit ETMEZ — çağıran transaction'ı yönetir. Kullanıcının var olduğu
    çağıran tarafından kontrol edilmiş olmalıdır.
    CART_ITEMS adımındaki "sepete ekle" akışı bunu kullanır.
    """
    row = cursor.execute("SELECT * FROM carts WHERE user_id = ?", (user_id,)).fetchone()
    if row is not None:
        return row
    cursor.execute("INSERT INTO carts (user_id) VALUES (?)", (user_id,))
    return cursor.execute(
        "SELECT * FROM carts WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()


@router.post(
    "",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sepet oluştur",
    description=(
        "Bir kullanıcı için sepet oluşturur.\n\n"
        "**İş kuralları:**\n"
        "- [R-user] `user_id` mevcut olmalı → **400**.\n"
        "- [R-tek] Kullanıcının zaten bir sepeti varsa → **409** (FR7 acc1)."
    ),
    responses={
        201: {"description": "Sepet oluşturuldu."},
        400: {"description": "Geçersiz user_id."},
        409: {"description": "Kullanıcının zaten bir sepeti var."},
    },
)
def create_cart(payload: CartCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        if not _user_exists(cursor, payload.user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{payload.user_id} id'li kullanıcı bulunamadı.",
            )

        existing = cursor.execute(
            "SELECT id FROM carts WHERE user_id = ?", (payload.user_id,)
        ).fetchone()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu kullanıcının zaten bir sepeti var.",
            )

        try:
            cursor.execute("INSERT INTO carts (user_id) VALUES (?)", (payload.user_id,))
        except sqlite3.IntegrityError:
            # UNIQUE(user_id) güvenlik ağı.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu kullanıcının zaten bir sepeti var.",
            )
        conn.commit()

        new_id = cursor.lastrowid
        row = cursor.execute("SELECT * FROM carts WHERE id = ?", (new_id,)).fetchone()
        return _row_to_response(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[CartResponse],
    summary="Sepetleri listele",
    description="Sepetleri listeler. `user_id` verilirse o kullanıcının sepeti(ler)i.",
)
def list_carts(user_id: int | None = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if user_id is not None:
            rows = cursor.execute(
                "SELECT * FROM carts WHERE user_id = ? ORDER BY id", (user_id,)
            ).fetchall()
        else:
            rows = cursor.execute("SELECT * FROM carts ORDER BY id").fetchall()
        return [_row_to_response(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{cart_id}",
    response_model=CartResponse,
    summary="Tek bir sepeti getir",
    description="Verilen id'ye sahip sepeti döndürür.\n\n**İş kuralı:** [R3] Sepet yoksa **404**.",
    responses={404: {"description": "Sepet bulunamadı."}},
)
def get_cart(cart_id: int):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM carts WHERE id = ?", (cart_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{cart_id} id'li sepet bulunamadı.",
            )
        return _row_to_response(row)
    finally:
        conn.close()
