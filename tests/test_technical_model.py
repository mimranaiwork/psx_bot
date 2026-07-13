import os

import pytest

import config
from db import database
from models import technical_model


def test_prepare_training_data_shapes_and_types(loaded_price_history):
    price_df = database.get_price_history(loaded_price_history)
    X, y, complete = technical_model.prepare_training_data(price_df)

    assert len(X) == len(y) == len(complete)
    assert set(technical_model.FEATURE_COLUMNS).issubset(X.columns)
    assert not X.isna().any().any()
    assert y.isin([-1, 0, 1]).all()


def test_train_walk_forward_raises_on_insufficient_data(test_db, synthetic_price_rows):
    rows = synthetic_price_rows(n_days=50)  # well under MIN_TRAINING_ROWS
    database.upsert_price_rows("TINY", rows)
    price_df = database.get_price_history("TINY")

    with pytest.raises(ValueError):
        technical_model.train_walk_forward(price_df, "TINY")


def test_train_walk_forward_end_to_end(loaded_price_history, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MODELS_DIR", str(tmp_path))
    price_df = database.get_price_history(loaded_price_history)

    model, report = technical_model.train_walk_forward(price_df, loaded_price_history)

    assert 0.0 <= report["accuracy"] <= 1.0
    assert report["train_rows"] > 0
    assert report["test_rows"] > 0
    model_path = os.path.join(str(tmp_path), f"{loaded_price_history}_technical_model.pkl")
    assert os.path.exists(model_path)


def test_predict_latest_requires_trained_model(loaded_price_history, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MODELS_DIR", str(tmp_path))
    price_df = database.get_price_history(loaded_price_history)

    with pytest.raises(ValueError):
        technical_model.predict_latest(loaded_price_history, price_df)


def test_predict_latest_after_training(loaded_price_history, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MODELS_DIR", str(tmp_path))
    price_df = database.get_price_history(loaded_price_history)
    technical_model.train_walk_forward(price_df, loaded_price_history)

    pred_class, proba = technical_model.predict_latest(loaded_price_history, price_df)

    assert pred_class in (-1, 0, 1)
    assert abs(sum(proba.values()) - 1.0) < 1e-6
