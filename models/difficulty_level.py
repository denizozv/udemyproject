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


def _bos_olamaz(deger: str, alan_adi: str) -> str:
    """Ortak yardımcı: metni kırpar; sadece boşluksa hata fırlatır."""
    temiz = deger.strip()
    if not temiz:
        raise ValueError(f"{alan_adi} boş olamaz.")
    return temiz


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
    def code_bos_olamaz(cls, v: str) -> str:
        return _bos_olamaz(v, "code")

    @field_validator("name")
    @classmethod
    def name_bos_olamaz(cls, v: str) -> str:
        return _bos_olamaz(v, "name")

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
    def code_bos_olamaz(cls, v: str) -> str:
        return _bos_olamaz(v, "code")

    @field_validator("name")
    @classmethod
    def name_bos_olamaz(cls, v: str) -> str:
        return _bos_olamaz(v, "name")

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
