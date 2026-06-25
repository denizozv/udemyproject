"""
models/review.py
----------------
REVIEWS entity'si için Pydantic modelleri (kurs değerlendirmeleri).

REVIEWS kolonları (Excel'e birebir): id, course_id, user_id, rating, comment,
created_date, deleted_date.

Doğrulamalar (BİZ FR6):
  - rating zorunlu ve 1-5 arası (acc4/acc5)
  - comment opsiyonel
NOT: is_active kolonu yoktur; cevapta 'is_active' TÜRETİLMİŞTİR (deleted_date IS NULL).
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewCreate(BaseModel):
    """Yeni değerlendirme OLUŞTURURKEN beklenen veri."""

    course_id: int = Field(..., description="Değerlendirilen kursun id'si.", examples=[1])
    user_id: int = Field(..., description="Değerlendiren kullanıcının id'si.", examples=[3])
    rating: int = Field(..., ge=1, le=5, description="Puan, 1-5 arası (zorunlu).", examples=[5])
    comment: str | None = Field(default=None, max_length=1000, description="Yorum (opsiyonel).", examples=["Cok faydali bir kurstu"])

    @field_validator("comment")
    @classmethod
    def yorum_temizle(cls, v: str | None) -> str | None:
        if v is None:
            return None
        temiz = v.strip()
        return temiz if temiz else None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"course_id": 1, "user_id": 3, "rating": 5, "comment": "Cok faydali bir kurstu"}
        }
    )


class ReviewUpdate(BaseModel):
    """Mevcut değerlendirmeyi GÜNCELLERKEN beklenen veri (rating + comment)."""

    rating: int = Field(..., ge=1, le=5, description="Yeni puan, 1-5 arası.", examples=[4])
    comment: str | None = Field(default=None, max_length=1000, examples=["Icerik guzel ama biraz hizli"])

    @field_validator("comment")
    @classmethod
    def yorum_temizle(cls, v: str | None) -> str | None:
        if v is None:
            return None
        temiz = v.strip()
        return temiz if temiz else None

    model_config = ConfigDict(
        json_schema_extra={"example": {"rating": 4, "comment": "Icerik guzel ama biraz hizli"}}
    )


class ReviewResponse(BaseModel):
    """Değerlendirmeyi istemciye DÖNDÜRÜRKEN kullanılan model."""

    id: int = Field(..., examples=[1])
    course_id: int = Field(..., examples=[1])
    user_id: int = Field(..., examples=[3])
    rating: int = Field(..., examples=[5])
    comment: str | None = Field(..., examples=["Cok faydali bir kurstu"])
    is_active: bool = Field(..., description="Aktif mi? (TÜRETİLMİŞ: deleted_date IS NULL)", examples=[True])
    created_date: str = Field(..., examples=["2024-03-20 18:00:00"])
    deleted_date: str | None = Field(..., examples=[None])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "course_id": 1,
                "user_id": 3,
                "rating": 5,
                "comment": "Cok faydali bir kurstu",
                "is_active": True,
                "created_date": "2024-03-20 18:00:00",
                "deleted_date": None,
            }
        }
    )
