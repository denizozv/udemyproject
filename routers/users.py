"""
routers/users.py
----------------
USERS entity'sinin endpoint'leri. Kayıt (register), profil, şifre değişimi ve
soft-delete / yeniden aktifleştirme işlemlerini içerir.

Uygulanan iş kuralları:
  - [R1] Zorunlu alanlar + format (full_name, mail, password>=8, phone, birth_date)
         -> Pydantic (422)  (BİZ FR1 acc2/acc3/acc5/acc6/acc7)
  - [R-mail] mail benzersiz: aktif bir kullanıcıda VEYA saklama (90 gün) süresi
         dolmamış silinmiş bir kayıtta aynı mail varsa -> 409
         (BİZ FR1 acc4 + FR3 acc5)
  - [R3] olmayan id istenirse 404
  - Soft-delete: silme -> is_active=0, deleted_date=now (FR3 acc1)
  - Reactivate: is_active=1, deleted_date=NULL (FR3 acc3)
  - GÜVENLİK: password_hash hiçbir cevapta dönmez.

UYGULANDI (Adım 11 ek):
  - [acc8] Kayıt başarılı olduğunda kullanıcıya varsayılan 'Student' rolü
    USER_ROLES üzerinden atanır (atomik: rol yoksa kayıt da oluşmaz).

ERTELENEN:
  - [FR2] Giriş (login), hesap kilidi, yeniden aktifleştirme onay akışı -> auth adımı.
  - [FR3 acc4] Saklama süresi dolan verinin kalıcı silinmesi/anonimleştirilmesi
    -> zamanlanmış batch işi (kapsam dışı).
"""

import sqlite3

from fastapi import APIRouter, HTTPException, status

from database import get_connection
from models.course import CourseResponse
from models.user import (
    AccountDeleteRequest,
    CleanupReport,
    PasswordChange,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from security import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["Users"])

# Saklama süresi (FR3): silinmiş hesabın verisi/maili bu süre boyunca korunur.
SAKLAMA_GUN = 90

# FR1 acc8: yeni kullanıcıya atanacak varsayılan rolün adı.
VARSAYILAN_ROL = "Student"


def _satiri_cevir(row: sqlite3.Row) -> UserResponse:
    """
    Veritabanı satırını UserResponse'a çevirir.
    DİKKAT: password_hash bilinçli olarak ALINMAZ (cevaba sızmaması için).
    """
    return UserResponse(
        id=row["id"],
        full_name=row["full_name"],
        mail=row["mail"],
        phone=row["phone"],
        birth_date=row["birth_date"],
        is_active=bool(row["is_active"]),
        created_date=row["created_date"],
        deleted_date=row["deleted_date"],
    )


