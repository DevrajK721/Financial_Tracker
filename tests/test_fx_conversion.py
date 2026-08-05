from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.db import session_scope
from src.models.account import Account
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot
from src.services import fx
from src.services.dashboard_data import account_balances
from src.services.fx import FxRate, convert_to_gbp
from src.services.net_worth import calculate_net_worth_details


def test_fx_conversion_uses_cached_fetched_rate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(fx, "FX_CACHE_PATH", tmp_path / "fx_rates.json")

    def fake_fetch(currency: str) -> FxRate:
        return FxRate(currency, "GBP", Decimal("0.80"), "2026-08-05", "Test")

    monkeypatch.setattr(fx, "fetch_rate_to_gbp", fake_fetch)

    converted = convert_to_gbp(Decimal("100.00"), "USD")
    assert converted.native_amount == Decimal("100.00")
    assert converted.native_currency == "USD"
    assert converted.gbp_amount == Decimal("80.00")
    assert converted.rate_to_gbp == Decimal("0.80")

    cached = convert_to_gbp(Decimal("50.00"), "USD")
    assert cached.gbp_amount == Decimal("40.00")


def test_usd_snapshot_contributes_to_net_worth_in_gbp(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    month = date(2026, 8, 1)
    monkeypatch.setattr(fx, "FX_CACHE_PATH", tmp_path / "fx_rates.json")

    def fake_fetch(currency: str) -> FxRate:
        return FxRate(currency, "GBP", Decimal("0.75"), "2026-08-05", "Test")

    monkeypatch.setattr(fx, "fetch_rate_to_gbp", fake_fetch)

    with session_scope() as session:
        account = Account(name="US Broker", account_type="trading", currency="USD")
        session.add(account)
        session.flush()
        session.add(
            MonthlyAccountSnapshot(
                account_id=account.id,
                month=month,
                balance=Decimal("1000.00"),
                snapshot_type="end",
            )
        )

    details = calculate_net_worth_details(month)
    balances = account_balances(month)

    assert details["total_assets"] == Decimal("750.00")
    assert details["net_worth"] == Decimal("750.00")
    assert balances[0]["currency"] == "USD"
    assert balances[0]["native_balance"] == 1000.00
    assert balances[0]["balance"] == 750.00
    assert balances[0]["fx_rate_to_gbp"] == 0.75
