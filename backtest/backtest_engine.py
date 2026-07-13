"""
Backtesting engine — walk-forward validated, includes brokerage fees and
slippage, and always compares against a buy-and-hold baseline. A strategy
that doesn't beat buy-and-hold after costs is not adding value.
"""
import sys
import os
import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from features import technical_features
from models import technical_model


def run_backtest(price_df, symbol, retrain_every_days=60):
    """
    Simulates trading using rolling walk-forward model retraining:
    every `retrain_every_days`, retrain on all data up to that point, then
    trade the next window using out-of-sample predictions only.

    Returns a dict of performance metrics plus the equity curve.
    """
    df = technical_features.compute_all(price_df)
    df = technical_features.add_forward_return_label(
        df, config.PREDICTION_HORIZON_DAYS, config.MOVE_THRESHOLD_PCT
    )
    df = df.dropna(subset=technical_model.FEATURE_COLUMNS + ["label"]).reset_index(drop=True)

    if len(df) < config.MIN_TRAINING_ROWS + retrain_every_days:
        raise ValueError(
            f"Not enough data for backtesting ({len(df)} rows). Need at least "
            f"{config.MIN_TRAINING_ROWS + retrain_every_days} rows of complete features."
        )

    import lightgbm as lgb

    initial_train_size = config.MIN_TRAINING_ROWS
    position = 0          # 0 = flat, 1 = long
    cash = 1.0             # normalized starting capital
    equity_curve = []
    trade_log = []
    entry_price = None

    i = initial_train_size
    while i < len(df) - config.PREDICTION_HORIZON_DAYS:
        train_end = i
        train_start = max(0, train_end - config.WALK_FORWARD_TRAIN_WINDOW_DAYS)
        train_slice = df.iloc[train_start:train_end]

        model = lgb.LGBMClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.05,
            num_leaves=15, min_child_samples=20, random_state=42, verbose=-1,
        )
        model.fit(train_slice[technical_model.FEATURE_COLUMNS], train_slice["label"])

        test_end = min(i + retrain_every_days, len(df) - config.PREDICTION_HORIZON_DAYS)
        for j in range(i, test_end):
            row = df.iloc[[j]]
            pred = model.predict(row[technical_model.FEATURE_COLUMNS])[0]
            price_today = df.iloc[j]["close"]
            date_today = df.iloc[j]["trade_date"]

            # Simple long-only strategy: go long on bullish prediction,
            # exit only on an explicit bearish prediction (stay long
            # through "flat" predictions rather than churning out of
            # trending positions — see backtest diagnosis: exiting on
            # any non-"up" signal kept time-in-market to ~30% during a
            # secular PSX rally). No shorting (PSX short selling has its
            # own regulatory constraints not modeled here).
            if position == 0 and pred == 1:
                position = 1
                entry_price = price_today * (1 + config.SLIPPAGE_PCT)
                cash -= cash * (config.BROKERAGE_FEE_PCT + config.CDC_FEE_PCT)
                trade_log.append({"date": date_today, "action": "BUY", "price": entry_price})

            elif position == 1 and pred == -1:
                exit_price = price_today * (1 - config.SLIPPAGE_PCT)
                trade_return = (exit_price - entry_price) / entry_price
                cash *= (1 + trade_return)
                cash -= cash * (config.BROKERAGE_FEE_PCT + config.CDC_FEE_PCT)
                trade_log.append({"date": date_today, "action": "SELL", "price": exit_price,
                                   "trade_return": trade_return})
                position = 0
                entry_price = None

            equity_curve.append({"date": date_today, "equity": cash if position == 0
                                  else cash * (price_today / entry_price)})

        i = test_end

    equity_df = pd.DataFrame(equity_curve)
    trades_df = pd.DataFrame(trade_log)

    metrics = _compute_metrics(equity_df, trades_df, df)
    return metrics, equity_df, trades_df


def _compute_metrics(equity_df, trades_df, price_df):
    if equity_df.empty:
        return {"error": "No equity curve generated — insufficient data or no trades triggered."}

    strategy_return = equity_df["equity"].iloc[-1] / equity_df["equity"].iloc[0] - 1

    baseline_start = price_df["close"].iloc[config.MIN_TRAINING_ROWS]
    baseline_end = price_df["close"].iloc[-config.PREDICTION_HORIZON_DAYS - 1]
    baseline_return = baseline_end / baseline_start - 1

    daily_returns = equity_df["equity"].pct_change().dropna()
    sharpe_ratio = (
        (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
        if daily_returns.std() > 0 else 0.0
    )

    cummax = equity_df["equity"].cummax()
    drawdown = (equity_df["equity"] - cummax) / cummax
    max_drawdown = drawdown.min()

    completed_trades = trades_df[trades_df["action"] == "SELL"] if not trades_df.empty else pd.DataFrame()
    win_rate = (
        (completed_trades["trade_return"] > 0).mean()
        if not completed_trades.empty else None
    )

    return {
        "strategy_return": round(strategy_return, 4),
        "baseline_return_buy_hold": round(baseline_return, 4),
        "beats_baseline": strategy_return > baseline_return,
        "sharpe_ratio": round(sharpe_ratio, 3),
        "max_drawdown": round(max_drawdown, 4),
        "total_trades": len(completed_trades),
        "win_rate": round(win_rate, 3) if win_rate is not None else None,
    }
