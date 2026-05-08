from decimal import Decimal

from pydantic import EmailStr, Field

from app.enums import UserRole
from app.schemas.common import ORMBaseModel


class UserBase(ORMBaseModel):
    company_id: int | None = None
    active_company_id: int | None = None
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=25)
    email: EmailStr | None = None
    role: UserRole
    clickup_user_id: str | None = Field(default=None, max_length=64)
    weekly_salary: Decimal = Decimal("0.00")
    commission_percentage: Decimal = Decimal("0.00")
    is_active: bool = True
    permissions: dict | None = None
    notes: str | None = None


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(ORMBaseModel):
    company_id: int | None = None
    active_company_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, min_length=7, max_length=25)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: UserRole | None = None
    clickup_user_id: str | None = Field(default=None, max_length=64)
    weekly_salary: Decimal | None = None
    commission_percentage: Decimal | None = None
    is_active: bool | None = None
    permissions: dict | None = None
    notes: str | None = None


class UserSelfUpdate(ORMBaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, min_length=7, max_length=25)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserRead(ORMBaseModel):
    id: int
    company_id: int | None = None
    active_company_id: int | None = None
    name: str
    phone: str | None = None
    email: str | None = None
    role: UserRole
    branch: str = "local"
    clickup_user_id: str | None = None
    weekly_salary: Decimal = Decimal("0.00")
    commission_percentage: Decimal = Decimal("0.00")
    is_active: bool = True
    permissions: dict | None = None
    notes: str | None = None
    google_sub: str | None = None
    privacy_policy_version: str | None = None
