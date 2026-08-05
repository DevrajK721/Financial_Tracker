from __future__ import annotations

# Net worth comes from monthly account snapshots.
# End-of-month balances are preferred; start-of-month balances are used as a
# fallback so current balances do not disappear when only a start snapshot exists.
# Assets add to net worth. Debt accounts subtract from net worth.

from datetime import date
from decimal import Decimal

from src.services.snapshot_balances import monthly_account_balances


def calculate_net_worth_details(month: date) -> dict[str, Decimal]:
    """Return assets, debts, and net worth for a month."""
    total_assets = Decimal("0.00")
    total_debts = Decimal("0.00")

    for balance in monthly_account_balances(month):
        if balance.is_debt:
            total_debts += balance.balance
        else:
            total_assets += balance.balance

    return {
        "total_assets": total_assets,
        "total_debts": total_debts,
        "net_worth": total_assets - total_debts,
    }


def calculate_net_worth(month: date) -> Decimal:
    """Return just net worth for callers that only need one number."""
    return calculate_net_worth_details(month)["net_worth"]