def _mail_kullanimda_mi(cursor: sqlite3.Cursor, mail: str, haric_id: int | None = None) -> bool:
    """
    [R-mail] Verilen mail kullanımda mı?
    Kullanımda sayılır: (a) aktif bir kullanıcıda, VEYA (b) silinmiş ama saklama
    süresi (90 gün) henüz dolmamış bir kayıtta. 'haric_id' güncellemede kendi
    kaydını hariç tutmak için kullanılır.
    """
    sql = (
        "SELECT id FROM users "
        "WHERE mail = ? "
        "  AND ( is_active = 1 "
        "        OR (deleted_date IS NOT NULL "
        "            AND deleted_date >= datetime('now','localtime', ?)) )"
    )
    params: list = [mail, f"-{SAKLAMA_GUN} days"]
    if haric_id is not None:
        sql += " AND id <> ?"
        params.append(haric_id)
    return cursor.execute(sql, params).fetchone() is not None


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Kullanıcı kaydı (register)",
    description=(
        "Yeni kullanıcı oluşturur. Şifre PBKDF2 ile hash'lenip saklanır; "
        "cevapta dönmez.\n\n"
        "**İş kuralları:**\n"
        "- [R1] Zorunlu alanlar + format (BİZ FR1 acc2/3/5/6/7) → 422.\n"
        "- [R-mail] Aktif ya da saklama süresi (90g) dolmamış silinmiş bir kayıtta "
        "aynı e-posta varsa **409** (FR1 acc4 + FR3 acc5).\n"
        "- Kullanıcı aktif (is_active=1) oluşturulur (acc9).\n"
        "- [acc8] Kayıtla birlikte kullanıcıya varsayılan **Student** rolü atanır "
        "(USER_ROLES). Sistemde aktif 'Student' rolü yoksa kayıt **409** ile reddedilir."
    ),
    responses={
        201: {"description": "Kullanıcı oluşturuldu ve Student rolü atandı."},
        409: {"description": "Bu e-posta kullanımda VEYA aktif 'Student' rolü tanımlı değil."},
        422: {"description": "Doğrulama hatası (zorunlu alan/format)."},
    },
)
def kullanici_kaydet(payload: UserCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # [R-mail] e-posta kullanımda mı?
        if _mail_kullanimda_mi(cursor, payload.mail):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu e-posta kullanımda.",
            )

        # [acc8] Varsayılan 'Student' rolü sistemde aktif mi? Atomik olması için
        # kullanıcıyı OLUŞTURMADAN ÖNCE kontrol ediyoruz; rol yoksa hiçbir şey
        # oluşturulmaz (yarım kayıt kalmaz).
        student = cursor.execute(
            "SELECT id FROM roles WHERE lower(name) = lower(?) AND is_active = 1",
            (VARSAYILAN_ROL,),
        ).fetchone()
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Kayıt tamamlanamadı: sistemde aktif '{VARSAYILAN_ROL}' rolü "
                    f"tanımlı değil. Önce POST /roles ile '{VARSAYILAN_ROL}' rolü oluşturun."
                ),
            )

        # Şifreyi hash'le (düz şifre asla saklanmaz).
        sifre_hash = hash_password(payload.password)

        # 1) Kullanıcıyı ekle.
        cursor.execute(
            "INSERT INTO users (full_name, mail, password_hash, phone, birth_date) "
            "VALUES (?, ?, ?, ?, ?)",
            (payload.full_name, payload.mail, sifre_hash, payload.phone, payload.birth_date),
        )
        yeni_id = cursor.lastrowid

        # 2) [acc8] Varsayılan Student rolünü ata (aynı transaction).
        cursor.execute(
            "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
            (yeni_id, student["id"]),
        )

        # Her iki ekleme birlikte kalıcı olur.
        conn.commit()

        row = cursor.execute("SELECT * FROM users WHERE id = ?", (yeni_id,)).fetchone()
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[UserResponse],
    summary="Kullanıcıları listele",
    description="Tüm kullanıcıları listeler. `only_active=true` → yalnızca aktif kullanıcılar.",
)
def kullanicilari_listele(only_active: bool = False):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if only_active:
            rows = cursor.execute(
                "SELECT * FROM users WHERE is_active = 1 ORDER BY id"
            ).fetchall()
        else:
            rows = cursor.execute("SELECT * FROM users ORDER BY id").fetchall()
        return [_satiri_cevir(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Tek bir kullanıcıyı getir",
    description="Verilen id'ye sahip kullanıcıyı döndürür.\n\n**İş kuralı:** [R3] Kullanıcı yoksa **404**.",
    responses={404: {"description": "Kullanıcı bulunamadı."}},
)
def kullanici_getir(user_id: int):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{user_id} id'li kullanıcı bulunamadı.",
            )
        return _satiri_cevir(row)
    finally:
        conn.close()


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Kullanıcı profilini güncelle",
    description=(
        "Ad, e-posta, telefon ve doğum tarihini günceller (şifre hariç).\n\n"
        "**İş kuralları:**\n"
        "- [R3] Kullanıcı yoksa **404**.\n"
        "- [R-mail] Yeni e-posta başka bir aktif/saklamada kullanıcıda varsa **409**."
    ),
    responses={
        404: {"description": "Kullanıcı bulunamadı."},
        409: {"description": "Bu e-posta kullanımda."},
        422: {"description": "Doğrulama hatası."},
    },
)
def kullanici_guncelle(user_id: int, payload: UserUpdate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        row = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{user_id} id'li kullanıcı bulunamadı.",
            )

        # [R-mail] yeni mail, kendisi HARİÇ başka kullanıcıda mı?
        if _mail_kullanimda_mi(cursor, payload.mail, haric_id=user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu e-posta kullanımda.",
            )

        cursor.execute(
            "UPDATE users SET full_name = ?, mail = ?, phone = ?, birth_date = ? WHERE id = ?",
            (payload.full_name, payload.mail, payload.phone, payload.birth_date, user_id),
        )
        conn.commit()

        guncel = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()


@router.patch(
    "/{user_id}/password",
    response_model=UserResponse,
    summary="Şifre değiştir",
    description=(
        "Kullanıcının şifresini değiştirir. Yeni şifre PBKDF2 ile hash'lenir.\n\n"
        "**İş kuralları:** [R1] yeni şifre ≥ 8 karakter (422), [R3] kullanıcı yoksa **404**."
    ),
    responses={404: {"description": "Kullanıcı bulunamadı."}, 422: {"description": "Şifre 8 karakterden kısa."}},
)
def sifre_degistir(user_id: int, payload: PasswordChange):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{user_id} id'li kullanıcı bulunamadı.",
            )
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(payload.new_password), user_id),
        )
        conn.commit()
        guncel = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()


