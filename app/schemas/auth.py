from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    phone: str = Field(min_length=7, max_length=25)
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=25)
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

