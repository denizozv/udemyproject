"""
models/user.py
--------------
USERS entity'si için Pydantic modelleri.

Doğrulama kuralları (BİZ FR1):
  - full_name: boş olamaz (acc2)
  - mail: geçerli e-posta formatı (acc3)
  - password: en az 8 karakter (acc5)  [yalnızca istekte; cevapta ASLA dönmez]
  - phone: yalnızca rakam, 10–11 hane (acc6)
  - birth_date: geçerli tarih ve gelecekte olamaz (acc7)

GÜVENLİK: password (düz şifre) yalnızca istek modelinde bulunur. Cevap modeli
(UserResponse) password/password_hash İÇERMEZ.
"""

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Basit e-posta deseni (ek bağımlılık kullanmamak için regex ile).
# "bir@şey.uzanti" kaba kontrolü; boşluk ve ikinci @ kabul etmez.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Telefon: yalnızca rakam, 10–11 hane (Türkiye örnek verisine uygun).
_PHONE_PATTERN = re.compile(r"^\d{10,11}$")


def _validate_birth_date(value: str) -> str:
    """birth_date'i 'YYYY-MM-DD' olarak doğrular ve gelecekte olmadığını kontrol eder."""
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Doğum tarihi 'YYYY-MM-DD' formatında olmalıdır.")
    if parsed > date.today():
        raise ValueError("Doğum tarihi gelecekteki bir tarih olamaz.")
    return parsed.isoformat()


class UserCreate(BaseModel):
    """
    Kullanıcı KAYIT (register) isteğinde beklenen veri.
    Beş alan da zorunludur (BİZ FR1 acc1/acc2).
    """

    full_name: str = Field(..., min_length=2, max_length=100, description="Ad soyad.", examples=["Ahmet Yilmaz"])
    mail: str = Field(..., description="Geçerli e-posta adresi.", examples=["ahmet@elearning.com"])
    password: str = Field(..., min_length=8, max_length=128, description="En az 8 karakter. Hash'lenerek saklanır.", examples=["GizliSifre123"])
    phone: str = Field(..., description="Telefon (yalnızca rakam, 10–11 hane).", examples=["05321112233"])
    birth_date: str = Field(..., description="Doğum tarihi (YYYY-MM-DD). Gelecekte olamaz.", examples=["1985-04-12"])

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Ad soyad boş olamaz.")
        return stripped

    @field_validator("mail")
    @classmethod
    def mail_valid(cls, v: str) -> str:
        # Normalize: baştaki/sondaki boşluk silinir, küçük harfe çevrilir.
        stripped = v.strip().lower()
        if not _EMAIL_PATTERN.match(stripped):
            raise ValueError("Geçerli bir e-posta adresi giriniz.")
        return stripped

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v: str) -> str:
        stripped = v.strip()
        if not _PHONE_PATTERN.match(stripped):
            raise ValueError("Telefon yalnızca rakamlardan oluşmalı ve 10–11 hane olmalıdır.")
        return stripped

    @field_validator("birth_date")
    @classmethod
    def birth_date_valid(cls, v: str) -> str:
        return _validate_birth_date(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Ahmet Yilmaz",
                "mail": "ahmet@elearning.com",
                "password": "GizliSifre123",
                "phone": "05321112233",
                "birth_date": "1985-04-12",
            }
        }
    )


