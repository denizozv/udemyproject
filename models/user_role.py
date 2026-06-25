"""
models/user_role.py
-------------------
USER_ROLES entity'si için Pydantic modelleri (kullanıcı↔rol bağlantısı).

USER_ROLES kolonları (Excel'e birebir): id, user_id, role_id, created_date, deleted_date.
NOT: Bu tabloda is_active kolonu yoktur. Cevapta kolaylık olsun diye 'is_active'
TÜRETİLMİŞ (deleted_date IS NULL) bir bilgi olarak gösterilir.
"""

from pydantic import BaseModel, ConfigDict, Field


class UserRoleCreate(BaseModel):
    """Bir kullanıcıya rol ATARKEN beklenen veri: user_id + role_id."""

    user_id: int = Field(..., description="Rol atanacak kullanıcının id'si.", examples=[1])
    role_id: int = Field(..., description="Atanacak rolün id'si (aktif olmalı).", examples=[2])

    model_config = ConfigDict(json_schema_extra={"example": {"user_id": 1, "role_id": 2}})


class UserRoleResponse(BaseModel):
    """Kullanıcı-rol atamasını istemciye DÖNDÜRÜRKEN kullanılan model."""

    id: int = Field(..., examples=[1])
    user_id: int = Field(..., examples=[1])
    role_id: int = Field(..., examples=[2])
    is_active: bool = Field(
        ..., description="Atama aktif mi? (TÜRETİLMİŞ: deleted_date IS NULL).", examples=[True]
    )
    created_date: str = Field(..., examples=["2024-01-05 09:20:00"])
    deleted_date: str | None = Field(
        ..., description="Rol kaldırılma tarihi (aktifse null).", examples=[None]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": 1,
                "role_id": 2,
                "is_active": True,
                "created_date": "2024-01-05 09:20:00",
                "deleted_date": None,
            }
        }
    )
