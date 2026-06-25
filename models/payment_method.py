"""
models/payment_method.py
------------------------
PAYMENT_METHODS entity'si için Pydantic modelleri.
Yapı DIFFICULTY_LEVELS ile birebir aynıdır: code (benzersiz) + name (zorunlu).

PAYMENT_METHODS kolonları (Excel'e birebir): id, code, name, is_active, created_date.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _not_empty(value: str, field_name: str) -> str:
    """Ortak yardımcı: metni kırpar; sadece boşluksa hata fırlatır."""
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} boş olamaz.")
    return stripped


class PaymentMethodCreate(BaseModel):
    """Yeni ödeme yöntemi OLUŞTURURKEN beklenen veri: code + name."""

    code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Teknik kod. Boş olamaz; benzersizdir. Örn: CREDIT_CARD.",
        examples=["CREDIT_CARD"],
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Görünen ad. Boş olamaz. Örn: Kredi Karti.",
        examples=["Kredi Karti"],
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
        json_schema_extra={"example": {"code": "CREDIT_CARD", "name": "Kredi Karti"}}
    )


class PaymentMethodUpdate(BaseModel):
    """Mevcut ödeme yöntemini GÜNCELLERKEN beklenen veri: code + name."""

    code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Yeni teknik kod. Boş olamaz; başka kayıtta kullanılıyor olamaz.",
        examples=["DEBIT_CARD"],
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Yeni görünen ad. Boş olamaz.",
        examples=["Banka Karti"],
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
        json_schema_extra={"example": {"code": "DEBIT_CARD", "name": "Banka Karti"}}
    )


class PaymentMethodResponse(BaseModel):
    """Ödeme yöntemi bilgisini istemciye DÖNDÜRÜRKEN kullanılan model."""

    id: int = Field(..., description="Benzersiz numara (PK).", examples=[1])
    code: str = Field(..., description="Teknik kod.", examples=["CREDIT_CARD"])
    name: str = Field(..., description="Görünen ad.", examples=["Kredi Karti"])
    is_active: bool = Field(..., description="Aktif mi? (true=aktif, false=pasif)", examples=[True])
    created_date: str = Field(
        ..., description="Oluşturulma tarih-saati.", examples=["2024-01-01 10:00:00"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "code": "CREDIT_CARD",
                "name": "Kredi Karti",
                "is_active": True,
                "created_date": "2024-01-01 10:00:00",
            }
        }
    )