@router.delete(
    "/{user_id}",
    response_model=UserResponse,
    summary="Hesabı sil (soft-delete)",
    description=(
        "Hesabı fiziksel silmez; **pasife alır** ve silinme tarihini yazar "
        "(is_active=0, deleted_date=now). FR3 acc1.\n\n"
        "**İş kuralı:** [R3] Kullanıcı yoksa **404**."
    ),
    responses={404: {"description": "Kullanıcı bulunamadı."}},
)
def kullanici_sil(user_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{user_id} id'li kullanıcı bulunamadı.",
            )
        cursor.execute(
            "UPDATE users SET is_active = 0, deleted_date = datetime('now','localtime') WHERE id = ?",
            (user_id,),
        )
        conn.commit()
        guncel = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()


@router.patch(
    "/{user_id}/reactivate",
    response_model=UserResponse,
    summary="Silinmiş hesabı yeniden aktifleştir",
    description=(
        "Soft-delete edilmiş bir hesabı geri yükler (is_active=1, "
        "deleted_date=NULL). FR3 acc3.\n\n"
        "**İş kuralı:** [R3] Kullanıcı yoksa **404**.\n\n"
        "_Not: Giriş (login) sırasındaki onaylı yeniden aktifleştirme akışı (FR2) "
        "auth adımında ele alınacaktır; bu endpoint veri seviyesindeki işlemdir._"
    ),
    responses={404: {"description": "Kullanıcı bulunamadı."}},
)
def kullanici_yeniden_aktiflestir(user_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{user_id} id'li kullanıcı bulunamadı.",
            )
        cursor.execute(
            "UPDATE users SET is_active = 1, deleted_date = NULL WHERE id = ?",
            (user_id,),
        )
        conn.commit()
        guncel = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()


