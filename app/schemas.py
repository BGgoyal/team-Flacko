from pydantic import BaseModel, Field


class EmailRegister(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=120)


class EmailLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str


class OtpStart(BaseModel):
    phone: str = Field(min_length=10, max_length=16)


class OtpCheck(BaseModel):
    phone: str = Field(min_length=10, max_length=16)
    code: str = Field(min_length=4, max_length=10)
    name: str = Field(default="", max_length=120)


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    monthly_income: float = Field(ge=0)
    income_type: str = Field(max_length=40)
    monthly_expenses: float = Field(ge=0)
    current_savings: float = Field(ge=0)
    goal_title: str = Field(min_length=1, max_length=200)
    goal_amount: float = Field(ge=0)


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    planned_amount: float = Field(ge=0)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    planned_amount: float | None = Field(default=None, ge=0)


class SipIn(BaseModel):
    goal_amount: float = Field(ge=0)
    monthly_contribution: float = Field(ge=0)
    duration_months: int = Field(ge=1, le=600)
    assumed_return_annual: float = Field(ge=0, le=30)


class CoachIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
