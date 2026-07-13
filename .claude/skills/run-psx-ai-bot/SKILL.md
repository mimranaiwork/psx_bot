---
name: run-psx-ai-bot
description: Build, install, and run the PSX AI Insights Bot — the CLI (main.py), the FastAPI backend (api/main.py), and the React web portal (web/). Init the DB, run the synthetic-data demo pipeline, train/backtest/signal for a symbol, load a CSV of price data, run the test suite, or launch the full web portal. Use when asked to run, start, demo, or verify this project.
---

Three ways to drive this project: the CLI (`main.py`, no server needed),
the FastAPI backend (`api/main.py`, thin HTTP wrapper over the same
pipeline modules), and the React web portal (`web/`, talks to the API).
The web portal is the primary way to use this project now — see "Run
(web portal)" below. All paths are relative to the repo root (the
directory containing `main.py`).

## Prerequisites

Just Python 3 with `venv` (verified against Python 3.14.6, macOS). No
system packages beyond that were needed — `pip install -r requirements.txt`
built everything (including `lightgbm`) from wheels with no compiler step.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
```

## Run (agent path)

Use the smoke driver — it exercises the full CLI surface in one shot:
`init-db` → `demo` (synthetic-data pipeline) → `train`/`backtest`/`signal`/
`update-outcomes` against the `DEMO` symbol the demo created → `load-prices`
from a sample CSV. Idempotent; safe to re-run.

```bash
bash .claude/skills/run-psx-ai-bot/driver.sh
```

Expect ~15s of installs then output ending in `=== smoke run complete ===`.
The `demo` step is the most representative single command if you just need
to confirm the pipeline works — it runs DB init, synthetic data generation,
walk-forward training, backtest, and signal generation in one call:

```bash
source .venv/bin/activate
python main.py demo
```

Individual subcommands (after `demo` or `load-prices` has populated a
symbol):

| command | what it does |
|---|---|
| `python main.py init-db` | Creates `data/psx_bot.db` (SQLite) and schema |
| `python main.py demo` | Synthetic data → train → backtest → signal, all in one |
| `python main.py load-prices --symbol X --csv path.csv` | Loads OHLCV CSV (cols: `date,open,high,low,close,volume`) into the DB |
| `python main.py train --symbol X` | Walk-forward trains the LightGBM technical model |
| `python main.py backtest --symbol X` | Runs the walk-forward backtest, prints + persists metrics |
| `python main.py signal --symbol X` | Prints current Buy/Hold/Sell signal + rationale |
| `python main.py update-outcomes --symbol X` | Back-fills actual outcomes for past signals |

Data lands in `data/psx_bot.db` (SQLite), `data/prices/`, `data/models/`.

## Run (web portal)

Two processes: the FastAPI backend and the Vite dev server. Run each in
its own terminal (or background them).

```bash
# terminal 1 -- backend, port 8000
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000

# terminal 2 -- frontend, port 5173 (falls back to 5174+ if taken)
cd web
npm install   # first time only
npm run dev
```

Open the URL Vite prints (`http://localhost:5173` or whatever port it
picked). Pages: `/` (symbol browser + latest signal per symbol),
`/symbols/:symbol` (price chart with SMA/RSI/MACD panes, signal card,
latest backtest, pipeline controls to load data/train/backtest/generate
a signal for that symbol), `/backtests` (sortable leaderboard across all
loaded symbols), `/signals-log` (historical accuracy log).

API docs (auto-generated): `http://localhost:8000/docs`.

**If Vite picks a port other than 5173**, add it to
`allow_origins` in `api/main.py`'s CORS middleware — only 5173/5174 are
allowlisted by default.

## Run (human path, CLI only)

Same CLI commands as above, run interactively. For the older Streamlit
dashboard (superseded by the web portal, not covered by the driver, and
untested in this headless pass):

```bash
source .venv/bin/activate
streamlit run dashboard/app.py
```

## Test

```bash
source .venv/bin/activate
pytest -q
# with coverage:
pytest -q --cov=. --cov-report=term-missing
```

119 tests, all isolated from `data/psx_bot.db` via a per-test temp
SQLite file (see `tests/conftest.py`'s `test_db` fixture, which
monkeypatches `config.DB_PATH`; the `client` fixture wraps a FastAPI
`TestClient` around the same isolated DB for the `test_api_*.py`
files). Covers technical features/model, backtest engine, fundamental
features/rules, event features, the signal engine's decision table
(including the events negative-hint veto), the DB layer, announcement
categorization, the LLM rationale template fallback, every `main.py` CLI
command, and every API router (symbols/signals/backtests/pipeline).
Runs in ~15s; safe to re-run anytime without touching real data.

## Gotchas

- `requirements.txt` pins old lower bounds (e.g. `pandas>=2.0.0`,
  `numpy>=1.24.0`) but pip resolved current versions against Python 3.14.6
  (pandas 3.0.3, numpy 2.5.1, lightgbm 4.6.0, streamlit 1.59.2) with no
  conflicts. If a future run pulls a version that breaks, pin exact
  versions rather than assuming the lower bounds are load-bearing.
- The LLM rationale layer (`models/llm_synthesis.py`) needs
  `ANTHROPIC_API_KEY` set; without it, `signal` silently falls back to a
  template-based rationale — this is expected, not a bug, and is what the
  driver exercises (no key set).
- `demo` always uses symbol `DEMO` and reseeds it deterministically (fixed
  RNG seed), so re-running `demo` overwrites the same rows rather than
  accumulating.
- The synthetic-data backtest legitimately loses money (~-28% vs -0.5%
  buy-and-hold, accuracy ~0.35) — that's a random walk with no real edge,
  not a broken pipeline. Don't mistake bad demo metrics for a bug.
- `backtest_engine`'s metrics dict is full of numpy scalar types
  (`numpy.float64`, `numpy.bool_`), which FastAPI's JSON encoder can't
  serialize directly (`beats_baseline` in particular, since it's a
  numpy-vs-numpy comparison, not a plain Python bool). `api/routers/pipeline.py`
  has a `_sanitize()` helper that recursively calls `.item()` on anything
  with that method before returning — reuse it for any new endpoint that
  passes pipeline output straight through.
- Vite's default port 5173 may already be taken locally (e.g. by Docker
  Desktop) — it silently falls back to 5174+. If that happens, the
  backend's CORS `allow_origins` needs the new port added (see above) or
  requests from the frontend will fail with a CORS error, not a 4xx/5xx.
