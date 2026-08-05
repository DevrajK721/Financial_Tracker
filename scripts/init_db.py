from __future__ import annotations

# Run this script after defining models.
# It imports every model so SQLAlchemy knows the tables exist,
# then calls create_tables() to create them inside finances.db.

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db import create_tables
from src.models.account import Account 
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.models.monthly_income import MonthlyIncome
from src.models.monthly_expense import MonthlyExpense
from src.models.monthly_transfer import MonthlyTransfer
from src.models.debt_profile import DebtProfile
from src.models.goal import Goal
from src.models.monthly_goal_allocation import MonthlyGoalAllocation
from src.models.subscription import Subscription

# TODO: import every model class here as you complete it.
# Example:
# from src.models.account import Account


def main() -> None:
    create_tables()
    print("Database tables created.")


if __name__ == "__main__":
    main()
