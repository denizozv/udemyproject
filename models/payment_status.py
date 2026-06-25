"""
models/payment_status.py
------------------------
PAYMENT_STATUSES entity'si için Pydantic modelleri.
Yapı DIFFICULTY_LEVELS / PAYMENT_METHODS ile birebir aynı: code (benzersiz) + name.

PAYMENT_STATUSES kolonları (Excel'e birebir): id, code, name, is_active, created_date.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _not_empty(value: str, field_name: str) -> str:
    """Ortak yardımcı: metni kırpar; sadece boşluksa hata fırlatır."""
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} boş olamaz.")
    return stripped


class PaymentStatusCreate(BaseModel):
    """Yeni ödeme durumu OLUŞTURURKEN beklenen veri: code + name."""

    code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Teknik kod. Boş olamaz; benzersizdir. Örn: PENDING.",
        examples=["PENDING"],
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Görünen ad. Boş olamaz. Örn: Beklemede.",
        examples=["Beklemede"],
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
        json_schema_extra={"example": {"code": "PENDING", "name": "Beklemede"}}
    )


class PaymentStatusUpdate(BaseModel):
    """Mevcut ödeme durumunu GÜNCELLERKEN beklenen veri: code + name."""

    code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Yeni teknik kod. Boş olamaz; başka kayıtta kullanılıyor olamaz.",
        examples=["COMPLETED"],
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Yeni görünen ad. Boş olamaz.",
        examples=["Tamamlandi"],
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
        json_schema_extra={"example": {"code": "COMPLETED", "name": "Tamamlandi"}}
    )


class PaymentStatusResponse(BaseModel):
    """Ödeme durumu bilgisini istemciye DÖNDÜRÜRKEN kullanılan model."""

    id: int = Field(..., description="Benzersiz numara (PK).", examples=[1])
    code: str = Field(..., description="Teknik kod.", examples=["PENDING"])
    name: str = Field(..., description="Görünen ad.", examples=["Beklemede"])
    is_active: bool = Field(..., description="Aktif mi? (true=aktif, false=pasif)", examples=[True])
    created_date: str = Field(
        ..., description="Oluşturulma tarih-saati.", examples=["2024-01-01 10:00:00"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "code": "PENDING",
                "name": "Beklemede",
                "is_active": True,
                "created_date": "2024-01-01 10:00:00",
            }
        }
    )
