from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    profile: Mapped["MoneyProfile | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    categories: Mapped[list["BudgetCategory"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sip: Mapped["SipPlan | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="sessions")


class MoneyProfile(Base):
    __tablename__ = "money_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    monthly_income: Mapped[float] = mapped_column(Float, default=0)
    income_type: Mapped[str] = mapped_column(String(40), default="salary")
    monthly_expenses: Mapped[float] = mapped_column(Float, default=0)
    current_savings: Mapped[float] = mapped_column(Float, default=0)
    goal_title: Mapped[str] = mapped_column(String(200), default="")
    goal_amount: Mapped[float] = mapped_column(Float, default=0)

    user: Mapped[User] = relationship(back_populates="profile")


class BudgetCategory(Base):
    __tablename__ = "budget_categories"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_category"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    planned_amount: Mapped[float] = mapped_column(Float, default=0)

    user: Mapped[User] = relationship(back_populates="categories")


class SipPlan(Base):
    __tablename__ = "sip_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    goal_amount: Mapped[float] = mapped_column(Float, default=0)
    monthly_contribution: Mapped[float] = mapped_column(Float, default=0)
    duration_months: Mapped[int] = mapped_column(Integer, default=12)
    assumed_return_annual: Mapped[float] = mapped_column(Float, default=0)

    user: Mapped[User] = relationship(back_populates="sip")


class MarketCache(Base):
    __tablename__ = "market_cache"

    cache_key: Mapped[str] = mapped_column(String(80), primary_key=True)
    payload_json: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), default="ok")
    message: Mapped[str] = mapped_column(String(400), default="")
