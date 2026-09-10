from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    user_name: str = Field(min_length=3, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    company_name: str = Field(min_length=2, max_length=180)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SessionResponse(BaseModel):
    user_name: str
    company_name: str


class MeResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    company_id: int
    company_name: str


class PasswordResetIssueRequest(BaseModel):
    email: EmailStr


class PasswordResetIssueResponse(BaseModel):
    reset_token: str
    expires_minutes: int = 15


class PasswordResetConfirmRequest(BaseModel):
    reset_token: str = Field(min_length=32, max_length=4096)
    new_password: str = Field(min_length=8, max_length=128)
