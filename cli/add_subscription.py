from __future__ import annotations

# CLI script for adding a recurring payment such as phone, gym, or streaming.
# These records can later feed projections and subscription reviews.

import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.helpers import VALID_BILLING_FREQUENCIES, VALID_EXPENSE_CATEGORIES, ask_choice, ask_decimal
from src.db import session_scope
from src.models.subscription import Subscription


def parse_optional_date(date_text: str) -> date | None:
    """Convert YYYY-MM-DD text into a date, or None if blank."""
    return None if not date_text else date.fromisoformat(date_text)


def main() -> None:
    name = input("Subscription name: ").strip()
    monthly_amount = ask_decimal("Monthly equivalent amount: ")
    billing_frequency = ask_choice("Billing frequency", VALID_BILLING_FREQUENCIES)
    category = ask_choice("Category", VALID_EXPENSE_CATEGORIES)
    next_payment_date = parse_optional_date(input("Next payment date [YYYY-MM-DD, optional]: ").strip())

    subscription = Subscription(
        name=name,
        monthly_amount=monthly_amount,
        billing_frequency=billing_frequency,
        category=category,
        next_payment_date=next_payment_date,
    )

    with session_scope() as session:
        session.add(subscription)

    print("Subscription added.")


if __name__ == "__main__":
    main()
