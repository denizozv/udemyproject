"""
models/course_instructor.py
---------------------------
COURSE_INSTRUCTORS entity'si için Pydantic modelleri (kurs↔eğitmen bağlantısı).

COURSE_INSTRUCTORS kolonları (Excel'e birebir): id, course_id, instructor_id,
is_primary, created_date, deleted_date.
NOT: is_active kolonu yoktur; cevapta 'is_active' TÜRETİLMİŞTİR (deleted_date IS NULL).
"""

from pydantic import BaseModel, ConfigDict, Field


class CourseInstructorCreate(BaseModel):
    """Bir kursa eğitmen ATARKEN beklenen veri."""

    course_id: int = Field(..., description="Kurs id'si.", examples=[1])
    instructor_id: int = Field(..., description="Eğitmen (aktif Instructor rolü olan kullanıcı) id'si.", examples=[1])
    is_primary: bool = Field(
        default=False,
        description="Kursun birincil eğitmeni mi? Kurs başına en fazla 1 aktif primary olabilir.",
        examples=[True],
    )

    model_config = ConfigDict(
        json_schema_extra={"example": {"course_id": 1, "instructor_id": 1, "is_primary": True}}
    )


class CourseInstructorResponse(BaseModel):
    """Kurs-eğitmen atamasını istemciye DÖNDÜRÜRKEN kullanılan model."""

    id: int = Field(..., examples=[1])
    course_id: int = Field(..., examples=[1])
    instructor_id: int = Field(..., examples=[1])
    is_primary: bool = Field(..., examples=[True])
    is_active: bool = Field(..., description="Atama aktif mi? (TÜRETİLMİŞ: deleted_date IS NULL)", examples=[True])
    created_date: str = Field(..., examples=["2024-02-01 12:00:00"])
    deleted_date: str | None = Field(..., examples=[None])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "course_id": 1,
                "instructor_id": 1,
                "is_primary": True,
                "is_active": True,
                "created_date": "2024-02-01 12:00:00",
                "deleted_date": None,
            }
        }
    )
