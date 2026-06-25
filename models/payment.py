"""
models/payment.py
-----------------
PAYMENTS entity'si için Pydantic modelleri (sipariş ödemesi).

PAYMENTS kolonları (Excel'e birebir): id, order_id, payment_method_id,
payment_status_id, payment_date, address, created_date.

Yeni ödeme oluştururken durum (payment_status_id) istemciden ALINMAZ; sistem
otomatik PENDING atar (FR8 acc7). Durum değişimi ayrı endpoint ile yapılır.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentCreate(BaseModel):
    """Ödeme OLUŞTURURKEN beklenen veri (durum otomatik PENDING)."""

    order_id: int = Field(..., description="Ödenecek siparişin id'si.", examples=[1])
    payment_method_id: int = Field(..., description="Ödeme yöntemi id'si (aktif olmalı).", examples=[1])
    address: str = Field(..., min_length=3, max_length=300, description="Adres. Boş olamaz (FR8 acc3).", examples=["Istanbul Kadikoy Moda Cad. No:12"])

    @field_validator("address")
    @classmethod
    def address_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Adres boş olamaz.")
        return stripped

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"order_id": 1, "payment_method_id": 1, "address": "Istanbul Kadikoy Moda Cad. No:12"}
        }
    )


class PaymentStatusChange(BaseModel):
    """Ödeme durumunu DEĞİŞTİRİRKEN beklenen veri (örn. COMPLETED/FAILED/REFUNDED)."""

    payment_status_id: int = Field(..., description="Yeni ödeme durumu id'si (aktif olmalı).", examples=[2])

    model_config = ConfigDict(json_schema_extra={"example": {"payment_status_id": 2}})


class PaymentResponse(BaseModel):
    """Ödeme bilgisini istemciye DÖNDÜRÜRKEN kullanılan model."""

    id: int = Field(..., examples=[1])
    order_id: int = Field(..., examples=[1])
    payment_method_id: int = Field(..., examples=[1])
    payment_status_id: int = Field(..., examples=[1])
    payment_date: str = Field(..., examples=["2024-03-15 14:30:00"])
    address: str = Field(..., examples=["Istanbul Kadikoy Moda Cad. No:12"])
    created_date: str = Field(..., examples=["2024-03-15 14:30:00"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "order_id": 1,
                "payment_method_id": 1,
                "payment_status_id": 1,
                "payment_date": "2024-03-15 14:30:00",
                "address": "Istanbul Kadikoy Moda Cad. No:12",
                "created_date": "2024-03-15 14:30:00",
            }
        }
    )
