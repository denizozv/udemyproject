"""
models/cart.py
--------------
CARTS entity'si için Pydantic modelleri (kullanıcı sepeti).

CARTS kolonları (Excel'e birebir): id, user_id, created_date.
Kullanıcı başına en fazla bir sepet (user_id UNIQUE).
"""

from pydantic import BaseModel, ConfigDict, Field


class CartCreate(BaseModel):
    """Sepet OLUŞTURURKEN beklenen veri (yalnızca user_id)."""

    user_id: int = Field(..., description="Sepetin sahibi kullanıcının id'si.", examples=[3])

    model_config = ConfigDict(json_schema_extra={"example": {"user_id": 3}})


class CartResponse(BaseModel):
    """Sepet bilgisini istemciye DÖNDÜRÜRKEN kullanılan model."""

    id: int = Field(..., examples=[1])
    user_id: int = Field(..., examples=[3])
    created_date: str = Field(..., examples=["2024-03-01 13:00:00"])

    model_config = ConfigDict(
        json_schema_extra={"example": {"id": 1, "user_id": 3, "created_date": "2024-03-01 13:00:00"}}
    )
