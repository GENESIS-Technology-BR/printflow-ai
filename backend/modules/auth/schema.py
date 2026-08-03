from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    user_name: str = Field(min_length=3, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    company_name: str = Field(min_length=2, max_length=180)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_name: str
    company_name: str


class MeResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    company_id: int
    company_name: str
