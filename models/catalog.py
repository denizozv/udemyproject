"""
models/catalog.py
-----------------
FR4 (kurs listeleme/filtreleme) ve FR5 (kurs detayı) için zengin okuma modelleri.

Bu modeller birden fazla tablodan (COURSES + REVIEWS + COURSE_INSTRUCTORS +
ORDER_ITEMS) türetilmiş bilgiler taşır; salt-okunurdur (kayıt oluşturmaz).
"""

from pydantic import BaseModel, ConfigDict, Field


class InstructorBrief(BaseModel):
    """Kurs detayında eğitmen özeti."""

    instructor_id: int = Field(..., examples=[1])
    full_name: str = Field(..., examples=["Ahmet Yilmaz"])
    is_primary: bool = Field(..., examples=[True])


class ReviewBrief(BaseModel):
    """Kurs detayında değerlendirme özeti (aktif değerlendirmeler)."""

    id: int = Field(..., examples=[1])
    user_id: int = Field(..., examples=[3])
    rating: int = Field(..., examples=[5])
    comment: str | None = Field(..., examples=["Cok faydali bir kurstu"])
    created_date: str = Field(..., examples=["2024-03-20 18:00:00"])


class CourseCard(BaseModel):
    """
    Katalogda (FR4 acc9) bir kurs kartı. average_rating aktif değerlendirmelerden
    hesaplanır (acc10); aktif değerlendirme yoksa null.
    """

    id: int = Field(..., examples=[1])
    course_name: str = Field(..., examples=["Spring Boot ile REST API"])
    category_id: int = Field(..., examples=[2])
    language_id: int = Field(..., examples=[1])
    difficulty_id: int = Field(..., examples=[2])
    price: float = Field(..., examples=[499.9])
    primary_instructor: str | None = Field(..., description="Birincil eğitmenin adı (yoksa null).", examples=["Ahmet Yilmaz"])
    average_rating: float | None = Field(..., description="Aktif değerlendirme ortalaması (yoksa null).", examples=[4.5])
    review_count: int = Field(..., description="Aktif değerlendirme sayısı.", examples=[12])


class CourseCatalogPage(BaseModel):
    """Sayfalanmış katalog sonucu (FR4 acc8: sayfa başına 12)."""

    items: list[CourseCard]
    page: int = Field(..., examples=[1])
    page_size: int = Field(..., examples=[12])
    total: int = Field(..., description="Filtreye uyan toplam kurs sayısı.", examples=[37])
    total_pages: int = Field(..., examples=[4])
    sort: str = Field(..., description="Uygulanan sıralama.", examples=["popularity"])


class CourseDetail(BaseModel):
    """Kurs detay görünümü (FR5): kurs + ortalama puan + eğitmenler + aktif yorumlar."""

    id: int = Field(..., examples=[1])
    course_name: str = Field(..., examples=["Spring Boot ile REST API"])
    description: str | None = Field(..., examples=["Sifirdan REST API gelistirme"])
    price: float = Field(..., examples=[499.9])
    category_id: int = Field(..., examples=[2])
    language_id: int = Field(..., examples=[1])
    difficulty_id: int = Field(..., examples=[2])
    is_active: bool = Field(..., examples=[True])
    average_rating: float | None = Field(..., examples=[4.5])
    review_count: int = Field(..., examples=[12])
    instructors: list[InstructorBrief] = Field(..., description="Aktif eğitmenler.")
    reviews: list[ReviewBrief] = Field(..., description="Aktif değerlendirmeler.")
