"""
models/blacklist.py
-------------------
BLACKLIST entity'si için Pydantic modelleri (kara liste).

BLACKLIST kolonları (Excel'e birebir): id, user_id, banned_by, reason,
ban_until, is_active, created_date.

ban_until: NULL/boş ise SÜRESİZ yasak. Doluysa 'YYYY-MM-DD' veya
'YYYY-MM-DD HH:MM:SS' formatında olmalı; normalize edilip tam tarih-saat olarak
saklanır.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _ban_until_normalize(value: str) -> str:
    """
    ban_until metnini doğrular ve 'YYYY-MM-DD HH:MM:SS' biçimine normalize eder.
    Yalnızca tarih verilirse saat 00:00:00 kabul edilir.
    """
    stripped = value.strip()
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(stripped, pattern)
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    raise ValueError("ban_until 'YYYY-MM-DD' veya 'YYYY-MM-DD HH:MM:SS' formatında olmalıdır.")


class BlacklistCreate(BaseModel):
    """Kullanıcıyı kara listeye ALIRKEN beklenen veri."""

    user_id: int = Field(..., description="Yasaklanan kullanıcının id'si.", examples=[6])
    banned_by: int = Field(..., description="Yasağı uygulayan kullanıcının id'si.", examples=[1])
    reason: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Yasak gerekçesi. Boş olamaz (FR12 acc3).",
        examples=["Spam icerik paylasimi"],
    )
    ban_until: str | None = Field(
        default=None,
        description="Yasağın bitişi (YYYY-MM-DD veya tam tarih-saat). Boş = süresiz.",
        examples=["2024-12-31 00:00:00"],
    )

    @field_validator("reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Gerekçe (reason) boş olamaz.")
        return stripped

    @field_validator("ban_until")
    @classmethod
    def ban_until_valid(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _ban_until_normalize(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 6,
                "banned_by": 1,
                "reason": "Spam icerik paylasimi",
                "ban_until": None,
            }
        }
    )


class BlacklistResponse(BaseModel):
    """Kara liste kaydını istemciye DÖNDÜRÜRKEN kullanılan model."""

    id: int = Field(..., examples=[1])
    user_id: int = Field(..., examples=[6])
    banned_by: int = Field(..., examples=[1])
    reason: str = Field(..., examples=["Spam icerik paylasimi"])
    ban_until: str | None = Field(..., description="Bitiş (süresizse null).", examples=[None])
    is_active: bool = Field(..., description="Kayıt aktif mi? (kaldırılmadıysa true)", examples=[True])
    is_valid: bool = Field(
        ...,
        description="Yasak ŞU AN geçerli mi? (TÜRETİLMİŞ: is_active VE süresi geçmemiş).",
        examples=[True],
    )
    created_date: str = Field(..., examples=["2024-05-15 09:00:00"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": 6,
                "banned_by": 1,
                "reason": "Spam icerik paylasimi",
                "ban_until": None,
                "is_active": True,
                "is_valid": True,
                "created_date": "2024-05-15 09:00:00",
            }
        }
    )
