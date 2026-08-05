from __future__ import annotations

# Currency support for the finance tracker.
# Amounts are stored in the native account currency, then converted to GBP for
# dashboard totals, net worth, debts, and projections.


BASE_CURRENCY = "GBP"

CURRENCY_LABELS = {
    "GBP": "GBP - British Pound",
    "USD": "USD - US Dollar",
    "EUR": "EUR - Euro",
    "CNY": "CNY - Chinese Yuan",
    "JPY": "JPY - Japanese Yen",
    "INR": "INR - Indian Rupee",
    "MYR": "MYR - Malaysian Ringgit",
}

SUPPORTED_CURRENCIES = set(CURRENCY_LABELS)


def normalise_currency(currency: str | None) -> str:
    """Return an uppercase currency code, defaulting blank values to GBP."""
    return (currency or BASE_CURRENCY).strip().upper()


def validate_currency(currency: str | None) -> str:
    """Return a supported currency code or raise a clear error."""
    code = normalise_currency(currency)
    if code not in SUPPORTED_CURRENCIES:
        choices = ", ".join(sorted(SUPPORTED_CURRENCIES))
        raise ValueError(f"Unsupported currency '{code}'. Supported currencies are: {choices}.")
    return code
