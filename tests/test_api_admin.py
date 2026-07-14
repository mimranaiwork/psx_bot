from db import database


def test_import_prices_fails_closed_when_admin_token_unset(client, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    resp = client.post(
        "/admin/symbols/OGDC/import-prices",
        json={"rows": [{"date": "2026-01-01", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 100}]},
        headers={"X-Admin-Token": "anything"},
    )
    assert resp.status_code == 503


def test_import_prices_rejects_missing_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret123")
    resp = client.post(
        "/admin/symbols/OGDC/import-prices",
        json={"rows": [{"date": "2026-01-01", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 100}]},
    )
    assert resp.status_code == 403


def test_import_prices_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret123")
    resp = client.post(
        "/admin/symbols/OGDC/import-prices",
        json={"rows": [{"date": "2026-01-01", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 100}]},
        headers={"X-Admin-Token": "wrong"},
    )
    assert resp.status_code == 403


def test_import_prices_succeeds_with_correct_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret123")
    resp = client.post(
        "/admin/symbols/OGDC/import-prices",
        json={"rows": [
            {"date": "2026-01-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 1000},
            {"date": "2026-01-02", "open": 1.5, "high": 2.5, "low": 1, "close": 2, "volume": 2000},
        ]},
        headers={"X-Admin-Token": "secret123"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["rows"] == 2

    df = database.get_price_history("OGDC")
    assert len(df) == 2
    assert df.iloc[0]["close"] == 1.5


def test_import_fundamentals_succeeds_with_correct_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret123")
    resp = client.post(
        "/admin/symbols/OGDC/import-fundamentals",
        json={"rows": [
            {"period": "Q1", "report_date": "2026-01-01", "eps": 1.0, "revenue": 100, "net_profit": 10, "dividend_per_share": 0.5},
        ]},
        headers={"X-Admin-Token": "secret123"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["rows"] == 1

    conn = database.get_connection()
    row = conn.execute("SELECT * FROM financial_reports WHERE symbol = 'OGDC'").fetchone()
    conn.close()
    assert row is not None
    assert row["eps"] == 1.0
    assert row["source_pdf"] == "bulk-import"


def test_import_backtests_succeeds_with_correct_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret123")
    resp = client.post(
        "/admin/symbols/OGDC/import-backtests",
        json={"rows": [
            {"start_date": "2021-01-01", "end_date": "2026-01-01", "total_trades": 25,
             "win_rate": 0.72, "sharpe_ratio": 0.7, "max_drawdown": -0.3,
             "strategy_return": 0.66, "baseline_return": 4.2, "notes": "test"},
        ]},
        headers={"X-Admin-Token": "secret123"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["rows"] == 1

    runs = database.get_backtest_runs("OGDC")
    assert len(runs) == 1
    assert runs.iloc[0]["strategy_return"] == 0.66


def test_import_signals_succeeds_with_correct_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret123")
    resp = client.post(
        "/admin/symbols/OGDC/import-signals",
        json={"rows": [
            {"signal_date": "2026-07-13", "signal": "HOLD", "confidence": "Moderate",
             "model_probability": 0.66, "fundamental_flag": "insufficient_data",
             "rationale": "test rationale", "horizon_days": 5,
             "actual_forward_return": 0.02, "outcome_correct": 1},
        ]},
        headers={"X-Admin-Token": "secret123"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["rows"] == 1

    logged = database.get_signals_log("OGDC")
    assert len(logged) == 1
    assert logged.iloc[0]["signal"] == "HOLD"
    assert logged.iloc[0]["actual_forward_return"] == 0.02
    assert logged.iloc[0]["outcome_correct"] == 1


def test_import_backtests_rejects_missing_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret123")
    resp = client.post(
        "/admin/symbols/OGDC/import-backtests",
        json={"rows": [{"strategy_return": 0.1}]},
    )
    assert resp.status_code == 403


def test_import_signals_rejects_missing_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret123")
    resp = client.post(
        "/admin/symbols/OGDC/import-signals",
        json={"rows": [{"signal_date": "2026-07-13", "signal": "HOLD", "confidence": "Low"}]},
    )
    assert resp.status_code == 403
