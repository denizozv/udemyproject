"""
models/auth.py
--------------
FR2 (giriş / login) için istek ve sonuç modelleri.

NOT: Bu sürümde token/JWT YOKTUR. Login yalnızca kimliği doğrular ve kullanıcının
aktif rollerini döndürür. Endpoint bazlı yetkilendirme (her isteğin rolünü
kontrol etme) ayrı bir kapsamdır ve burada uygulanmaz.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    """Giriş isteği (FR2 acc1): mail + password."""

    mail: str = Field(..., min_length=1, description="E-posta.", examples=["ahmet@elearning.com"])
    password: str = Field(..., min_length=1, description="Şifre.", examples=["GizliSifre123"])
    confirm_reactivation: bool = Field(
        default=False,
        description="Silinmiş hesabı yeniden etkinleştirmeyi onaylamak için true (FR2 acc7).",
        examples=[False],
    )

    @field_validator("mail")
    @classmethod
    def mail_normalize(cls, v: str) -> str:
        return v.strip().lower()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"mail": "ahmet@elearning.com", "password": "GizliSifre123", "confirm_reactivation": False}
        }
    )


class LoginResult(BaseModel):
    """Giriş sonucu."""

    success: bool = Field(..., description="Giriş başarılı mı?", examples=[True])
    reactivation_required: bool = Field(
        ...,
        description="Hesap silinmiş ve saklama süresi içinde; onay (confirm_reactivation) gerekiyor mu? (FR2 acc6)",
        examples=[False],
    )
    user_id: int | None = Field(..., examples=[1])
    full_name: str | None = Field(..., examples=["Ahmet Yilmaz"])
    mail: str | None = Field(..., examples=["ahmet@elearning.com"])
    roles: list[str] = Field(..., description="Kullanıcının aktif rolleri (FR2 acc10).", examples=[["Student", "Instructor"]])
    token: str | None = Field(
        default=None,
        description="Bearer token. Sonraki isteklerde 'Authorization: Bearer <token>' olarak gönderilir. (Başarısız/onay bekleyen girişte null.)",
        examples=["nE3v...QwZ"],
    )
    message: str = Field(..., examples=["Giriş başarılı."])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "reactivation_required": False,
                "user_id": 1,
                "full_name": "Ahmet Yilmaz",
                "mail": "ahmet@elearning.com",
                "roles": ["Student", "Instructor"],
                "message": "Giriş başarılı.",
            }
        }
    )
