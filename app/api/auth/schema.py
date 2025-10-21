from typing import Literal
from uuid import UUID

from pydantic import EmailStr, field_validator

from ...core.security import validate_password
from ...database.models.account import AdminRole
from ..global_schema import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    token: str


class LoginInformation(BaseModel):
    name: str
    email: EmailStr
    phone_number: str
    uuid: UUID
    account_type: Literal["volunteer", "general_user"]


class AdminLoginInformation(BaseModel):
    name: str
    email: EmailStr
    phone_number: str
    uuid: UUID
    role: AdminRole


class LoginCredentials(BaseModel):
    email: EmailStr
    password: str


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    def validate_new_password(cls, value: str):
        return validate_password(value)


class RefreshToken(BaseModel):
    refresh_token: str
    token_type: str = "bearer"


# Password Reset Schemas
class OTPSendRequest(BaseModel):
    email: EmailStr


class OTPSentResponseData(BaseModel):
    otp_sent: bool


class OTPVerifyRequest(BaseModel):
    otp: int


class OTPVerifiedResponseData(BaseModel):
    otp_verified: bool


class PasswordResetRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    def validate_new_password(cls, value: str):
        return validate_password(value)


class PasswordResetResponseData(BaseModel):
    message: str
