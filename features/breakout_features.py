"""
Pre-breakout screener: flags symbols showing a classic "coiling" setup --
tight volatility (Bollinger Band squeeze) near recent resistance, with
volume starting to build and momentum not yet overextended.

This is a rule-based pattern *screener*, not a prediction: it identifies
a technical setup that often precedes breakouts, not a guarantee one
follows. See backtest/breakout_backtest.py for a historical check on
how often this setup has actually led anywhere before trusting it.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from features import technical_features


def compute_breakout_features(price_df):
    """
    price_df: raw OHLCV DataFrame from the database.
    Returns technical_features.compute_all()'s output with two extra
    columns: bb_width_percentile (this bar's Bollinger width vs. its own
    trailing history) and pct_from_high (distance below the trailing
    rolling high, i.e. "resistance").
    """
    df = technical_features.compute_all(price_df)
    df = df.sort_values("trade_date").reset_index(drop=True)

    df["bb_width_percentile"] = df["bb_width"].rolling(
        config.BREAKOUT_SQUEEZE_LOOKBACK_DAYS
    ).rank(pct=True)

    df["rolling_high"] = df["close"].rolling(
        config.BREAKOUT_RESISTANCE_LOOKBACK_DAYS
    ).max()
    df["pct_from_high"] = (df["rolling_high"] - df["close"]) / df["rolling_high"]

    return df


def get_breakout_signal(symbol, price_df):
    """
    Returns a dict describing whether `symbol` currently looks like a
    pre-breakout setup, plus the individual component checks so the
    result is auditable rather than a black-box flag.
    """
    df = compute_breakout_features(price_df)

    required = ["bb_width_percentile", "pct_from_high", "volume_spike_ratio", "rsi_14"]
    if df.empty or df.iloc[-1][required].isna().any():
        return {"symbol": symbol, "is_pre_breakout": False, "reason": "insufficient_data"}

    latest = df.iloc[-1]

    squeeze = bool(latest["bb_width_percentile"] <= config.BREAKOUT_SQUEEZE_PERCENTILE)
    near_resistance = bool(latest["pct_from_high"] <= config.BREAKOUT_RESISTANCE_PCT)
    volume_building = bool(latest["volume_spike_ratio"] >= config.BREAKOUT_VOLUME_RATIO)
    momentum_ok = bool(config.BREAKOUT_RSI_MIN <= latest["rsi_14"] <= config.BREAKOUT_RSI_MAX)

    checks_passed = sum([squeeze, near_resistance, volume_building, momentum_ok])
    is_pre_breakout = checks_passed >= config.BREAKOUT_MIN_CHECKS

    return {
        "symbol": symbol,
        "is_pre_breakout": is_pre_breakout,
        "checks_passed": checks_passed,
        "squeeze": squeeze,
        "near_resistance": near_resistance,
        "volume_building": volume_building,
        "momentum_ok": momentum_ok,
        "bb_width_percentile": round(float(latest["bb_width_percentile"]), 4),
        "pct_from_high": round(float(latest["pct_from_high"]), 4),
        "volume_spike_ratio": round(float(latest["volume_spike_ratio"]), 4),
        "rsi_14": round(float(latest["rsi_14"]), 2),
        "close": float(latest["close"]),
        "trade_date": str(latest["trade_date"])[:10],
    }