class UserUpdate(BaseModel):
    """
    Kullanıcı profilini GÜNCELLERKEN beklenen veri (şifre HARİÇ).
    Şifre değişimi ayrı endpoint ile yapılır (/users/{id}/password).
    """

    full_name: str = Field(..., min_length=2, max_length=100, examples=["Ahmet Yilmaz"])
    mail: str = Field(..., examples=["ahmet@elearning.com"])
    phone: str = Field(..., examples=["05321112233"])
    birth_date: str = Field(..., examples=["1985-04-12"])

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Ad soyad boş olamaz.")
        return stripped

    @field_validator("mail")
    @classmethod
    def mail_valid(cls, v: str) -> str:
        stripped = v.strip().lower()
        if not _EMAIL_PATTERN.match(stripped):
            raise ValueError("Geçerli bir e-posta adresi giriniz.")
        return stripped

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v: str) -> str:
        stripped = v.strip()
        if not _PHONE_PATTERN.match(stripped):
            raise ValueError("Telefon yalnızca rakamlardan oluşmalı ve 10–11 hane olmalıdır.")
        return stripped

    @field_validator("birth_date")
    @classmethod
    def birth_date_valid(cls, v: str) -> str:
        return _validate_birth_date(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Ahmet Yilmaz",
                "mail": "ahmet@elearning.com",
                "phone": "05321112233",
                "birth_date": "1985-04-12",
            }
        }
    )


class PasswordChange(BaseModel):
    """Şifre değiştirme isteği. Yeni şifre en az 8 karakter (acc5)."""

    new_password: str = Field(..., min_length=8, max_length=128, examples=["YeniSifre456"])

    model_config = ConfigDict(json_schema_extra={"example": {"new_password": "YeniSifre456"}})


class AccountDeleteRequest(BaseModel):
    """
    Kullanıcının KENDİ hesabını silerken gönderdiği veri.
    Mevcut şifresini girer; doğrulanınca hesap soft-delete edilir (FR3 acc1).
    (Burada min_length koymuyoruz; bu mevcut şifrenin doğrulanmasıdır, yeni
    şifre kuralı değil.)
    """

    password: str = Field(..., min_length=1, description="Hesabın mevcut şifresi.", examples=["GizliSifre123"])

    model_config = ConfigDict(json_schema_extra={"example": {"password": "GizliSifre123"}})


class CleanupSkipped(BaseModel):
    """Temizlikte ATLANAN bir hesap ve atlanma nedeni."""

    id: int = Field(..., examples=[5])
    reason: str = Field(..., examples=["banned_by referansı var; başka kayıtlarda kullanılıyor"])


class CleanupReport(BaseModel):
    """Saklama süresi temizliği (cleanup) sonucu raporu."""

    dry_run: bool = Field(..., description="true ise yalnızca rapor (silme yapılmadı).", examples=[True])
    retention_days: int = Field(..., description="Saklama süresi (gün).", examples=[90])
    candidate_count: int = Field(..., description="Süresi dolmuş aday hesap sayısı.", examples=[3])
    deleted_user_ids: list[int] = Field(..., description="Silinen (veya silinecek) hesap id'leri.", examples=[[4, 7]])
    skipped: list[CleanupSkipped] = Field(..., description="Atlanan hesaplar ve nedenleri.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dry_run": True,
                "retention_days": 90,
                "candidate_count": 3,
                "deleted_user_ids": [4, 7],
                "skipped": [{"id": 1, "reason": "banned_by referansı var; başka kayıtlarda kullanılıyor"}],
            }
        }
    )


class UserResponse(BaseModel):
    """
    Kullanıcı bilgisini istemciye DÖNDÜRÜRKEN kullanılan model.
    GÜVENLİK: password / password_hash KESİNLİKLE yer almaz.
    """

    id: int = Field(..., examples=[1])
    full_name: str = Field(..., examples=["Ahmet Yilmaz"])
    mail: str = Field(..., examples=["ahmet@elearning.com"])
    phone: str | None = Field(..., examples=["05321112233"])
    birth_date: str | None = Field(..., examples=["1985-04-12"])
    is_active: bool = Field(..., examples=[True])
    created_date: str = Field(..., examples=["2024-01-05 09:20:00"])
    deleted_date: str | None = Field(..., description="Soft-delete tarihi (silinmemişse null).", examples=[None])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "full_name": "Ahmet Yilmaz",
                "mail": "ahmet@elearning.com",
                "phone": "05321112233",
                "birth_date": "1985-04-12",
                "is_active": True,
                "created_date": "2024-01-05 09:20:00",
                "deleted_date": None,
            }
        }
    )
