from db import database


def test_init_db_creates_all_tables(test_db):
    conn = database.get_connection()
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    expected = {"price_history", "announcements", "financial_reports", "signals_log", "backtest_runs"}
    assert expected.issubset(tables)


def test_upsert_price_rows_is_idempotent(test_db):
    rows = [{"date": "2026-01-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 1000}]
    database.upsert_price_rows("SYM", rows)
    database.upsert_price_rows("SYM", rows)  # re-run must not duplicate

    df = database.get_price_history("SYM")
    assert len(df) == 1
    assert df.iloc[0]["close"] == 1.5


def test_upsert_price_rows_overwrites_on_same_date(test_db):
    database.upsert_price_rows("SYM", [
        {"date": "2026-01-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 1000},
    ])
    database.upsert_price_rows("SYM", [
        {"date": "2026-01-01", "open": 1, "high": 2, "low": 0.5, "close": 9.9, "volume": 2000},
    ])
    df = database.get_price_history("SYM")
    assert len(df) == 1
    assert df.iloc[0]["close"] == 9.9


def test_get_price_history_orders_ascending_by_date(test_db):
    rows = [
        {"date": "2026-01-03", "open": 1, "high": 1, "low": 1, "close": 3, "volume": 100},
        {"date": "2026-01-01", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 100},
        {"date": "2026-01-02", "open": 1, "high": 1, "low": 1, "close": 2, "volume": 100},
    ]
    database.upsert_price_rows("SYM", rows)
    df = database.get_price_history("SYM")
    assert list(df["close"]) == [1, 2, 3]


def test_get_price_history_empty_for_unknown_symbol(test_db):
    df = database.get_price_history("NOPE")
    assert df.empty


def test_insert_and_get_signals_log(test_db):
    record = {
        "symbol": "SYM", "signal_date": "2026-07-01", "signal": "BUY", "confidence": "High",
        "model_probability": 0.8, "fundamental_flag": "positive", "rationale": "test",
        "horizon_days": 5,
    }
    signal_id = database.insert_signal(record)
    assert signal_id is not None

    df = database.get_signals_log("SYM")
    assert len(df) == 1
    assert df.iloc[0]["signal"] == "BUY"

    all_df = database.get_signals_log()
    assert len(all_df) == 1


def test_insert_backtest_run(test_db):
    record = {
        "symbol": "SYM", "start_date": "2026-01-01", "end_date": "2026-06-01",
        "total_trades": 10, "win_rate": 0.5, "sharpe_ratio": 1.0, "max_drawdown": -0.1,
        "strategy_return": 0.2, "baseline_return": 0.1, "notes": "test",
    }
    run_id = database.insert_backtest_run(record)
    assert run_id is not None
