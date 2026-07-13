"""
Technical model: LightGBM classifier trained on technical indicator
features to predict direction of price move over a fixed horizon.

Uses walk-forward validation, not random train/test split — critical for
time-series data, since random splits leak future information into training.
"""
import sys
import os
import pandas as pd
import numpy as np
import pickle

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from features import technical_features

FEATURE_COLUMNS = [
    "sma_20", "sma_50", "sma_200", "ema_20", "ema_50",
    "rsi_14", "macd", "macd_signal", "macd_hist",
    "bb_width", "atr_14", "volume_spike_ratio",
    "roc_10", "roc_20", "price_vs_sma50", "price_vs_sma200", "sma20_vs_sma50",
]


def prepare_training_data(price_df):
    """
    price_df: raw OHLCV DataFrame from the database.
    Returns (X, y, feature_df) with rows that have complete features/labels.
    """
    df = technical_features.compute_all(price_df)
    df = technical_features.add_forward_return_label(
        df, config.PREDICTION_HORIZON_DAYS, config.MOVE_THRESHOLD_PCT
    )

    # Drop rows with NaN in features or label (indicator warm-up period,
    # and final rows where forward return can't be computed)
    complete = df.dropna(subset=FEATURE_COLUMNS + ["label"])
    X = complete[FEATURE_COLUMNS]
    y = complete["label"]
    return X, y, complete


def train_walk_forward(price_df, symbol):
    """
    Trains a LightGBM classifier using a walk-forward split: the most
    recent WALK_FORWARD_TEST_WINDOW_DAYS rows are held out as a test set,
    everything before that (up to WALK_FORWARD_TRAIN_WINDOW_DAYS) is training.

    Returns (model, test_report) where test_report has out-of-sample metrics.
    """
    import lightgbm as lgb
    from sklearn.metrics import classification_report, accuracy_score

    X, y, complete = prepare_training_data(price_df)

    if len(X) < config.MIN_TRAINING_ROWS:
        raise ValueError(
            f"Not enough data to train ({len(X)} rows, need at least "
            f"{config.MIN_TRAINING_ROWS}). Load more historical data first."
        )

    test_size = min(config.WALK_FORWARD_TEST_WINDOW_DAYS, len(X) // 5)
    train_size = min(config.WALK_FORWARD_TRAIN_WINDOW_DAYS, len(X) - test_size)

    X_train = X.iloc[-(train_size + test_size):-test_size]
    y_train = y.iloc[-(train_size + test_size):-test_size]
    X_test = X.iloc[-test_size:]
    y_test = y.iloc[-test_size:]

    model = lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        num_leaves=15,
        min_child_samples=20,
        random_state=42,
        verbose=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    print(f"[{symbol}] Walk-forward test accuracy: {accuracy:.3f} "
          f"(train={len(X_train)} rows, test={len(X_test)} rows)")

    model_path = os.path.join(config.MODELS_DIR, f"{symbol}_technical_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    return model, {
        "accuracy": accuracy,
        "classification_report": report,
        "train_rows": len(X_train),
        "test_rows": len(X_test),
    }


def load_model(symbol):
    model_path = os.path.join(config.MODELS_DIR, f"{symbol}_technical_model.pkl")
    if not os.path.exists(model_path):
        return None
    with open(model_path, "rb") as f:
        return pickle.load(f)


def predict_latest(symbol, price_df):
    """
    Returns (predicted_class, class_probabilities) for the most recent
    row of available data. predicted_class in {-1, 0, 1}.
    """
    model = load_model(symbol)
    if model is None:
        raise ValueError(f"No trained model found for {symbol}. Run training first.")

    df = technical_features.compute_all(price_df)
    latest = df.dropna(subset=FEATURE_COLUMNS).iloc[[-1]]
    if latest.empty:
        raise ValueError("Not enough data to compute features for the latest row.")

    X_latest = latest[FEATURE_COLUMNS]
    pred_class = model.predict(X_latest)[0]
    pred_proba = model.predict_proba(X_latest)[0]
    class_labels = model.classes_

    proba_dict = dict(zip(class_labels, pred_proba))
    return pred_class, proba_dict
