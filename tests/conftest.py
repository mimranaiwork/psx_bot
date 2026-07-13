import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import pytest

import config
from db import database


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    """Isolates every test from the real data/psx_bot.db by pointing
    config.DB_PATH at a fresh temp file and initializing the schema."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(config, "DB_PATH", str(db_path))
    database.init_db()
    yield db_path


@pytest.fixture()
def synthetic_price_rows():
    """Factory for deterministic synthetic OHLCV rows (fixed seed, fixed
    end date so results never depend on when the test runs)."""

    def _make(n_days=700, seed=42, start_price=100.0, drift=0.0006, vol=0.015):
        rng = np.random.default_rng(seed)
        dates = pd.bdate_range(end=pd.Timestamp("2026-06-30"), periods=n_days)
        returns = rng.normal(drift, vol, n_days)
        prices = start_price * np.cumprod(1 + returns)

        rows = []
        for i, date in enumerate(dates):
            close = prices[i]
            open_ = close * (1 + rng.normal(0, 0.005))
            high = max(open_, close) * (1 + abs(rng.normal(0, 0.006)))
            low = min(open_, close) * (1 - abs(rng.normal(0, 0.006)))
            volume = int(rng.integers(50_000, 2_000_000))
            rows.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(open_, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": volume,
            })
        return rows

    return _make


@pytest.fixture()
def loaded_price_history(test_db, synthetic_price_rows):
    """Loads a full synthetic history for symbol TESTSYM into the isolated
    test DB and returns the symbol name."""
    rows = synthetic_price_rows()
    database.upsert_price_rows("TESTSYM", rows)
    return "TESTSYM"


@pytest.fixture()
def client(test_db, tmp_path, monkeypatch):
    """FastAPI TestClient wired to the same isolated test DB, with
    MODELS_DIR redirected too so train/backtest/signal endpoints don't
    write real model pickles during tests."""
    monkeypatch.setattr(config, "MODELS_DIR", str(tmp_path))
    from fastapi.testclient import TestClient
    from api.main import app

    with TestClient(app) as c:
        yield c
