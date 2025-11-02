"""User-related Pydantic models."""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nickname: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    email: Optional[EmailStr] = None
    nickname: Optional[str] = None


class UserResponse(BaseModel):
    user_id: str
    email: str
    nickname: Optional[str] = None
    is_admin: bool = False
    created_at: str
