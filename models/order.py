"""
models/order.py
---------------
ORDERS entity'si için Pydantic modelleri (kesinleşmiş sipariş).

ORDERS kolonları (Excel'e birebir): id, user_id, total_price, created_date.
Sipariş IMMUTABLE'dır; güncelleme modeli yoktur.
"""

from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    """
    Sipariş OLUŞTURURKEN beklenen veri.
    NOT: Gerçek siparişler genelde checkout akışıyla üretilir; bu manuel oluşturma
    temel CRUD içindir. total_price negatif olamaz.
    """

    user_id: int = Field(..., description="Siparişin sahibi kullanıcının id'si.", examples=[3])
    total_price: float = Field(..., ge=0, description="Sipariş toplam tutarı (>= 0).", examples=[799.4])

    model_config = ConfigDict(json_schema_extra={"example": {"user_id": 3, "total_price": 799.4}})


class OrderResponse(BaseModel):
    """Sipariş bilgisini istemciye DÖNDÜRÜRKEN kullanılan model."""

    id: int = Field(..., examples=[1])
    user_id: int = Field(..., examples=[3])
    total_price: float = Field(..., examples=[799.4])
    created_date: str = Field(..., examples=["2024-03-15 14:25:00"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"id": 1, "user_id": 3, "total_price": 799.4, "created_date": "2024-03-15 14:25:00"}
        }
    )
