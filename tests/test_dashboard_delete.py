from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from streamlit.testing.v1 import AppTest

from src import db
from src.db import Base
from src.db import session_scope
from src.models.account import Account
from src.models.monthly_account_snapshot import MonthlyAccountSnapshot


def use_file_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Use a file-backed SQLite database because Streamlit AppTest runs in another thread."""
    engine = create_engine(f"sqlite:///{tmp_path / 'dashboard_test.db'}")
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    monkeypatch.setattr(db, "engine", engine)
    monkeypatch.setattr(db, "SessionLocal", TestingSessionLocal)
    Base.metadata.create_all(bind=engine)


def test_delete_account_page_renders_without_exceptions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    use_file_database(monkeypatch, tmp_path)

    with session_scope() as session:
        account = Account(name="Test Bank", account_type="bank", currency="GBP")
        session.add(account)
        session.flush()
        session.add(
            MonthlyAccountSnapshot(
                account_id=account.id,
                month=date(2026, 8, 1),
                snapshot_type="end",
                balance=Decimal("100.00"),
            )
        )

    app = AppTest.from_file("app/dashboard.py")
    app.query_params["page"] = "entries"
    app.query_params["section"] = "delete"
    app.run(timeout=20)

    assert len(app.exception) == 0

    record_type = next(selectbox for selectbox in app.selectbox if selectbox.label == "Record type")
    record_type.select("🏦 Account")
    app.run(timeout=20)

    assert len(app.exception) == 0
    assert len(app.multiselect) == 1

    account_choices = list(app.multiselect[0].options)
    assert account_choices
    app.multiselect[0].select(account_choices[0])
    app.run(timeout=20)

    assert len(app.exception) == 0
    assert any(
        checkbox.label == "Also delete all linked records for the selected account(s)."
        for checkbox in app.checkbox
    )
