from __future__ import annotations

# Account represents a real place where money sits or debt exists.
# Examples: Monzo, Cash ISA, Stocks ISA, Pension, Student Loan.
# Do not make separate BankAccount/ISA/Pension classes yet.
# Use account_type to distinguish them.

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    is_emergency_fund: Mapped[bool] = mapped_column(nullable=False, default=False)
