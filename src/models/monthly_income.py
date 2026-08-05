from __future__ import annotations

# MonthlyIncome stores incoming money for a month.
# Examples: salary, bonus, family support, other income.
# Salary PAYE calculations should live in a service later, not directly here.

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class MonthlyIncome(Base):
    __tablename__ = "monthly_incomes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    month: Mapped[date] = mapped_column(Date, nullable=False)
    income_type: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    target_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
