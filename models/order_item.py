"""
models/order_item.py
--------------------
ORDER_ITEMS entity'si için Pydantic modelleri (sipariş kalemleri).

ORDER_ITEMS kolonları (Excel'e birebir): id, order_id, course_id, unit_price,
created_date. Kalem immutable; güncelleme modeli yoktur.
"""

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    """Sipariş kalemi OLUŞTURURKEN beklenen veri."""

    order_id: int = Field(..., description="Bağlı siparişin id'si.", examples=[1])
    course_id: int = Field(..., description="Satın alınan kursun id'si.", examples=[1])
    unit_price: float = Field(..., ge=0, description="Kursun sipariş anındaki fiyatı (snapshot, >= 0).", examples=[499.9])

    model_config = ConfigDict(
        json_schema_extra={"example": {"order_id": 1, "course_id": 1, "unit_price": 499.9}}
    )


class OrderItemResponse(BaseModel):
    """Sipariş kalemini istemciye DÖNDÜRÜRKEN kullanılan model."""

    id: int = Field(..., examples=[1])
    order_id: int = Field(..., examples=[1])
    course_id: int = Field(..., examples=[1])
    unit_price: float = Field(..., examples=[499.9])
    created_date: str = Field(..., examples=["2024-03-15 14:25:00"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"id": 1, "order_id": 1, "course_id": 1, "unit_price": 499.9, "created_date": "2024-03-15 14:25:00"}
        }
    )
