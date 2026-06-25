"""
models/language.py
-------------------
LANGUAGES entity'si için Pydantic modelleri (ROLES ile aynı şablon).

LANGUAGES kolonları (Excel'e birebir sadık): id, language_name, is_active, created_date.
Doğrulama burada başlar; kural ihlalinde FastAPI otomatik 422 döner.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LanguageCreate(BaseModel):
    """
    Yeni dil OLUŞTURURKEN beklenen veri. Sadece 'language_name' alınır;
    'id', 'is_active', 'created_date' sunucu tarafında otomatik atanır.
    """

    language_name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Dil adı. Boş olamaz; sistemde benzersizdir. Örn: Turkce, Ingilizce.",
        examples=["Turkce"],
    )

    @field_validator("language_name")
    @classmethod
    def isim_bos_olamaz(cls, deger: str) -> str:
        # Baştaki/sondaki boşlukları kırp; sadece boşluksa reddet.
        temiz = deger.strip()
        if not temiz:
            raise ValueError("Dil adı boş olamaz.")
        return temiz

    model_config = ConfigDict(json_schema_extra={"example": {"language_name": "Turkce"}})


class LanguageUpdate(BaseModel):
    """Mevcut bir dili GÜNCELLERKEN beklenen veri (yalnızca 'language_name')."""

    language_name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Dilin yeni adı. Boş olamaz; başka bir dilde kullanılıyor olamaz.",
        examples=["Almanca"],
    )

    @field_validator("language_name")
    @classmethod
    def isim_bos_olamaz(cls, deger: str) -> str:
        temiz = deger.strip()
        if not temiz:
            raise ValueError("Dil adı boş olamaz.")
        return temiz

    model_config = ConfigDict(json_schema_extra={"example": {"language_name": "Almanca"}})


class LanguageResponse(BaseModel):
    """Dil bilgisini istemciye DÖNDÜRÜRKEN kullanılan model."""

    id: int = Field(..., description="Dilin benzersiz numarası (PK).", examples=[1])
    language_name: str = Field(..., description="Dil adı.", examples=["Turkce"])
    is_active: bool = Field(..., description="Dil aktif mi? (true=aktif, false=pasif)", examples=[True])
    created_date: str = Field(
        ..., description="Oluşturulma tarih-saati.", examples=["2024-01-03 09:00:00"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "language_name": "Turkce",
                "is_active": True,
                "created_date": "2024-01-03 09:00:00",
            }
        }
    )
