"""
models/course.py
----------------
COURSES entity'si için Pydantic modelleri.

COURSES kolonları (Excel'e birebir): id, category_id, language_id, course_name,
price, description, difficulty_id, is_active, created_date, deleted_date.

Doğrulamalar (BİZ FR9):
  - course_name boş olamaz (acc2)
  - price > 0 (acc3 "sıfır veya negatif olamaz" → ücretsiz kurs yok)
  - category_id / language_id / difficulty_id: mevcut+aktif olmalı (router'da, acc4-5)
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CourseCreate(BaseModel):
    """Yeni kurs OLUŞTURURKEN beklenen veri."""

    category_id: int = Field(..., description="Kategori id'si (aktif olmalı).", examples=[2])
    language_id: int = Field(..., description="Dil id'si (aktif olmalı).", examples=[1])
    course_name: str = Field(..., min_length=3, max_length=150, description="Kurs adı.", examples=["Spring Boot ile REST API"])
    price: float = Field(..., gt=0, description="Fiyat. Sıfır veya negatif olamaz (>0).", examples=[499.9])
    description: str | None = Field(default=None, max_length=2000, description="Açıklama (opsiyonel).", examples=["Sifirdan REST API gelistirme"])
    difficulty_id: int = Field(..., description="Zorluk seviyesi id'si (aktif olmalı).", examples=[2])

    @field_validator("course_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Kurs adı boş olamaz.")
        return stripped

    @field_validator("description")
    @classmethod
    def clean_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "category_id": 2,
                "language_id": 1,
                "course_name": "Spring Boot ile REST API",
                "price": 499.9,
                "description": "Sifirdan REST API gelistirme",
                "difficulty_id": 2,
            }
        }
    )


class CourseUpdate(BaseModel):
    """Mevcut kursu GÜNCELLERKEN beklenen veri (CourseCreate ile aynı alanlar)."""

    category_id: int = Field(..., examples=[3])
    language_id: int = Field(..., examples=[1])
    course_name: str = Field(..., min_length=3, max_length=150, examples=["Android Kotlin"])
    price: float = Field(..., gt=0, examples=[599.0])
    description: str | None = Field(default=None, max_length=2000, examples=["Kotlin ile mobil uygulama"])
    difficulty_id: int = Field(..., examples=[3])

    @field_validator("course_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Kurs adı boş olamaz.")
        return stripped

    @field_validator("description")
    @classmethod
    def clean_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "category_id": 3,
                "language_id": 1,
                "course_name": "Android Kotlin",
                "price": 599.0,
                "description": "Kotlin ile mobil uygulama",
                "difficulty_id": 3,
            }
        }
    )


class CourseResponse(BaseModel):
    """Kurs bilgisini istemciye DÖNDÜRÜRKEN kullanılan model."""

    id: int = Field(..., examples=[1])
    category_id: int = Field(..., examples=[2])
    language_id: int = Field(..., examples=[1])
    course_name: str = Field(..., examples=["Spring Boot ile REST API"])
    price: float = Field(..., examples=[499.9])
    description: str | None = Field(..., examples=["Sifirdan REST API gelistirme"])
    difficulty_id: int = Field(..., examples=[2])
    is_active: bool = Field(..., examples=[True])
    created_date: str = Field(..., examples=["2024-02-01 12:00:00"])
    deleted_date: str | None = Field(..., examples=[None])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "category_id": 2,
                "language_id": 1,
                "course_name": "Spring Boot ile REST API",
                "price": 499.9,
                "description": "Sifirdan REST API gelistirme",
                "difficulty_id": 2,
                "is_active": True,
                "created_date": "2024-02-01 12:00:00",
                "deleted_date": None,
            }
        }
    )
