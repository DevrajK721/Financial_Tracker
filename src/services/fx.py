from __future__ import annotations

# Foreign exchange conversion helpers.
# The app keeps account snapshots in their native currency, then converts to GBP
# when calculating dashboard totals. Rates are cached locally so the dashboard
# can keep working when the API is temporarily unavailable.

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from src.currencies import BASE_CURRENCY, validate_currency


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FX_CACHE_PATH = PROJECT_ROOT / "data" / "runtime" / "fx_rates.json"
FRANKFURTER_API = "https://api.frankfurter.dev/v2"
FX_CACHE_MAX_AGE_SECONDS = 6 * 60 * 60
MONEY = Decimal("0.01")


class FxRateError(RuntimeError):
    """Raised when a non-GBP amount cannot be converted safely."""


@dataclass(frozen=True)
class FxRate:
    from_currency: str
    to_currency: str
    rate: Decimal
    rate_date: str
    provider: str = "Frankfurter"


@dataclass(frozen=True)
class FxConversion:
    native_amount: Decimal
    native_currency: str
    gbp_amount: Decimal
    rate_to_gbp: Decimal
    rate_date: str
    provider: str


def money_decimal(amount: Decimal) -> Decimal:
    """Round money to pounds and pence."""
    return amount.quantize(MONEY, rounding=ROUND_HALF_UP)


def load_cache() -> dict:
    """Load cached FX rates from local runtime storage."""
    if not FX_CACHE_PATH.exists():
        return {}
    try:
        return json.loads(FX_CACHE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def save_cache(cache: dict) -> None:
    """Persist cached FX rates locally."""
    FX_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FX_CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True))


def cache_key(from_currency: str, to_currency: str = BASE_CURRENCY) -> str:
    return f"latest:{from_currency}:{to_currency}"


def cached_rate(from_currency: str, to_currency: str = BASE_CURRENCY, *, max_age_seconds: int | None) -> FxRate | None:
    """Return a cached rate if present and fresh enough."""
    row = load_cache().get(cache_key(from_currency, to_currency))
    if not row:
        return None

    fetched_at = float(row.get("fetched_at", 0))
    if max_age_seconds is not None and time.time() - fetched_at > max_age_seconds:
        return None

    try:
        return FxRate(
            from_currency=row["from_currency"],
            to_currency=row["to_currency"],
            rate=Decimal(str(row["rate"])),
            rate_date=str(row["rate_date"]),
            provider=str(row.get("provider", "Frankfurter")),
        )
    except (KeyError, ValueError):
        return None


def write_cached_rate(rate: FxRate) -> None:
    """Store a fetched rate in the local cache."""
    cache = load_cache()
    cache[cache_key(rate.from_currency, rate.to_currency)] = {
        "from_currency": rate.from_currency,
        "to_currency": rate.to_currency,
        "rate": str(rate.rate),
        "rate_date": rate.rate_date,
        "provider": rate.provider,
        "fetched_at": time.time(),
    }
    save_cache(cache)


def fetch_rate_to_gbp(currency: str) -> FxRate:
    """Fetch the latest supported currency to GBP rate from Frankfurter."""
    from_currency = validate_currency(currency)
    if from_currency == BASE_CURRENCY:
        return FxRate(BASE_CURRENCY, BASE_CURRENCY, Decimal("1"), date.today().isoformat())

    url = f"{FRANKFURTER_API}/rate/{from_currency}/{BASE_CURRENCY}"
    request = urllib.request.Request(url, headers={"User-Agent": "Finances-Tracker/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"), parse_float=Decimal)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise FxRateError(f"Could not fetch {from_currency} to GBP exchange rate.") from exc

    try:
        return FxRate(
            from_currency=from_currency,
            to_currency=BASE_CURRENCY,
            rate=Decimal(str(payload["rate"])),
            rate_date=str(payload["date"]),
        )
    except KeyError as exc:
        raise FxRateError(f"Frankfurter returned an invalid {from_currency} to GBP response.") from exc


def get_rate_to_gbp(currency: str) -> FxRate:
    """Return the latest cached/fetched rate from a supported currency to GBP."""
    from_currency = validate_currency(currency)
    if from_currency == BASE_CURRENCY:
        return FxRate(BASE_CURRENCY, BASE_CURRENCY, Decimal("1"), date.today().isoformat())

    fresh = cached_rate(from_currency, max_age_seconds=FX_CACHE_MAX_AGE_SECONDS)
    if fresh is not None:
        return fresh

    try:
        fetched = fetch_rate_to_gbp(from_currency)
    except FxRateError:
        stale = cached_rate(from_currency, max_age_seconds=None)
        if stale is not None:
            return stale
        raise

    write_cached_rate(fetched)
    return fetched


def convert_to_gbp(amount: Decimal, currency: str) -> FxConversion:
    """Convert a native-currency amount into GBP using the latest available rate."""
    native_currency = validate_currency(currency)
    rate = get_rate_to_gbp(native_currency)
    return FxConversion(
        native_amount=amount,
        native_currency=native_currency,
        gbp_amount=money_decimal(amount * rate.rate),
        rate_to_gbp=rate.rate,
        rate_date=rate.rate_date,
        provider=rate.provider,
    )
