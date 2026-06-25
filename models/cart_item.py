"""
models/cart_item.py
-------------------
CART_ITEMS entity'si için Pydantic modelleri (sepet kalemleri).

CART_ITEMS kolonları (Excel'e birebir): id, cart_id, course_id, created_date.

"Sepete ekle" isteği kullanıcı odaklıdır: {user_id, course_id} alınır; kullanıcının
sepeti yoksa otomatik (lazy) oluşturulur. Saklanan kayıt yine cart_id içerir.
"""

from pydantic import BaseModel, ConfigDict, Field


class CartItemCreate(BaseModel):
    """Sepete kurs EKLERKEN beklenen veri: user_id + course_id (lazy sepet)."""

    user_id: int = Field(..., description="Sepetine eklenecek kullanıcının id'si.", examples=[3])
    course_id: int = Field(..., description="Sepete eklenecek kursun id'si.", examples=[1])

    model_config = ConfigDict(json_schema_extra={"example": {"user_id": 3, "course_id": 1}})


class CartItemResponse(BaseModel):
    """Sepet kalemini istemciye DÖNDÜRÜRKEN kullanılan model."""

    id: int = Field(..., examples=[1])
    cart_id: int = Field(..., examples=[1])
    course_id: int = Field(..., examples=[1])
    created_date: str = Field(..., examples=["2024-03-01 13:05:00"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"id": 1, "cart_id": 1, "course_id": 1, "created_date": "2024-03-01 13:05:00"}
        }
    )


class CartSummaryItem(BaseModel):
    """Sepet özetinde tek bir kalem (kurs adı + fiyatı)."""

    course_id: int = Field(..., examples=[1])
    course_name: str = Field(..., examples=["Spring Boot ile REST API"])
    price: float = Field(..., examples=[499.9])


class CartSummary(BaseModel):
    """
    Sepet özeti (FR7 acc5): her satırda kurs adı + fiyat, ayrıca toplam tutar.
    Kullanıcının sepeti yoksa boş özet döner (cart_id = null).
    """

    user_id: int = Field(..., examples=[3])
    cart_id: int | None = Field(..., description="Kullanıcının sepet id'si (yoksa null).", examples=[1])
    items: list[CartSummaryItem] = Field(..., description="Sepetteki kalemler.")
    item_count: int = Field(..., examples=[2])
    total_price: float = Field(..., description="Kalemlerin güncel fiyat toplamı.", examples=[799.4])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 3,
                "cart_id": 1,
                "items": [
                    {"course_id": 3, "course_name": "Android Kotlin", "price": 599.0},
                    {"course_id": 4, "course_name": "Figma ile UI Tasarimi", "price": 199.9},
                ],
                "item_count": 2,
                "total_price": 798.9,
            }
        }
    )
