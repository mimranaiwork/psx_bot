import pandas as pd

from features import technical_features


def _price_df_from_rows(rows):
    df = pd.DataFrame(rows)
    return df.rename(columns={"date": "trade_date"})


def test_compute_all_adds_expected_columns(synthetic_price_rows):
    df = _price_df_from_rows(synthetic_price_rows(n_days=300))
    out = technical_features.compute_all(df)
    expected = {
        "sma_20", "sma_50", "sma_200", "ema_20", "ema_50", "rsi_14",
        "macd", "macd_signal", "macd_hist", "bb_mid", "bb_upper", "bb_lower",
        "bb_width", "atr_14", "volume_avg_30", "volume_spike_ratio",
        "roc_10", "roc_20", "price_vs_sma50", "price_vs_sma200", "sma20_vs_sma50",
    }
    assert expected.issubset(out.columns)


def test_compute_all_sorts_by_date_even_if_input_is_shuffled(synthetic_price_rows):
    rows = synthetic_price_rows(n_days=50)[::-1]
    df = _price_df_from_rows(rows)
    out = technical_features.compute_all(df)
    assert out["trade_date"].is_monotonic_increasing


def test_rsi_within_bounds(synthetic_price_rows):
    df = _price_df_from_rows(synthetic_price_rows(n_days=300))
    out = technical_features.compute_all(df)
    valid = out["rsi_14"].dropna()
    assert not valid.empty
    assert (valid >= 0).all() and (valid <= 100).all()


def test_bollinger_bands_ordering_and_width(synthetic_price_rows):
    df = _price_df_from_rows(synthetic_price_rows(n_days=300))
    out = technical_features.compute_all(df)
    valid = out.dropna(subset=["bb_upper", "bb_mid", "bb_lower", "bb_width"])
    assert not valid.empty
    assert (valid["bb_width"] >= 0).all()
    assert (valid["bb_upper"] >= valid["bb_mid"]).all()
    assert (valid["bb_lower"] <= valid["bb_mid"]).all()


def test_atr_non_negative(synthetic_price_rows):
    df = _price_df_from_rows(synthetic_price_rows(n_days=300))
    out = technical_features.compute_all(df)
    assert (out["atr_14"].dropna() >= 0).all()


def test_volume_spike_ratio_is_ratio_to_rolling_average(synthetic_price_rows):
    df = _price_df_from_rows(synthetic_price_rows(n_days=300))
    out = technical_features.compute_all(df)
    valid = out.dropna(subset=["volume_spike_ratio", "volume_avg_30"])
    recomputed = valid["volume"] / valid["volume_avg_30"]
    pd.testing.assert_series_equal(valid["volume_spike_ratio"], recomputed, check_names=False)


def test_forward_return_label_known_cases():
    dates = pd.bdate_range(start="2026-01-01", periods=10)
    closes = [100, 100, 100, 100, 100, 105, 96, 100, 100, 100]
    df = pd.DataFrame({"trade_date": dates, "close": closes})

    labeled = technical_features.add_forward_return_label(
        df, horizon_days=5, move_threshold_pct=0.02
    )

    assert labeled.loc[0, "label"] == 1     # +5% over 5 days -> up
    assert labeled.loc[1, "label"] == -1    # -4% over 5 days -> down
    assert labeled.loc[2, "label"] == 0     # 0% over 5 days -> flat
    assert pd.isna(labeled.loc[9, "forward_return"])  # no data 5 days ahead
