from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src import db
from src.db import Base
from src.models.account import Account
from src.models.debt_profile import DebtProfile
from src.models.goal import Goal
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.models.monthly_expense import MonthlyExpense
from src.models.monthly_goal_allocation import MonthlyGoalAllocation
from src.models.monthly_income import MonthlyIncome
from src.models.monthly_transfer import MonthlyTransfer
from src.models.subscription import Subscription


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch: pytest.MonkeyPatch):
    """Use a fresh in-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "SessionLocal", TestingSessionLocal)

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


__all__ = [
    "Account",
    "DebtProfile",
    "Goal",
    "MonthlyAccountSnapshot",
    "MonthlyExpense",
    "MonthlyGoalAllocation",
    "MonthlyIncome",
    "MonthlyTransfer",
    "Subscription",
]
