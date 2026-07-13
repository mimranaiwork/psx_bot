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
