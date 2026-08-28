import re
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field, model_validator

COMMON_PASSWORDS = {"password", "password1", "12345678", "qwertyui", "letmein1"}

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str
    full_name: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def check_password(self):
        if self.password != self.password_confirm:
            raise ValueError("passwords do not match")
        if self.password.lower() in COMMON_PASSWORDS:
            raise ValueError("password is too common")
        if not re.search(r"[A-Za-z]", self.password) or not re.search(r"[0-9]", self.password):
            raise ValueError("password must contain letters and numbers")
        return self

class SignupResponse(BaseModel):
    status: Literal["confirmation_sent"]
    email: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str

    @model_validator(mode="after")
    def check_password(self):
        if self.password != self.password_confirm:
            raise ValueError("passwords do not match")
        if self.password.lower() in COMMON_PASSWORDS:
            raise ValueError("password is too common")
        if not re.search(r"[A-Za-z]", self.password) or not re.search(r"[0-9]", self.password):
            raise ValueError("password must contain letters and numbers")
        return self

class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    timezone: str
    role: str

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserProfile
