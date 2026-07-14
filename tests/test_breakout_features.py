import numpy as np
import pandas as pd

from features import breakout_features


def _coiling_setup_df(seed=0):
    """
    Deterministic OHLCV series that is a textbook pre-breakout setup:
    80 days of wider swings (establishes a trailing high + higher
    volatility baseline), then 60 days of tight consolidation just under
    that high, with a volume bump on the last few days.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end="2026-07-10", periods=140)

    prices = []
    base = 100.0
    for _ in range(80):
        base *= 1 + rng.normal(0.001, 0.02)
        prices.append(base)
    swing_high = max(prices)
    consolidate_base = swing_high * 0.985
    for _ in range(60):
        consolidate_base *= 1 + rng.normal(0.0005, 0.003)
        prices.append(consolidate_base)

    closes = np.array(prices)
    opens = closes * (1 + rng.normal(0, 0.001, len(closes)))
    highs = np.maximum(opens, closes) * 1.003
    lows = np.minimum(opens, closes) * 0.997
    volumes = np.full(len(closes), 500_000)
    volumes[-5:] = 900_000  # volume building at the end

    return pd.DataFrame({
        "trade_date": dates, "open": opens, "high": highs, "low": lows,
        "close": closes, "volume": volumes,
    })


def _flat_random_walk_df(n_days=140, seed=1):
    """A generic random walk -- shouldn't reliably trigger the screener."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end="2026-07-10", periods=n_days)
    returns = rng.normal(0.0002, 0.018, n_days)
    closes = 100 * np.cumprod(1 + returns)
    opens = closes * (1 + rng.normal(0, 0.005, n_days))
    highs = np.maximum(opens, closes) * (1 + abs(rng.normal(0, 0.006, n_days)))
    lows = np.minimum(opens, closes) * (1 - abs(rng.normal(0, 0.006, n_days)))
    volumes = rng.integers(50_000, 2_000_000, n_days)
    return pd.DataFrame({
        "trade_date": dates, "open": opens, "high": highs, "low": lows,
        "close": closes, "volume": volumes,
    })


def test_compute_breakout_features_adds_expected_columns():
    out = breakout_features.compute_breakout_features(_coiling_setup_df())
    assert {"bb_width_percentile", "rolling_high", "pct_from_high"}.issubset(out.columns)


def test_insufficient_data_returns_false():
    tiny_df = _coiling_setup_df().iloc[:30].reset_index(drop=True)
    result = breakout_features.get_breakout_signal("SYM", tiny_df)
    assert result["is_pre_breakout"] is False
    assert result["reason"] == "insufficient_data"


def test_coiling_setup_is_flagged_pre_breakout():
    result = breakout_features.get_breakout_signal("SYM", _coiling_setup_df())
    assert result["is_pre_breakout"] is True
    assert result["checks_passed"] == 4
    assert result["squeeze"] is True
    assert result["near_resistance"] is True
    assert result["volume_building"] is True
    assert result["momentum_ok"] is True
    assert result["symbol"] == "SYM"


def test_result_includes_component_values_for_auditability():
    result = breakout_features.get_breakout_signal("SYM", _coiling_setup_df())
    for key in ("bb_width_percentile", "pct_from_high", "volume_spike_ratio", "rsi_14", "close", "trade_date"):
        assert key in result


def test_generic_random_walk_is_not_flagged():
    # seed=1 verified to produce checks_passed=0 -- a plain random walk
    # with no consolidation/resistance/volume structure shouldn't pass
    # the screener's bar.
    result = breakout_features.get_breakout_signal("SYM", _flat_random_walk_df(seed=1))
    assert result["is_pre_breakout"] is False
