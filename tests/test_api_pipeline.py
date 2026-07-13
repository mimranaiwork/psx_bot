from db import database


# --- load-* endpoints (loader functions mocked -- network calls don't belong in unit tests) --

def test_load_prices_wires_request_through(client, monkeypatch):
    import ingestion.yfinance_loader as yfl
    calls = []
    monkeypatch.setattr(yfl, "load_yfinance_to_db", lambda symbol, yf_ticker, period: calls.append(
        (symbol, yf_ticker, period)
    ) or 42)

    resp = client.post("/symbols/OGDC/load-prices", json={"yf_ticker": "OGDC.KA", "period": "5y"})
    assert resp.status_code == 200
    assert resp.json()["data"]["rows"] == 42
    assert calls == [("OGDC", "OGDC.KA", "5y")]


def test_load_prices_defaults_period(client, monkeypatch):
    import ingestion.yfinance_loader as yfl
    calls = []
    monkeypatch.setattr(yfl, "load_yfinance_to_db", lambda symbol, yf_ticker, period: calls.append(period) or 0)
    client.post("/symbols/OGDC/load-prices", json={})
    assert calls == ["5y"]


def test_load_fundamentals_wires_request_through(client, monkeypatch):
    import ingestion.yfinance_fundamentals_loader as yff
    calls = []
    monkeypatch.setattr(yff, "load_yfinance_fundamentals", lambda symbol, yf_ticker: calls.append(
        (symbol, yf_ticker)
    ) or 4)

    resp = client.post("/symbols/OGDC/load-fundamentals", json={"yf_ticker": "OGDC.KA"})
    assert resp.status_code == 200
    assert resp.json()["data"]["rows"] == 4
    assert calls == [("OGDC", "OGDC.KA")]


def test_load_news_wires_request_through(client, monkeypatch):
    import ingestion.yfinance_news_loader as yfn
    calls = []
    monkeypatch.setattr(yfn, "load_yfinance_news", lambda symbol, yf_ticker: calls.append(
        (symbol, yf_ticker)
    ) or 1)

    resp = client.post("/symbols/OGDC/load-news", json={"yf_ticker": "OGDC.KA"})
    assert resp.status_code == 200
    assert resp.json()["data"]["rows"] == 1


# --- train / backtest / signal / update-outcomes (real synthetic data, full pipeline) --

def test_train_400_when_no_data(client, test_db):
    resp = client.post("/symbols/NOPE/train")
    assert resp.status_code == 400
    assert "No data for NOPE" in resp.json()["detail"]


def test_train_success(client, loaded_price_history):
    resp = client.post(f"/symbols/{loaded_price_history}/train")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert 0.0 <= data["accuracy"] <= 1.0
    assert data["train_rows"] > 0


def test_backtest_400_when_no_data(client, test_db):
    resp = client.post("/symbols/NOPE/backtest")
    assert resp.status_code == 400


def test_backtest_success_persists_run(client, loaded_price_history):
    resp = client.post(f"/symbols/{loaded_price_history}/backtest")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "strategy_return" in data
    assert isinstance(data["beats_baseline"], bool)  # numpy.bool_ correctly sanitized

    runs = database.get_backtest_runs(loaded_price_history)
    assert len(runs) == 1


def test_signal_400_when_no_price_data(client, test_db):
    resp = client.post("/symbols/NOPE/signal")
    assert resp.status_code == 400


def test_signal_400_when_no_trained_model(client, loaded_price_history):
    resp = client.post(f"/symbols/{loaded_price_history}/signal")
    assert resp.status_code == 400
    assert "No trained model" in resp.json()["detail"]


def test_signal_success_after_training(client, loaded_price_history):
    train_resp = client.post(f"/symbols/{loaded_price_history}/train")
    assert train_resp.status_code == 200

    resp = client.post(f"/symbols/{loaded_price_history}/signal")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["signal"] in ("BUY", "HOLD", "SELL")

    logged = database.get_signals_log(loaded_price_history)
    assert len(logged) == 1


def test_update_outcomes_zero_when_nothing_elapsed(client, loaded_price_history):
    resp = client.post(f"/symbols/{loaded_price_history}/update-outcomes")
    assert resp.status_code == 200
    assert resp.json()["data"]["updated"] == 0
