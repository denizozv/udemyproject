"""
models/role.py
--------------
ROLES entity'si için Pydantic modelleri.

Pydantic modeli = "bu veri neye benzemeli?" sorusunun cevabı.
Gelen istek (request) ve dönen cevap (response) için ayrı modeller tanımlarız.
Doğrulama (validation) ilk olarak BURADA başlar: tip uymazsa veya kural
ihlal edilirse FastAPI otomatik 422 (Unprocessable Entity) döner.

ROLES kolonları (Excel'e birebir sadık): id, name, is_active, created_date.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RoleCreate(BaseModel):
    """
    Yeni rol OLUŞTURURKEN istemciden (client) beklediğimiz veri.
    Sadece 'name' alınır; 'id', 'is_active', 'created_date' sunucu tarafında
    otomatik atanır (kullanıcı bunları gönderemez).
    """

    # name: zorunlu (...) bir metin. min/max uzunluk temel bir akıl-sağlığı
    # sınırıdır (FR'de rol için özel uzunluk kuralı yok). examples -> Swagger örneği.
    name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Rol adı. Boş olamaz; sistemde benzersizdir. Örn: Admin, Instructor, Student.",
        examples=["Instructor"],
    )

    # field_validator: 'name' alanı için ek/özel doğrulama.
    # Tip ve uzunluk kontrolünden SONRA çalışır (Pydantic v2 varsayılanı 'after').
    @field_validator("name")
    @classmethod
    def name_not_empty(cls, value: str) -> str:
        # .strip() -> baştaki/sondaki boşlukları siler.
        stripped = value.strip()
        # Sadece boşluktan oluşan ("   ") bir isim geçersizdir.
        if not stripped:
            raise ValueError("Rol adı boş olamaz.")
        # Temizlenmiş (kırpılmış) hali kaydedilir.
        return stripped

    # Swagger'da istek gövdesi (request body) için örnek gösterimi.
    model_config = ConfigDict(json_schema_extra={"example": {"name": "Instructor"}})


class RoleUpdate(BaseModel):
    """
    Mevcut bir rolü GÜNCELLERKEN beklenen veri. Şimdilik sadece 'name'
    güncellenebilir (aktiflik durumu ayrı endpoint'lerle yönetilir).
    """

    name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Rolün yeni adı. Boş olamaz; başka bir rolde kullanılıyor olamaz.",
        examples=["Egitmen"],
    )

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Rol adı boş olamaz.")
        return stripped

    model_config = ConfigDict(json_schema_extra={"example": {"name": "Egitmen"}})


class RoleResponse(BaseModel):
    """
    Rol bilgisini istemciye DÖNDÜRÜRKEN kullanılan model.
    Veritabanındaki tüm kolonları (id dahil) içerir.
    """

    id: int = Field(..., description="Rolün benzersiz numarası (PK).", examples=[2])
    name: str = Field(..., description="Rol adı.", examples=["Instructor"])
    is_active: bool = Field(..., description="Rol aktif mi? (true=aktif, false=pasif)", examples=[True])
    created_date: str = Field(
        ..., description="Oluşturulma tarih-saati.", examples=["2024-01-01 10:00:00"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 2,
                "name": "Instructor",
                "is_active": True,
                "created_date": "2024-01-01 10:00:00",
            }
        }
    )
