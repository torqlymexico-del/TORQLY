from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    phone: str = Field(min_length=7, max_length=25)
    password: str = Field(min_length=8, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

