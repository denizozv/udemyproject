"""
routers/auth.py
---------------
FR2 — Kullanıcı girişi (login).

Uygulanan iş kuralları (BİZ FR2):
  - acc1: mail + password alanları (Pydantic zorunlu).
  - acc2/acc3: hatalı/eksik kimlik bilgisi -> hangisinin hatalı olduğu belirtilmeden
    **401** "E-posta veya şifre hatalı".
  - acc4/acc5: geçerli (aktif + süresi geçmemiş) kara liste yasağı varsa -> **403**.
    Süresi geçmiş süreli yasak geçerli sayılmaz; süresiz yasak her zaman geçerlidir.
  - acc6/acc7: kendi hesabını silmiş ve saklama süresi (90g) İÇİNDEKİ kullanıcı doğru
    bilgilerle girince yeniden etkinleştirme ONAYI istenir; confirm_reactivation=true
    ile hesap yeniden aktif edilir (is_active=1, deleted_date=NULL) ve giriş tamamlanır.
  - acc8: saklama süresi DOLMUŞ silinmiş hesapla giriş -> hesap yokmuş gibi **401**.
  - acc9/acc10: başarılı girişte kullanıcının TÜM aktif rolleri döndürülür.

KAPSAM NOTU: Token/JWT ve hesap kilidi (CLAUDE acc11) bu sürümde YOKTUR.
"""

import sqlite3

from fastapi import APIRouter, Header, HTTPException, status

from database import get_connection
from models.auth import LoginRequest, LoginResult
from security import generate_token, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])

RETENTION_DAYS = 90  # FR3 saklama süresi (login'de reaktivasyon penceresi için)

# Kimlik hatasında her durumda aynı (ifşa etmeyen) mesaj (acc2).
MSG_LOGIN_INVALID = "E-posta veya şifre hatalı."


def _has_active_ban(cursor: sqlite3.Cursor, user_id: int) -> bool:
    """Kullanıcının ŞU AN geçerli (aktif + süresi geçmemiş) yasağı var mı? (acc4/acc5)"""
    return (
        cursor.execute(
            "SELECT 1 FROM blacklist "
            "WHERE user_id = ? AND is_active = 1 "
            "  AND (ban_until IS NULL OR ban_until > datetime('now','localtime')) LIMIT 1",
            (user_id,),
        ).fetchone()
        is not None
    )


def _get_active_roles(cursor: sqlite3.Cursor, user_id: int) -> list[str]:
    """Kullanıcının aktif rol adları (acc10)."""
    rows = cursor.execute(
        "SELECT r.name FROM user_roles ur JOIN roles r ON ur.role_id = r.id "
        "WHERE ur.user_id = ? AND ur.deleted_date IS NULL AND r.is_active = 1 "
        "ORDER BY r.id",
        (user_id,),
    ).fetchall()
    return [r["name"] for r in rows]


@router.post(
    "/login",
    response_model=LoginResult,
    summary="Kullanıcı girişi (FR2)",
    description=(
        "E-posta + şifre ile giriş yapar.\n\n"
        "**İş kuralları:**\n"
        "- Hatalı/eksik bilgi → **401** (hangisinin hatalı olduğu belirtilmez, acc2).\n"
        "- Geçerli kara liste yasağı → **403** (acc4/acc5).\n"
        "- Silinmiş (saklama süresi içindeki) hesap: önce onay istenir "
        "(`reactivation_required=true`); `confirm_reactivation=true` ile yeniden "
        "etkinleştirilir ve giriş tamamlanır (acc6/acc7).\n"
        "- Saklama süresi dolmuş hesap → hesap yokmuş gibi **401** (acc8).\n"
        "- Başarılı girişte tüm aktif roller döner (acc9/acc10)."
    ),
    responses={
        200: {"description": "Giriş başarılı VEYA yeniden etkinleştirme onayı gerekiyor."},
        401: {"description": "E-posta veya şifre hatalı (acc2)."},
        403: {"description": "Kullanıcı kara listede (acc4)."},
    },
)
def login(payload: LoginRequest):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Kullanıcıyı e-postaya göre bul (aktif veya silinmiş olabilir).
        user = cursor.execute(
            "SELECT * FROM users WHERE lower(mail) = lower(?)", (payload.mail,)
        ).fetchone()
        # acc2: kullanıcı yok veya şifre hatalı -> aynı genel hata.
        if user is None or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_LOGIN_INVALID)

        # acc4/acc5: geçerli yasak varsa giriş yok.
        if _has_active_ban(cursor, user["id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hesabınız kara listede; giriş yapamazsınız.",
            )

        # Silinmiş hesap mı?
        if not user["is_active"] and user["deleted_date"] is not None:
            # acc8: saklama süresi dolmuşsa hesap yokmuş gibi davran.
            retention_expired = cursor.execute(
                "SELECT 1 FROM users WHERE id = ? AND deleted_date < datetime('now','localtime', ?)",
                (user["id"], f"-{RETENTION_DAYS} days"),
            ).fetchone()
            if retention_expired is not None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MSG_LOGIN_INVALID)

            # acc6: saklama süresi içinde -> onay yoksa onay iste.
            if not payload.confirm_reactivation:
                return LoginResult(
                    success=False,
                    reactivation_required=True,
                    user_id=user["id"],
                    full_name=user["full_name"],
                    mail=user["mail"],
                    roles=[],
                    message="Hesabınız silinmiş. Yeniden etkinleştirmek için confirm_reactivation=true ile tekrar deneyin.",
                )
            # acc7: onaylandı -> hesabı yeniden aktif et.
            cursor.execute(
                "UPDATE users SET is_active = 1, deleted_date = NULL WHERE id = ?", (user["id"],)
            )
            conn.commit()

        # acc9/acc10: başarılı giriş -> aktif roller + oturum (token) oluştur.
        roles = _get_active_roles(cursor, user["id"])
        token = generate_token()
        cursor.execute(
            "INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user["id"])
        )
        conn.commit()
        return LoginResult(
            success=True,
            reactivation_required=False,
            user_id=user["id"],
            full_name=user["full_name"],
            mail=user["mail"],
            roles=roles,
            token=token,
            message="Giriş başarılı.",
        )
    finally:
        conn.close()


@router.post(
    "/logout",
    summary="Çıkış (logout)",
    description=(
        "Gönderilen bearer token'a ait oturumu sonlandırır (sessions kaydını siler).\n\n"
        "Token `Authorization: Bearer <token>` başlığında gönderilir. Geçersiz/eksik "
        "token'da da 200 döner (idempotent)."
    ),
)
def logout(authorization: str | None = Header(default=None)):
    # 'Authorization: Bearer <token>' -> token
    token = None
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip() or None

    conn = get_connection()
    try:
        if token:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
        return {"message": "Çıkış yapıldı."}
    finally:
        conn.close()
