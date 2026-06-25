"""
models/category.py
------------------
CATEGORIES entity'si için Pydantic modelleri.
İlk self-referencing (kendine FK veren) entity: 'parent_id' bir üst kategoriyi
işaret eder; NULL ise kategori bir kök (root) kategoridir.

CATEGORIES kolonları (Excel'e birebir): id, parent_id, name, is_active, created_date.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryCreate(BaseModel):
    """
    Yeni kategori OLUŞTURURKEN beklenen veri.
      - parent_id: opsiyonel. Verilmezse (None) kategori kök olur. Verilirse
        mevcut bir kategoriyi işaret etmelidir (router'da kontrol edilir).
      - name: zorunlu.
    """

    parent_id: int | None = Field(
        default=None,
        description="Üst kategori id'si. Boş bırakılırsa (null) kök kategoridir.",
        examples=[1],
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Kategori adı. Boş olamaz. Örn: Web Gelistirme.",
        examples=["Web Gelistirme"],
    )

    @field_validator("name")
    @classmethod
    def name_bos_olamaz(cls, deger: str) -> str:
        temiz = deger.strip()
        if not temiz:
            raise ValueError("Kategori adı boş olamaz.")
        return temiz

    model_config = ConfigDict(
        json_schema_extra={"example": {"parent_id": 1, "name": "Web Gelistirme"}}
    )


class CategoryUpdate(BaseModel):
    """
    Mevcut kategoriyi GÜNCELLERKEN beklenen veri (parent_id + name).
      - parent_id None gönderilirse kategori köke taşınır.
      - parent_id kategorinin kendi id'sine eşit olamaz (self-loop yasak).
    """

    parent_id: int | None = Field(
        default=None,
        description="Yeni üst kategori id'si. null = köke taşı. Kendi id'sine eşit olamaz.",
        examples=[1],
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Kategorinin yeni adı. Boş olamaz.",
        examples=["Mobil Gelistirme"],
    )

    @field_validator("name")
    @classmethod
    def name_bos_olamaz(cls, deger: str) -> str:
        temiz = deger.strip()
        if not temiz:
            raise ValueError("Kategori adı boş olamaz.")
        return temiz

    model_config = ConfigDict(
        json_schema_extra={"example": {"parent_id": 1, "name": "Mobil Gelistirme"}}
    )


class CategoryResponse(BaseModel):
    """Kategori bilgisini istemciye DÖNDÜRÜRKEN kullanılan model."""

    id: int = Field(..., description="Benzersiz numara (PK).", examples=[2])
    parent_id: int | None = Field(
        ..., description="Üst kategori id'si (kök ise null).", examples=[1]
    )
    name: str = Field(..., description="Kategori adı.", examples=["Web Gelistirme"])
    is_active: bool = Field(..., description="Aktif mi? (true=aktif, false=pasif)", examples=[True])
    created_date: str = Field(
        ..., description="Oluşturulma tarih-saati.", examples=["2024-01-03 10:05:00"]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 2,
                "parent_id": 1,
                "name": "Web Gelistirme",
                "is_active": True,
                "created_date": "2024-01-03 10:05:00",
            }
        }
    )
