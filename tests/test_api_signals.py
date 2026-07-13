from db import database


def _insert_signal(symbol, signal_date, signal="BUY"):
    database.insert_signal({
        "symbol": symbol, "signal_date": signal_date, "signal": signal,
        "confidence": "High", "model_probability": 0.8, "fundamental_flag": "neutral",
        "rationale": "test", "horizon_days": 5,
    })


def test_symbol_signal_404_when_none_logged(client, test_db):
    resp = client.get("/symbols/NOPE/signal")
    assert resp.status_code == 404


def test_symbol_signal_returns_most_recent(client, test_db):
    _insert_signal("SYM", "2026-01-01", "SELL")
    _insert_signal("SYM", "2026-07-01", "BUY")
    resp = client.get("/symbols/SYM/signal")
    assert resp.status_code == 200
    assert resp.json()["signal"] == "BUY"


def test_signals_log_filters_by_symbol(client, test_db):
    _insert_signal("SYM1", "2026-07-01")
    _insert_signal("SYM2", "2026-07-01")
    resp = client.get("/signals-log", params={"symbol": "SYM1"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "SYM1"


def test_signals_log_no_filter_returns_all(client, test_db):
    _insert_signal("SYM1", "2026-07-01")
    _insert_signal("SYM2", "2026-07-01")
    resp = client.get("/signals-log")
    assert len(resp.json()) == 2


def test_latest_signals_one_row_per_symbol(client, test_db):
    _insert_signal("SYM", "2026-01-01", "SELL")
    _insert_signal("SYM", "2026-07-01", "BUY")
    _insert_signal("OTHER", "2026-07-01", "HOLD")
    resp = client.get("/signals/latest")
    data = resp.json()
    assert len(data) == 2
    by_symbol = {row["symbol"]: row["signal"] for row in data}
    assert by_symbol == {"SYM": "BUY", "OTHER": "HOLD"}
