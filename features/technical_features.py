"""
Computes technical indicators from OHLCV price history.
Implemented directly with pandas (no ta-lib dependency, which can be
tricky to install) so this runs reliably in any environment.
"""
import pandas as pd
import numpy as np


def compute_all(df):
    """
    df: DataFrame with columns [trade_date, open, high, low, close, volume],
        sorted ascending by trade_date.
    Returns df with technical indicator columns appended.
    """
    df = df.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values("trade_date").reset_index(drop=True)

    df["sma_20"] = df["close"].rolling(20).mean()
    df["sma_50"] = df["close"].rolling(50).mean()
    df["sma_200"] = df["close"].rolling(200).mean()
    df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()

    df["rsi_14"] = _rsi(df["close"], period=14)

    macd_line, signal_line, macd_hist = _macd(df["close"])
    df["macd"] = macd_line
    df["macd_signal"] = signal_line
    df["macd_hist"] = macd_hist

    bb_mid, bb_upper, bb_lower = _bollinger_bands(df["close"], period=20)
    df["bb_mid"] = bb_mid
    df["bb_upper"] = bb_upper
    df["bb_lower"] = bb_lower
    df["bb_width"] = (bb_upper - bb_lower) / bb_mid

    df["atr_14"] = _atr(df, period=14)

    df["volume_avg_30"] = df["volume"].rolling(30).mean()
    df["volume_spike_ratio"] = df["volume"] / df["volume_avg_30"]

    # Trend/momentum features: RSI/MACD/Bollinger are mean-reversion
    # oriented and gave the model near-zero edge on PSX's trending regime
    # (see backtest diagnosis). These give it something trend-following
    # to learn from instead.
    df["roc_10"] = df["close"].pct_change(10)
    df["roc_20"] = df["close"].pct_change(20)
    df["price_vs_sma50"] = (df["close"] - df["sma_50"]) / df["sma_50"]
    df["price_vs_sma200"] = (df["close"] - df["sma_200"]) / df["sma_200"]
    df["sma20_vs_sma50"] = (df["sma_20"] - df["sma_50"]) / df["sma_50"]

    # Forward return (used as training label, NOT a feature — don't feed
    # this back into the model or you'll leak the target)
    return df


def _rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def _macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _bollinger_bands(series, period=20, num_std=2):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return mid, upper, lower


def _atr(df, period=14):
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(period).mean()


def add_forward_return_label(df, horizon_days, move_threshold_pct):
    """
    Adds a 'label' column: 1 (up), -1 (down), 0 (flat/no clear move) based
    on forward return over `horizon_days`. Used ONLY for model training —
    never available at prediction time, so must be dropped before inference.
    """
    df = df.copy()
    df["forward_return"] = df["close"].shift(-horizon_days) / df["close"] - 1
    df["label"] = 0
    df.loc[df["forward_return"] > move_threshold_pct, "label"] = 1
    df.loc[df["forward_return"] < -move_threshold_pct, "label"] = -1
    return df
