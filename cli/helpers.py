from __future__ import annotations

# Shared CLI helper functions.
# These keep the data-entry scripts small and make repeated prompts consistent.

from datetime import date
from decimal import Decimal
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.account_types import ACCOUNT_TYPE_LABELS, VALID_ACCOUNT_TYPES, account_type_label
from src.currencies import CURRENCY_LABELS, SUPPORTED_CURRENCIES
from src.models.account import Account


VALID_EXPENSE_CATEGORIES = {"rent", "transport", "food", "gym", "clothing", "phone", "subscriptions", "other"}
VALID_INCOME_TYPES = {"salary", "bonus", "family_support", "other"}
VALID_SNAPSHOT_TYPES = {"start", "end"}
VALID_BILLING_FREQUENCIES = {"monthly", "annual", "weekly"}

T = TypeVar("T")


def parse_month(month_text: str) -> date:
    """Convert YYYY-MM text into a date using the first day of that month."""
    return date.fromisoformat(f"{month_text}-01")


def ask_month(prompt: str = "Month [YYYY-MM]: ") -> date:
    """Prompt until the user enters a valid YYYY-MM month."""
    while True:
        try:
            return parse_month(input(prompt).strip())
        except ValueError:
            print("Please enter a valid month like 2026-08.")


def ask_decimal(prompt: str) -> Decimal:
    """Read a money-like number from input as Decimal, not float."""
    while True:
        try:
            return Decimal(input(prompt).strip())
        except Exception:
            print("Please enter a valid number like 1250.75.")


def ask_optional_text(prompt: str) -> str | None:
    """Return None when the user leaves an optional text field blank."""
    return input(prompt).strip() or None


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    """Prompt for a yes/no answer."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        answer = input(f"{prompt}{suffix}").strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please enter y or n.")


def ask_choice(prompt: str, choices: set[str]) -> str:
    """Prompt until the user enters one of the allowed values."""
    choices_text = "/".join(sorted(choices))
    while True:
        answer = input(f"{prompt} [{choices_text}]: ").strip().lower()
        if answer in choices:
            return answer
        print(f"Please choose one of: {choices_text}.")


def ask_account_type(prompt: str = "Account type") -> str:
    """Ask for an account type using readable labels while storing clean values."""
    choices = list(ACCOUNT_TYPE_LABELS.items())
    print(f"{prompt}:")
    for index, (_, label) in enumerate(choices, start=1):
        print(f"{index}: {label}")

    while True:
        answer = input("Choose number or account type: ").strip().lower()
        if answer.isdigit():
            index = int(answer)
            if 1 <= index <= len(choices):
                return choices[index - 1][0]

        if answer in VALID_ACCOUNT_TYPES:
            return answer

        for value, label in choices:
            if answer == label.lower():
                return value

        print("Please choose a listed number, label, or account type value.")


def ask_currency(prompt: str = "Currency", default: str = "GBP") -> str:
    """Ask for a supported account currency using readable labels."""
    default = default.strip().upper() if default else "GBP"
    choices = list(CURRENCY_LABELS.items())
    print(f"{prompt}:")
    for index, (code, label) in enumerate(choices, start=1):
        default_marker = " [default]" if code == default else ""
        print(f"{index}: {label}{default_marker}")

    while True:
        answer = input("Choose number or currency code: ").strip().upper()
        if not answer:
            return default
        if answer.isdigit():
            index = int(answer)
            if 1 <= index <= len(choices):
                return choices[index - 1][0]
        if answer in SUPPORTED_CURRENCIES:
            return answer

        choices_text = ", ".join(sorted(SUPPORTED_CURRENCIES))
        print(f"Please choose one of: {choices_text}.")


def list_accounts(session: Session) -> list[Account]:
    """Print accounts and return them ordered by name."""
    accounts = session.scalars(select(Account).order_by(Account.name)).all()

    if not accounts:
        print("No accounts found. Add an account first with cli/add_account.py.")
        return []

    print("Accounts:")
    for account in accounts:
        print(f"{account.id}: {account.name} ({account_type_label(account.account_type)})")

    return accounts


def ask_account_id(session: Session, prompt: str = "Account ID: ") -> int | None:
    """Show accounts and return a selected account ID, or None when no accounts exist."""
    accounts = list_accounts(session)
    if not accounts:
        return None

    valid_ids = {account.id for account in accounts}
    while True:
        try:
            account_id = int(input(prompt))
        except ValueError:
            print("Please enter a numeric account ID.")
            continue

        if account_id in valid_ids:
            return account_id

        print("That account ID does not exist.")
