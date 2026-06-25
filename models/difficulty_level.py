"""
models/difficulty_level.py
--------------------------
DIFFICULTY_LEVELS entity'si için Pydantic modelleri.

ROLES/LANGUAGES şablonuna benzer; farkı: İKİ anlamlı kolon vardır.
  - code -> teknik kod (BENZERSİZ olmalı; FR10 acc5)
  - name -> görünen ad (zorunlu ama benzersiz değil)

DIFFICULTY_LEVELS kolonları (Excel'e birebir): id, code, name, is_active, created_date.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _not_empty(value: str, field_name: str) -> str:
    """Ortak yardımcı: metni kırpar; sadece boşluksa hata fırlatır."""
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} boş olamaz.")
    return stripped


class DifficultyLevelCreate(BaseModel):
    """Yeni zorluk seviyesi OLUŞTURURKEN beklenen veri: code + name."""

    code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Teknik kod. Boş olamaz; sistemde benzersizdir. Örn: BEGINNER.",
        examples=["BEGINNER"],
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Görünen ad. Boş olamaz. Örn: Baslangic.",
        examples=["Baslangic"],
    )

    @field_validator("code")
    @classmethod
    def code_not_empty(cls, v: str) -> str:
        return _not_empty(v, "code")

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        return _not_empty(v, "name")

    model_config = ConfigDict(
        json_schema_extra={"example": {"code": "BEGINNER", "name": "Baslangic"}}
    )


class DifficultyLevelUpdate(BaseModel):
    """Mevcut zorluk seviyesini GÜNCELLERKEN beklenen veri: code + name."""

    code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Yeni teknik kod. Boş olamaz; başka kayıtta kullanılıyor olamaz.",
        examples=["INTERMEDIATE"],
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Yeni görünen ad. Boş olamaz.",
        examples=["Orta"],
    )

    @field_validator("code")
    @classmethod
    def code_not_empty(cls, v: str) -> str:
        return _not_empty(v, "code")

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        return _not_empty(v, "name")

    model_config = ConfigDict(
        json_schema_extra={"example": {"code": "INTERMEDIATE", "name": "Orta"}}
    )


class DifficultyLevelResponse(BaseModel):
    """Zorluk seviyesi bilgisini istemciye DÖNDÜRÜRKEN kullanılan model."""

    id: int = Field(..., description="Benzersiz numara (PK).", examples=[1])
    code: str = Field(..., description="Teknik kod.", examples=["BEGINNER"])
    name: str = Field(..., description="Görünen ad.", examples=["Baslangic"])
    is_active: bool = Field(..., description="Aktif mi? (true=aktif, false=pasif)", examples=[True])
    created_date: str = Field(
        ..., description="Oluşturulma tarih-saati.", examples=["2024-01-01 10:00:00"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "code": "BEGINNER",
                "name": "Baslangic",
                "is_active": True,
                "created_date": "2024-01-01 10:00:00",
            }
        }
    )
