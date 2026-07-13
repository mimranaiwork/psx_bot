from db import database


def test_list_symbols_empty(client):
    resp = client.get("/symbols")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_symbols_returns_summary(client, loaded_price_history):
    resp = client.get("/symbols")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symbol"] == loaded_price_history
    assert data[0]["row_count"] == 700


def test_get_symbol_prices_includes_indicators(client, loaded_price_history):
    resp = client.get(f"/symbols/{loaded_price_history}/prices")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 700
    assert "sma_20" in rows[0]
    assert "roc_10" in rows[0]
    # warm-up rows have null indicators, not NaN
    assert rows[0]["sma_200"] is None


def test_get_symbol_prices_404_for_unknown_symbol(client, test_db):
    resp = client.get("/symbols/NOPE/prices")
    assert resp.status_code == 404
