"""
auth_deps.py
------------
Kimlik doğrulama ve rol-bazlı yetkilendirme için FastAPI bağımlılıkları (Depends).

Akış:
  - İstemci, login'den aldığı token'ı her istekte `Authorization: Bearer <token>`
    başlığıyla gönderir.
  - `get_current_user` bu token'ı çözer, kullanıcıyı + aktif rollerini bulur,
    hesap aktifliğini ve kara liste yasağını kontrol eder.
  - `require_role("Admin", ...)` belirli rolleri zorunlu kılan bir bağımlılık üretir.

NOT: Token/JWT değil, sessions tablosunda saklanan opak token kullanılır
(stateful → yasaklamada anında iptal edilebilir, FR12 acc9).
"""

import sqlite3

from fastapi import Depends, Header, HTTPException, status

from database import get_connection


def _parse_token(authorization: str | None) -> str | None:
    """`Authorization: Bearer <token>` başlığından token'ı ayıklar."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """
    Geçerli token'a sahip aktif kullanıcıyı döndürür: {id, full_name, mail, roles}.

    Hatalar:
      - Token yok/geçersiz veya hesap pasif -> 401.
      - Kullanıcının geçerli kara liste yasağı varsa -> 403 (ve oturumları iptal edilir, FR12 acc9).
    """
    token = _parse_token(authorization)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Giriş gerekli (Authorization: Bearer <token>).",
        )
    conn = get_connection()
    try:
        cursor = conn.cursor()
        user = cursor.execute(
            "SELECT u.* FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.token = ?",
            (token,),
        ).fetchone()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz veya süresi dolmuş oturum."
            )
        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Hesap aktif değil."
            )
        # FR12 acc9: geçerli yasak varsa erişim yok + oturumları temizle.
        ban = cursor.execute(
            "SELECT 1 FROM blacklist WHERE user_id = ? AND is_active = 1 "
            "AND (ban_until IS NULL OR ban_until > datetime('now','localtime')) LIMIT 1",
            (user["id"],),
        ).fetchone()
        if ban is not None:
            cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
            conn.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Hesabınız kara listede."
            )
        roles = [
            r["name"]
            for r in cursor.execute(
                "SELECT r.name FROM user_roles ur JOIN roles r ON ur.role_id = r.id "
                "WHERE ur.user_id = ? AND ur.deleted_date IS NULL AND r.is_active = 1",
                (user["id"],),
            ).fetchall()
        ]
        return {"id": user["id"], "full_name": user["full_name"], "mail": user["mail"], "roles": roles}
    finally:
        conn.close()


def require_role(*required_roles: str):
    """
    Belirtilen rollerden EN AZ BİRİNE sahip olmayı zorunlu kılan bağımlılık üretir.
    Örn: dependencies=[Depends(require_role("Admin"))]
    """

    def check(user: dict = Depends(get_current_user)) -> dict:
        if not set(required_roles) & set(user["roles"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bu işlem için gerekli rol(ler): {', '.join(required_roles)}.",
            )
        return user

    return check
