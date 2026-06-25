"""
models/payment_status.py
------------------------
PAYMENT_STATUSES entity'si için Pydantic modelleri.
Yapı DIFFICULTY_LEVELS / PAYMENT_METHODS ile birebir aynı: code (benzersiz) + name.

PAYMENT_STATUSES kolonları (Excel'e birebir): id, code, name, is_active, created_date.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _bos_olamaz(deger: str, alan_adi: str) -> str:
    """Ortak yardımcı: metni kırpar; sadece boşluksa hata fırlatır."""
    temiz = deger.strip()
    if not temiz:
        raise ValueError(f"{alan_adi} boş olamaz.")
    return temiz


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
    def code_bos_olamaz(cls, v: str) -> str:
        return _bos_olamaz(v, "code")

    @field_validator("name")
    @classmethod
    def name_bos_olamaz(cls, v: str) -> str:
        return _bos_olamaz(v, "name")

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
    def code_bos_olamaz(cls, v: str) -> str:
        return _bos_olamaz(v, "code")

    @field_validator("name")
    @classmethod
    def name_bos_olamaz(cls, v: str) -> str:
        return _bos_olamaz(v, "name")

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
