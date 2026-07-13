-- PSX AI Insights Bot — database schema
-- SQLite by default (production: swap for PostgreSQL + TimescaleDB, same schema)

CREATE TABLE IF NOT EXISTS price_history (
    symbol TEXT NOT NULL,
    trade_date TEXT NOT NULL,   -- ISO format YYYY-MM-DD
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    PRIMARY KEY (symbol, trade_date)
);

CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    announced_at TEXT NOT NULL,
    category TEXT,              -- earnings, dividend, bonus, rights, director_dealing, mgmt_change, other
    raw_text TEXT,
    source_url TEXT,
    ingested_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS financial_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    period TEXT,                -- e.g. "Q3 FY26"
    report_date TEXT,
    eps REAL,
    revenue REAL,
    net_profit REAL,
    dividend_per_share REAL,
    source_pdf TEXT
);

CREATE TABLE IF NOT EXISTS signals_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    signal_date TEXT NOT NULL,
    signal TEXT NOT NULL,           -- BUY / HOLD / SELL
    confidence TEXT NOT NULL,       -- LOW / MODERATE / HIGH
    model_probability REAL,
    fundamental_flag TEXT,
    rationale TEXT,
    horizon_days INTEGER,
    actual_forward_return REAL,     -- filled in later once horizon has elapsed
    outcome_correct INTEGER,        -- 1/0/NULL, filled in later
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS backtest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    run_date TEXT DEFAULT CURRENT_TIMESTAMP,
    start_date TEXT,
    end_date TEXT,
    total_trades INTEGER,
    win_rate REAL,
    sharpe_ratio REAL,
    max_drawdown REAL,
    strategy_return REAL,
    baseline_return REAL,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_price_symbol_date ON price_history(symbol, trade_date);
CREATE INDEX IF NOT EXISTS idx_announcements_symbol ON announcements(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_symbol_date ON signals_log(symbol, signal_date);
