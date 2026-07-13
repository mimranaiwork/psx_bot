# PSX AI Insights Bot

An explainable Buy/Hold/Sell decision-support system for PSX-listed stocks.
Combines technical indicators, fundamental data, company announcements, and an
LLM synthesis layer — with mandatory backtesting and an honest accuracy log.

## ⚠️ Legal notice — read before connecting to live PSX data

PSX's terms of use prohibit automated/bulk collection of their market data
without a written license (see `dps.psx.com.pk` legal notice). This codebase
ships with:

- A **CSV-based loader** for data you've legally obtained (manual download,
  licensed feed, or your own broker export) — use this for PSX data.
- A **Yahoo Finance loader** for prototyping only, since PSX equities are
  covered unofficially there — do not rely on this for production accuracy.

**Do not point the ingestion layer at `dps.psx.com.pk` in an automated way**
until you have written permission from `marketdatarequest@psx.com.pk`. The
`ingestion/psx_manual_loader.py` module assumes you already have the data in
hand (CSV export), not that the code fetches it for you.

## Project layout

```
psx_ai_bot/
  config.py                    Central configuration
  db/
    schema.sql                 Database schema (SQLite by default)
    database.py                DB connection + helper functions
  ingestion/
    psx_manual_loader.py       Load manually-obtained/licensed PSX CSV data
    yfinance_loader.py         Prototype-only loader via Yahoo Finance
    announcement_loader.py     Load announcements from a JSON/CSV export
    financial_report_parser.py Parse financial report PDFs into structured data
  features/
    technical_features.py      SMA/EMA/RSI/MACD/Bollinger/ATR
    fundamental_features.py    EPS growth, margin trend, payout ratio
    event_features.py          Announcement categorization + surprise score
  models/
    technical_model.py         LightGBM classifier, walk-forward trained
    fundamental_rules.py       Rule-based fundamental flag
    llm_synthesis.py           Claude API call to generate plain-language rationale
  backtest/
    backtest_engine.py         Walk-forward backtest with fees/slippage
  signals/
    signal_engine.py           Combines model outputs into Buy/Hold/Sell + confidence
  dashboard/
    app.py                     Streamlit dashboard
  main.py                      CLI orchestration entrypoint
  requirements.txt
```

## Setup

```bash
pip install -r requirements.txt --break-system-packages
python main.py init-db
```

## Quickstart (using sample/synthetic data for testing the pipeline)

```bash
python main.py demo
```

This loads synthetic OHLCV data, computes technical features, trains a
walk-forward-validated model, backtests it against a buy-and-hold baseline,
and prints a sample signal — so you can verify the whole pipeline works
before plugging in real PSX data.

## Using real data

1. Obtain historical EOD data legally (manual PSX download for
   personal/non-commercial use, or a licensed feed).
2. Place CSVs in `data/prices/{SYMBOL}.csv` with columns:
   `date,open,high,low,close,volume`
3. Run: `python main.py load-prices --symbol SYMBOL`
4. Run: `python main.py train --symbol SYMBOL`
5. Run: `python main.py backtest --symbol SYMBOL`
6. Run: `python main.py signal --symbol SYMBOL` for a current signal
7. Launch dashboard: `streamlit run dashboard/app.py`

## Non-negotiable guardrails (see design doc)

- Every signal is probability-weighted decision support, never a guarantee.
- Every signal issued is logged with its actual outcome for accuracy tracking.
- No autonomous trade execution — a human confirms every trade.
- Paper-trade for 3-6 months minimum before using real capital.
