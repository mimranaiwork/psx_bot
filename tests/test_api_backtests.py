from db import database


def _insert_run(symbol):
    database.insert_backtest_run({
        "symbol": symbol, "start_date": "2026-01-01", "end_date": "2026-06-01",
        "total_trades": 10, "win_rate": 0.5, "sharpe_ratio": 1.0, "max_drawdown": -0.1,
        "strategy_return": 0.2, "baseline_return": 0.1, "notes": "test",
    })


def test_list_backtests_empty(client, test_db):
    resp = client.get("/backtests")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_backtests_filters_by_symbol(client, test_db):
    _insert_run("SYM1")
    _insert_run("SYM2")
    resp = client.get("/backtests", params={"symbol": "SYM1"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "SYM1"


def test_list_backtests_no_filter_returns_all(client, test_db):
    _insert_run("SYM1")
    _insert_run("SYM2")
    resp = client.get("/backtests")
    assert len(resp.json()) == 2
