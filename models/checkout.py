"""
models/checkout.py
------------------
CHECKOUT (sepetten sipariş) akışı için istek ve sonuç modelleri.

Checkout: kullanıcının sepetini tek işlemde ORDER + ORDER_ITEM'lar (+ PENDING
PAYMENT) haline getirir ve sepeti temizler (FR8).
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.order import OrderResponse
from models.order_item import OrderItemResponse
from models.payment import PaymentResponse


class CheckoutRequest(BaseModel):
    """Checkout (ödeme) başlatma isteği."""

    user_id: int = Field(..., description="Sepetini sipariş edecek kullanıcının id'si.", examples=[3])
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
            "example": {"user_id": 3, "payment_method_id": 1, "address": "Istanbul Kadikoy Moda Cad. No:12"}
        }
    )


class CheckoutResult(BaseModel):
    """Checkout sonucu: oluşan sipariş, kalemleri ve ödeme."""

    order: OrderResponse
    items: list[OrderItemResponse]
    payment: PaymentResponse
    item_count: int = Field(..., examples=[2])
    total_price: float = Field(..., examples=[799.4])
