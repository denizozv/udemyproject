"""
routers/roles.py
----------------
ROLES entity'sinin tüm endpoint'leri (HTTP adresleri) burada tanımlanır.
main.py bu dosyadaki 'router' nesnesini uygulamaya bağlar (include_router).

Veritabanına ORM ile değil, doğrudan sqlite3 ile erişiriz.
Her endpoint:
  1) get_connection() ile bir bağlantı açar,
  2) işini yapar,
  3) finally bloğunda bağlantıyı mutlaka kapatır.

Uygulanan iş kuralları (kaynak notu):
  - [R1] name boş olamaz            -> Pydantic (422)            (genel validasyon)
  - [R2] name benzersiz olmalı      -> mükerrer isimde 409       (mimari kural örneği)
  - [R3] olmayan id istenirse 404                               (referans bütünlüğü)
  - [R4] (ERTELENDİ) rol bir kullanıcıda aktif kullanılıyorsa pasife alınamaz
         -> USER_ROLES tablosu eklendiğinde uygulanacak.
"""

import sqlite3

from fastapi import APIRouter, HTTPException, status

from database import get_connection
from models.role import RoleCreate, RoleResponse, RoleUpdate

# APIRouter: bu entity'ye ait endpoint'leri gruplayan nesne.
#   prefix="/roles" -> tüm adresler /roles ile başlar.
#   tags=["Roles"]  -> Swagger'da bu endpoint'ler "Roles" başlığı altında toplanır.
router = APIRouter(prefix="/roles", tags=["Roles"])


def _satiri_role_cevir(row: sqlite3.Row) -> RoleResponse:
    """
    Veritabanından gelen bir satırı (sqlite3.Row) RoleResponse modeline dönüştürür.
    is_active veritabanında 0/1 (sayı) olarak tutulur; burada True/False'a çevrilir.
    """
    return RoleResponse(
        id=row["id"],
        name=row["name"],
        is_active=bool(row["is_active"]),
        created_date=row["created_date"],
    )


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni rol oluştur",
    description=(
        "Yeni bir rol kaydı oluşturur.\n\n"
        "**İş kuralları:**\n"
        "- [R1] `name` boş olamaz (boşsa 422).\n"
        "- [R2] `name` sistemde benzersiz olmalı; aynı isimde rol varsa **409 Conflict** döner."
    ),
    responses={
        201: {"description": "Rol başarıyla oluşturuldu."},
        409: {"description": "Aynı isimde bir rol zaten var."},
        422: {"description": "Doğrulama hatası (örn. name boş)."},
    },
)
def rol_olustur(payload: RoleCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # [R2] Benzersizlik ön kontrolü: aynı isimde rol var mı?
        mevcut = cursor.execute(
            "SELECT id FROM roles WHERE name = ?", (payload.name,)
        ).fetchone()
        if mevcut is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{payload.name}' adında bir rol zaten var.",
            )

        # Kaydı ekle. is_active ve created_date veritabanı varsayılanlarından gelir.
        try:
            cursor.execute("INSERT INTO roles (name) VALUES (?)", (payload.name,))
        except sqlite3.IntegrityError:
            # UNIQUE kısıtı (yarış durumu vb.) için ikinci bir güvenlik ağı.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{payload.name}' adında bir rol zaten var.",
            )
        conn.commit()

        # Yeni eklenen kaydın id'si ile tam kaydı geri oku ve döndür.
        yeni_id = cursor.lastrowid
        row = cursor.execute("SELECT * FROM roles WHERE id = ?", (yeni_id,)).fetchone()
        return _satiri_role_cevir(row)
    finally:
        conn.close()


