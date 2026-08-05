from __future__ import annotations

# Shared account type definitions.
# Keep this as the single source of truth so the CLI, dashboard, and services
# all understand the same account categories.

ACCOUNT_TYPE_LABELS = {
    "bank": "Bank Account",
    "high_interest_savings": "High-Interest Savings Account",
    "cash_isa": "Cash ISA",
    "lifetime_isa": "Lifetime ISA",
    "stocks_isa": "Stocks & Shares ISA",
    "trading": "Trading Account",
    "pension": "Pension",
    "debt": "Debt Account",
}

VALID_ACCOUNT_TYPES = set(ACCOUNT_TYPE_LABELS)

# Accounts where start/end snapshots can reveal growth after adjusting for
# transfers. For cash-like accounts, this mainly captures interest or bonuses.
GROWTH_ACCOUNT_TYPES = {
    "high_interest_savings",
    "cash_isa",
    "lifetime_isa",
    "stocks_isa",
    "trading",
    "pension",
}


def account_type_label(account_type: str | None) -> str:
    """Return a professional label for a stored account type value."""
    if account_type is None:
        return ""
    return ACCOUNT_TYPE_LABELS.get(account_type, account_type.replace("_", " ").title())
