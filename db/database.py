"""
Database access layer. Uses SQLite for portability; swap the connection
function for psycopg2/SQLAlchemy + Postgres in production without touching
calling code, as long as the same table schema is respected.
"""
import sqlite3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables from schema.sql if they don't already exist."""
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    with open(schema_path, "r") as f:
        schema_sql = f.read()
    conn = get_connection()
    try:
        conn.executescript(schema_sql)
        conn.commit()
        print(f"Database initialized at {config.DB_PATH}")
    finally:
        conn.close()


def upsert_price_rows(symbol, rows):
    """
    rows: list of dicts with keys date, open, high, low, close, volume
    Uses INSERT OR REPLACE to make ingestion idempotent (safe to re-run).
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT OR REPLACE INTO price_history
                (symbol, trade_date, open, high, low, close, volume)
            VALUES (:symbol, :trade_date, :open, :high, :low, :close, :volume)
            """,
            [
                {
                    "symbol": symbol,
                    "trade_date": r["date"],
                    "open": r["open"],
                    "high": r["high"],
                    "low": r["low"],
                    "close": r["close"],
                    "volume": r.get("volume", 0),
                }
                for r in rows
            ],
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def get_price_history(symbol):
    import pandas as pd
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM price_history WHERE symbol = ? ORDER BY trade_date ASC",
            conn,
            params=(symbol,),
        )
        return df
    finally:
        conn.close()


def insert_signal(record):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO signals_log
                (symbol, signal_date, signal, confidence, model_probability,
                 fundamental_flag, rationale, horizon_days)
            VALUES (:symbol, :signal_date, :signal, :confidence, :model_probability,
                    :fundamental_flag, :rationale, :horizon_days)
            """,
            record,
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def insert_backtest_run(record):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO backtest_runs
                (symbol, start_date, end_date, total_trades, win_rate,
                 sharpe_ratio, max_drawdown, strategy_return, baseline_return, notes)
            VALUES (:symbol, :start_date, :end_date, :total_trades, :win_rate,
                    :sharpe_ratio, :max_drawdown, :strategy_return, :baseline_return, :notes)
            """,
            record,
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_signals_log(symbol=None):
    import pandas as pd
    conn = get_connection()
    try:
        if symbol:
            df = pd.read_sql_query(
                "SELECT * FROM signals_log WHERE symbol = ? ORDER BY signal_date DESC",
                conn, params=(symbol,),
            )
        else:
            df = pd.read_sql_query("SELECT * FROM signals_log ORDER BY signal_date DESC", conn)
        return df
    finally:
        conn.close()


def get_backtest_runs(symbol=None):
    import pandas as pd
    conn = get_connection()
    try:
        if symbol:
            df = pd.read_sql_query(
                "SELECT * FROM backtest_runs WHERE symbol = ? ORDER BY run_date DESC",
                conn, params=(symbol,),
            )
        else:
            df = pd.read_sql_query("SELECT * FROM backtest_runs ORDER BY run_date DESC", conn)
        return df
    finally:
        conn.close()


def get_price_symbols_summary():
    """One row per symbol loaded in price_history: row count + latest date."""
    import pandas as pd
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            """
            SELECT symbol, COUNT(*) AS row_count, MAX(trade_date) AS latest_date
            FROM price_history
            GROUP BY symbol
            ORDER BY symbol
            """,
            conn,
        )
        return df
    finally:
        conn.close()


def get_latest_signals():
    """Most recent signals_log row per symbol."""
    import pandas as pd
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            """
            SELECT s.* FROM signals_log s
            INNER JOIN (
                SELECT symbol, MAX(signal_date) AS max_date
                FROM signals_log
                GROUP BY symbol
            ) latest ON s.symbol = latest.symbol AND s.signal_date = latest.max_date
            """,
            conn,
        )
        return df
    finally:
        conn.close()
