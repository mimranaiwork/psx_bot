"""
CLI entrypoint for the PSX AI Insights Bot.

Usage:
    python main.py init-db
    python main.py demo
    python main.py load-prices --symbol OGDC [--csv path/to/file.csv]
    python main.py load-prices-yfinance --symbol OGDC --yf-ticker OGDC.KA
    python main.py train --symbol OGDC
    python main.py backtest --symbol OGDC
    python main.py signal --symbol OGDC
    python main.py update-outcomes --symbol OGDC
"""
import argparse
import sys
import numpy as np
import pandas as pd

from db import database


def generate_synthetic_data(symbol="DEMO", n_days=1500, seed=42):
    """
    Generates synthetic OHLCV data purely for testing the pipeline
    end-to-end without needing real PSX data. NOT representative of
    real market behavior — for pipeline validation only.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n_days)

    # Random walk with slight upward drift and volatility clustering
    returns = rng.normal(0.0004, 0.015, n_days)
    prices = 100 * np.cumprod(1 + returns)

    rows = []
    for i, date in enumerate(dates):
        close = prices[i]
        open_ = close * (1 + rng.normal(0, 0.005))
        high = max(open_, close) * (1 + abs(rng.normal(0, 0.006)))
        low = min(open_, close) * (1 - abs(rng.normal(0, 0.006)))
        volume = int(rng.integers(50_000, 2_000_000))
        rows.append({
            "date": date.strftime("%Y-%m-%d"),
            "open": round(open_, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": volume,
        })

    database.upsert_price_rows(symbol, rows)
    print(f"Generated {n_days} days of synthetic data for {symbol}")
    return rows


def cmd_init_db(args):
    database.init_db()


def cmd_demo(args):
    """Runs the full pipeline end-to-end on synthetic data."""
    from models import technical_model
    from backtest import backtest_engine

    print("=" * 60)
    print("DEMO MODE: synthetic data only, NOT real PSX prices")
    print("=" * 60)

    database.init_db()
    generate_synthetic_data(symbol="DEMO", n_days=1500)

    price_df = database.get_price_history("DEMO")
    print(f"\nLoaded {len(price_df)} rows of price history.")

    print("\nTraining technical model (walk-forward validated)...")
    model, report = technical_model.train_walk_forward(price_df, "DEMO")
    print(f"Out-of-sample accuracy: {report['accuracy']:.3f}")

    print("\nRunning backtest...")
    metrics, equity_df, trades_df = backtest_engine.run_backtest(price_df, "DEMO")
    print("\nBacktest results:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    print("\nGenerating a sample signal from latest data...")
    from signals import signal_engine
    try:
        result = signal_engine.generate_signal("DEMO")
        print(f"\nSignal: {result['signal']} (confidence: {result['confidence']})")
        print(f"Rationale:\n{result['rationale']}")
    except Exception as e:
        print(f"Signal generation skipped: {e}")

    print("\nDemo complete. Pipeline works end-to-end on synthetic data.")
    print("Next: load real, legally-obtained PSX price data (see README.md) "
          "and re-run train/backtest/signal against a real symbol.")


def cmd_load_prices(args):
    from ingestion import psx_manual_loader
    database.init_db()
    psx_manual_loader.load_csv_to_db(args.symbol, args.csv)


def cmd_load_prices_yfinance(args):
    from ingestion import yfinance_loader
    database.init_db()
    yfinance_loader.load_yfinance_to_db(args.symbol, args.yf_ticker, args.period)


def cmd_load_fundamentals_yfinance(args):
    from ingestion import yfinance_fundamentals_loader
    database.init_db()
    yfinance_fundamentals_loader.load_yfinance_fundamentals(args.symbol, args.yf_ticker)


def cmd_load_news_yfinance(args):
    from ingestion import yfinance_news_loader
    database.init_db()
    yfinance_news_loader.load_yfinance_news(args.symbol, args.yf_ticker)


def cmd_train(args):
    from models import technical_model
    price_df = database.get_price_history(args.symbol)
    if price_df.empty:
        print(f"No data for {args.symbol}. Load prices first.")
        sys.exit(1)
    model, report = technical_model.train_walk_forward(price_df, args.symbol)
    print(f"Training complete. Out-of-sample accuracy: {report['accuracy']:.3f}")


def cmd_backtest(args):
    from backtest import backtest_engine
    price_df = database.get_price_history(args.symbol)
    if price_df.empty:
        print(f"No data for {args.symbol}. Load prices first.")
        sys.exit(1)
    metrics, equity_df, trades_df = backtest_engine.run_backtest(price_df, args.symbol)
    print("Backtest results:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
    database.insert_backtest_run({
        "symbol": args.symbol,
        "start_date": str(price_df["trade_date"].iloc[0]),
        "end_date": str(price_df["trade_date"].iloc[-1]),
        "total_trades": metrics.get("total_trades"),
        "win_rate": metrics.get("win_rate"),
        "sharpe_ratio": metrics.get("sharpe_ratio"),
        "max_drawdown": metrics.get("max_drawdown"),
        "strategy_return": metrics.get("strategy_return"),
        "baseline_return": metrics.get("baseline_return_buy_hold"),
        "notes": "",
    })


def cmd_signal(args):
    from signals import signal_engine
    result = signal_engine.generate_signal(args.symbol)
    print(f"\nSymbol: {result['symbol']}")
    print(f"Signal: {result['signal']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Rationale:\n{result['rationale']}")


def cmd_update_outcomes(args):
    from signals import signal_engine
    updated = signal_engine.update_signal_outcomes(args.symbol)
    print(f"Updated {updated} past signals with actual outcomes.")


def cmd_screen_breakouts(args):
    """Scans every loaded symbol for the pre-breakout 'coiling' setup."""
    import config
    from features import breakout_features

    min_rows = 20 + config.BREAKOUT_SQUEEZE_LOOKBACK_DAYS
    symbols_df = database.get_price_symbols_summary()
    flagged = []
    for symbol in symbols_df["symbol"]:
        price_df = database.get_price_history(symbol)
        if len(price_df) < min_rows:
            continue
        result = breakout_features.get_breakout_signal(symbol, price_df)
        if result.get("is_pre_breakout"):
            flagged.append(result)

    flagged.sort(key=lambda r: (-r["checks_passed"], r["pct_from_high"]))

    if not flagged:
        print("No pre-breakout setups found among currently loaded symbols.")
        return

    print(f"{len(flagged)} pre-breakout candidate(s):\n")
    for r in flagged:
        print(f"  {r['symbol']:10s} checks={r['checks_passed']}/4  "
              f"close={r['close']:.2f}  {r['pct_from_high']:.1%} below high  "
              f"RSI={r['rsi_14']:.1f}  vol_ratio={r['volume_spike_ratio']:.2f}")


def main():
    parser = argparse.ArgumentParser(description="PSX AI Insights Bot CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db")
    sub.add_parser("demo")

    p = sub.add_parser("load-prices")
    p.add_argument("--symbol", required=True)
    p.add_argument("--csv", required=False)

    p = sub.add_parser("load-prices-yfinance")
    p.add_argument("--symbol", required=True)
    p.add_argument("--yf-ticker", required=False)
    p.add_argument("--period", default="5y")

    p = sub.add_parser("load-fundamentals-yfinance")
    p.add_argument("--symbol", required=True)
    p.add_argument("--yf-ticker", required=False)

    p = sub.add_parser("load-news-yfinance")
    p.add_argument("--symbol", required=True)
    p.add_argument("--yf-ticker", required=False)

    p = sub.add_parser("train")
    p.add_argument("--symbol", required=True)

    p = sub.add_parser("backtest")
    p.add_argument("--symbol", required=True)

    p = sub.add_parser("signal")
    p.add_argument("--symbol", required=True)

    p = sub.add_parser("update-outcomes")
    p.add_argument("--symbol", required=True)

    sub.add_parser("screen-breakouts")

    args = parser.parse_args()
    commands = {
        "init-db": cmd_init_db,
        "demo": cmd_demo,
        "load-prices": cmd_load_prices,
        "load-prices-yfinance": cmd_load_prices_yfinance,
        "load-fundamentals-yfinance": cmd_load_fundamentals_yfinance,
        "load-news-yfinance": cmd_load_news_yfinance,
        "train": cmd_train,
        "backtest": cmd_backtest,
        "signal": cmd_signal,
        "update-outcomes": cmd_update_outcomes,
        "screen-breakouts": cmd_screen_breakouts,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