@router.post(
    "/{user_id}/delete-account",
    response_model=UserResponse,
    summary="Hesabı kendi şifresiyle sil (self-delete)",
    description=(
        "Kullanıcının KENDİ hesabını silmesi. Mevcut şifre gövdede gönderilir; "
        "doğrulanınca hesap soft-delete edilir (is_active=0, deleted_date=now — FR3 acc1).\n\n"
        "**İş kuralları:**\n"
        "- [R3] Kullanıcı yoksa **404**.\n"
        "- Şifre yanlışsa **403** (silme yapılmaz).\n"
        "- Hesap zaten silinmişse kayıt değişmeden döner (idempotent)."
    ),
    responses={
        403: {"description": "Şifre hatalı; silme reddedildi."},
        404: {"description": "Kullanıcı bulunamadı."},
    },
)
def hesabi_kendim_sil(user_id: int, payload: AccountDeleteRequest):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{user_id} id'li kullanıcı bulunamadı.",
            )

        # Mevcut şifre doğrulaması (düz şifre saklanmadığı için hash ile karşılaştırılır).
        if not verify_password(payload.password, row["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Şifre hatalı; hesap silme işlemi reddedildi.",
            )

        # Zaten silinmişse idempotent.
        if not row["is_active"]:
            return _satiri_cevir(row)

        cursor.execute(
            "UPDATE users SET is_active = 0, deleted_date = datetime('now','localtime') WHERE id = ?",
            (user_id,),
        )
        conn.commit()
        guncel = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _satiri_cevir(guncel)
    finally:
        conn.close()


@router.get(
    "/{user_id}/courses",
    response_model=list[CourseResponse],
    summary="Kullanıcının sahip olduğu (satın aldığı) kurslar",
    description=(
        "Kullanıcının **erişim sahibi olduğu** kursları listeler. Erişim, ödemesi "
        "**COMPLETED** olan siparişlerden türetilir (FR8 acc8). İade edilen "
        "(REFUNDED) veya bekleyen (PENDING) ödemeler erişim saymaz (acc10/acc11).\n\n"
        "**İş kuralı:** [R3] Kullanıcı yoksa **404**."
    ),
    responses={404: {"description": "Kullanıcı bulunamadı."}},
)
def kullanici_kurslari(user_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{user_id} id'li kullanıcı bulunamadı.",
            )
        rows = cursor.execute(
            "SELECT DISTINCT c.* FROM courses c "
            "JOIN order_items oi ON oi.course_id = c.id "
            "JOIN orders o ON oi.order_id = o.id "
            "JOIN payments p ON p.order_id = o.id "
            "JOIN payment_statuses ps ON p.payment_status_id = ps.id "
            "WHERE o.user_id = ? AND lower(ps.code) = 'completed' "
            "ORDER BY c.id",
            (user_id,),
        ).fetchall()
        return [
            CourseResponse(
                id=r["id"],
                category_id=r["category_id"],
                language_id=r["language_id"],
                course_name=r["course_name"],
                price=r["price"],
                description=r["description"],
                difficulty_id=r["difficulty_id"],
                is_active=bool(r["is_active"]),
                created_date=r["created_date"],
                deleted_date=r["deleted_date"],
            )
            for r in rows
        ]
    finally:
        conn.close()


@router.post(
    "/cleanup-expired",
    response_model=CleanupReport,
    summary="Saklama süresi dolan hesapları temizle (FR3 acc4)",
    description=(
        "Soft-delete edilmiş ve saklama süresi (90 gün) **dolmuş** hesapları "
        "KALICI olarak siler. Kullanıcıya ait bağlı kayıtlar (user_roles, blacklist) "
        "aynı işlemde silinir.\n\n"
        "**Güvenlik:** Varsayılan `dry_run=true` → hiçbir şey silmez, yalnızca "
        "etkilenecekleri raporlar. Gerçekten silmek için `dry_run=false` gönderin.\n\n"
        "**Atlama:** Bir hesap başka kayıtlarda `banned_by` ile referanslıysa "
        "(başkalarını yasaklamış bir admin gibi) silinmez; raporda `skipped` altında listelenir.\n\n"
        "Silinen kullanıcının bağlı tüm kayıtları (carts, cart_items, orders, "
        "order_items, payments, reviews, course_instructors, user_roles, blacklist) "
        "da aynı işlemde silinir.\n\n"
        "_Kapsam notu: BİZ FR3 acc4 'kalıcı silme' der; bu yüzden sipariş/ödeme "
        "kayıtları da silinir. Mali kayıtların korunması (anonimleştirme) tercih "
        "edilirse bu davranış değiştirilebilir._"
    ),
)
def saklamasi_dolanlari_temizle(dry_run: bool = True):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Süresi dolmuş adaylar: pasif + deleted_date 90 günden eski.
        adaylar = cursor.execute(
            "SELECT id FROM users "
            "WHERE is_active = 0 AND deleted_date IS NOT NULL "
            "  AND deleted_date < datetime('now','localtime', ?) "
            "ORDER BY id",
            (f"-{SAKLAMA_GUN} days",),
        ).fetchall()

        silinecek: list[int] = []
        atlanan: list[dict] = []

        for aday in adaylar:
            uid = aday["id"]
            # Bu kullanıcı başka kayıtlarda banned_by olarak geçiyor mu? (silme engeli)
            blok = cursor.execute(
                "SELECT 1 FROM blacklist WHERE banned_by = ? LIMIT 1", (uid,)
            ).fetchone()
            if blok is not None:
                atlanan.append(
                    {
                        "id": uid,
                        "reason": "banned_by referansı var; başka kullanıcıların yasak kayıtlarında kullanılıyor.",
                    }
                )
                continue

            silinecek.append(uid)
            if not dry_run:
                # Bağlı kayıtlar FK sırasına göre (çocuktan ebeveyne) silinir,
                # en sonda kullanıcı. Böylece foreign_keys=ON ile çakışma olmaz.
                # 1) Sepet: önce kalemler, sonra sepet.
                cursor.execute(
                    "DELETE FROM cart_items WHERE cart_id IN (SELECT id FROM carts WHERE user_id = ?)",
                    (uid,),
                )
                cursor.execute("DELETE FROM carts WHERE user_id = ?", (uid,))
                # 2) Siparişler: önce order_items ve payments, sonra orders.
                cursor.execute(
                    "DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE user_id = ?)",
                    (uid,),
                )
                cursor.execute(
                    "DELETE FROM payments WHERE order_id IN (SELECT id FROM orders WHERE user_id = ?)",
                    (uid,),
                )
                cursor.execute("DELETE FROM orders WHERE user_id = ?", (uid,))
                # 3) Değerlendirmeler, eğitmenlikler, roller, kara liste (user_id).
                cursor.execute("DELETE FROM reviews WHERE user_id = ?", (uid,))
                cursor.execute("DELETE FROM course_instructors WHERE instructor_id = ?", (uid,))
                cursor.execute("DELETE FROM user_roles WHERE user_id = ?", (uid,))
                cursor.execute("DELETE FROM blacklist WHERE user_id = ?", (uid,))
                # 4) Son olarak kullanıcı.
                cursor.execute("DELETE FROM users WHERE id = ?", (uid,))

        if not dry_run:
            conn.commit()

        return CleanupReport(
            dry_run=dry_run,
            retention_days=SAKLAMA_GUN,
            candidate_count=len(adaylar),
            deleted_user_ids=silinecek,
            skipped=atlanan,
        )
    finally:
        conn.close()
