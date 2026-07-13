"""
Tests for main.py's CLI command handlers. Each cmd_* function is called
directly with a hand-built argparse.Namespace (fast, precise) for the
logic-level coverage; one test drives main() itself via sys.argv to
cover the argparse parser/dispatch wiring that direct calls skip.

Network-touching subcommands (load-prices-yfinance,
load-fundamentals-yfinance, load-news-yfinance) have their underlying
loader functions monkeypatched out -- we're verifying main.py wires
arguments through correctly, not re-testing the (already network-bound,
untested-by-design) yfinance loaders themselves.
"""
import argparse

import pytest

import config
import main
from db import database


def _ns(**kwargs):
    return argparse.Namespace(**kwargs)


# --- init-db / demo -----------------------------------------------------

def test_cmd_init_db_creates_schema(test_db):
    main.cmd_init_db(_ns())
    conn = database.get_connection()
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert {"price_history", "signals_log", "backtest_runs"}.issubset(tables)


def test_cmd_demo_runs_full_pipeline(test_db, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MODELS_DIR", str(tmp_path))
    main.cmd_demo(_ns())

    price_df = database.get_price_history("DEMO")
    assert len(price_df) == 1500

    signals_df = database.get_signals_log("DEMO")
    assert len(signals_df) == 1
    assert signals_df.iloc[0]["signal"] in ("BUY", "HOLD", "SELL")


def test_cmd_demo_survives_signal_generation_failure(test_db, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "MODELS_DIR", str(tmp_path))
    import signals.signal_engine as se
    monkeypatch.setattr(se, "generate_signal", lambda symbol: (_ for _ in ()).throw(ValueError("boom")))

    main.cmd_demo(_ns())  # must not raise -- cmd_demo catches and prints instead

    assert "Signal generation skipped: boom" in capsys.readouterr().out


# --- load-prices (CSV) ----------------------------------------------------

def test_cmd_load_prices_from_csv(test_db, tmp_path):
    csv_path = tmp_path / "SYM.csv"
    csv_path.write_text(
        "date,open,high,low,close,volume\n"
        "2026-01-01,10.0,10.5,9.5,10.2,100000\n"
        "2026-01-02,10.2,10.8,10.0,10.6,120000\n"
    )
    main.cmd_load_prices(_ns(symbol="SYM", csv=str(csv_path)))

    df = database.get_price_history("SYM")
    assert len(df) == 2
    assert df.iloc[0]["close"] == 10.2


# --- yfinance-backed loaders (mocked, args-wiring only) --------------------

def test_cmd_load_prices_yfinance_wires_args_through(test_db, monkeypatch):
    import ingestion.yfinance_loader as yfl
    calls = []
    monkeypatch.setattr(yfl, "load_yfinance_to_db", lambda symbol, yf_ticker, period: calls.append(
        (symbol, yf_ticker, period)
    ))
    main.cmd_load_prices_yfinance(_ns(symbol="OGDC", yf_ticker="OGDC.KA", period="5y"))
    assert calls == [("OGDC", "OGDC.KA", "5y")]


def test_cmd_load_fundamentals_yfinance_wires_args_through(test_db, monkeypatch):
    import ingestion.yfinance_fundamentals_loader as yff
    calls = []
    monkeypatch.setattr(yff, "load_yfinance_fundamentals", lambda symbol, yf_ticker: calls.append(
        (symbol, yf_ticker)
    ))
    main.cmd_load_fundamentals_yfinance(_ns(symbol="OGDC", yf_ticker="OGDC.KA"))
    assert calls == [("OGDC", "OGDC.KA")]


def test_cmd_load_news_yfinance_wires_args_through(test_db, monkeypatch):
    import ingestion.yfinance_news_loader as yfn
    calls = []
    monkeypatch.setattr(yfn, "load_yfinance_news", lambda symbol, yf_ticker: calls.append(
        (symbol, yf_ticker)
    ))
    main.cmd_load_news_yfinance(_ns(symbol="OGDC", yf_ticker="OGDC.KA"))
    assert calls == [("OGDC", "OGDC.KA")]


# --- train / backtest / signal / update-outcomes ---------------------------

def test_cmd_train_exits_when_no_data(test_db, capsys):
    with pytest.raises(SystemExit) as exc_info:
        main.cmd_train(_ns(symbol="NOPE"))
    assert exc_info.value.code == 1
    assert "No data for NOPE" in capsys.readouterr().out


def test_cmd_train_success(loaded_price_history, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "MODELS_DIR", str(tmp_path))
    main.cmd_train(_ns(symbol=loaded_price_history))
    assert "Training complete" in capsys.readouterr().out


def test_cmd_backtest_exits_when_no_data(test_db):
    with pytest.raises(SystemExit) as exc_info:
        main.cmd_backtest(_ns(symbol="NOPE"))
    assert exc_info.value.code == 1


def test_cmd_backtest_success_persists_run(loaded_price_history, capsys):
    main.cmd_backtest(_ns(symbol=loaded_price_history))
    assert "Backtest results" in capsys.readouterr().out

    conn = database.get_connection()
    row = conn.execute(
        "SELECT * FROM backtest_runs WHERE symbol = ?", (loaded_price_history,)
    ).fetchone()
    conn.close()
    assert row is not None


def test_cmd_signal_success(loaded_price_history, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "MODELS_DIR", str(tmp_path))
    main.cmd_train(_ns(symbol=loaded_price_history))
    capsys.readouterr()  # drain training output

    main.cmd_signal(_ns(symbol=loaded_price_history))
    out = capsys.readouterr().out
    assert "Signal:" in out
    assert len(database.get_signals_log(loaded_price_history)) == 1


def test_cmd_update_outcomes_reports_zero_when_nothing_elapsed(loaded_price_history, capsys):
    main.cmd_update_outcomes(_ns(symbol=loaded_price_history))
    assert "Updated 0 past signals" in capsys.readouterr().out


# --- main() dispatch / argparse wiring --------------------------------------

def test_main_dispatches_init_db_via_argv(test_db, monkeypatch):
    monkeypatch.setattr("sys.argv", ["main.py", "init-db"])
    main.main()
    conn = database.get_connection()
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "price_history" in tables


def test_main_dispatches_train_via_argv_with_symbol_flag(loaded_price_history, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "MODELS_DIR", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["main.py", "train", "--symbol", loaded_price_history])
    main.main()
    assert "Training complete" in capsys.readouterr().out


def test_main_requires_a_subcommand(test_db, monkeypatch):
    monkeypatch.setattr("sys.argv", ["main.py"])
    with pytest.raises(SystemExit):
        main.main()