@router.get(
    "",
    response_model=list[RoleResponse],
    summary="Rolleri listele",
    description=(
        "Tüm rolleri listeler. `only_active=true` verilirse yalnızca aktif "
        "(is_active=1) roller döner."
    ),
)
def rolleri_listele(only_active: bool = False):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if only_active:
            rows = cursor.execute(
                "SELECT * FROM roles WHERE is_active = 1 ORDER BY id"
            ).fetchall()
        else:
            rows = cursor.execute("SELECT * FROM roles ORDER BY id").fetchall()
        # Her satırı RoleResponse'a çevirip liste olarak döndür.
        return [_satiri_role_cevir(r) for r in rows]
    finally:
        conn.close()


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Tek bir rolü getir",
    description="Verilen id'ye sahip rolü döndürür.\n\n**İş kuralı:** [R3] Rol yoksa **404**.",
    responses={404: {"description": "Belirtilen id'li rol bulunamadı."}},
)
def rol_getir(role_id: int):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{role_id} id'li rol bulunamadı.",
            )
        return _satiri_role_cevir(row)
    finally:
        conn.close()


@router.put(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Rolü güncelle",
    description=(
        "Mevcut bir rolün adını günceller.\n\n"
        "**İş kuralları:**\n"
        "- [R3] Rol yoksa **404**.\n"
        "- [R2] Yeni isim başka bir rolde kullanılıyorsa **409 Conflict**."
    ),
    responses={
        404: {"description": "Güncellenecek rol bulunamadı."},
        409: {"description": "Bu isim başka bir rolde kullanılıyor."},
        422: {"description": "Doğrulama hatası (örn. name boş)."},
    },
)
def rol_guncelle(role_id: int, payload: RoleUpdate):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # [R3] Önce rol var mı kontrol et.
        row = cursor.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{role_id} id'li rol bulunamadı.",
            )

        # [R2] Yeni isim, KENDİSİ DIŞINDA bir rolde var mı? (id <> role_id)
        cakisma = cursor.execute(
            "SELECT id FROM roles WHERE name = ? AND id <> ?", (payload.name, role_id)
        ).fetchone()
        if cakisma is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{payload.name}' adı başka bir rolde kullanılıyor.",
            )

        cursor.execute(
            "UPDATE roles SET name = ? WHERE id = ?", (payload.name, role_id)
        )
        conn.commit()

        guncel = cursor.execute(
            "SELECT * FROM roles WHERE id = ?", (role_id,)
        ).fetchone()
        return _satiri_role_cevir(guncel)
    finally:
        conn.close()


@router.patch(
    "/{role_id}/deactivate",
    response_model=RoleResponse,
    summary="Rolü pasife al",
    description=(
        "Rolü siler yerine **pasife alır** (is_active=0). Lookup kayıtları silinmez, "
        "pasife alınır.\n\n"
        "**İş kuralı:** [R3] Rol yoksa **404**.\n\n"
        "_Not: [R4] 'rol bir kullanıcıda aktif kullanılıyorsa pasife alınamaz' kuralı "
        "USER_ROLES tablosu eklendiğinde buraya eklenecektir._"
    ),
    responses={404: {"description": "Rol bulunamadı."}},
)
def rol_pasiflestir(role_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{role_id} id'li rol bulunamadı.",
            )
        cursor.execute("UPDATE roles SET is_active = 0 WHERE id = ?", (role_id,))
        conn.commit()
        guncel = cursor.execute(
            "SELECT * FROM roles WHERE id = ?", (role_id,)
        ).fetchone()
        return _satiri_role_cevir(guncel)
    finally:
        conn.close()


@router.patch(
    "/{role_id}/activate",
    response_model=RoleResponse,
    summary="Rolü yeniden aktifleştir",
    description="Pasif bir rolü tekrar aktif eder (is_active=1).\n\n**İş kuralı:** [R3] Rol yoksa **404**.",
    responses={404: {"description": "Rol bulunamadı."}},
)
def rol_aktiflestir(role_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{role_id} id'li rol bulunamadı.",
            )
        cursor.execute("UPDATE roles SET is_active = 1 WHERE id = ?", (role_id,))
        conn.commit()
        guncel = cursor.execute(
            "SELECT * FROM roles WHERE id = ?", (role_id,)
        ).fetchone()
        return _satiri_role_cevir(guncel)
    finally:
        conn.close()
