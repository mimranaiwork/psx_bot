from db import database
from tests.test_breakout_features import _coiling_setup_df, _flat_random_walk_df


def test_screen_breakouts_empty_when_no_symbols_loaded(client, test_db):
    resp = client.get("/screener/breakouts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_screen_breakouts_flags_coiling_setup(client, test_db):
    rows = _coiling_setup_df().rename(columns={"trade_date": "date"})
    rows["date"] = rows["date"].dt.strftime("%Y-%m-%d")
    database.upsert_price_rows("COIL", rows.to_dict("records"))

    resp = client.get("/screener/breakouts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "COIL"
    assert data[0]["is_pre_breakout"] is True


def test_screen_breakouts_excludes_non_setups_by_default(client, test_db):
    rows = _flat_random_walk_df(seed=1).rename(columns={"trade_date": "date"})
    rows["date"] = rows["date"].dt.strftime("%Y-%m-%d")
    database.upsert_price_rows("FLAT", rows.to_dict("records"))

    resp = client.get("/screener/breakouts")
    assert resp.json() == []


def test_screen_breakouts_all_flag_includes_non_setups(client, test_db):
    rows = _flat_random_walk_df(seed=1).rename(columns={"trade_date": "date"})
    rows["date"] = rows["date"].dt.strftime("%Y-%m-%d")
    database.upsert_price_rows("FLAT", rows.to_dict("records"))

    resp = client.get("/screener/breakouts", params={"flagged_only": "false"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "FLAT"
    assert data[0]["is_pre_breakout"] is False


def test_screen_breakouts_skips_symbols_with_too_little_history(client, test_db):
    rows = _coiling_setup_df().iloc[:50].rename(columns={"trade_date": "date"})
    rows["date"] = rows["date"].dt.strftime("%Y-%m-%d")
    database.upsert_price_rows("SHORT", rows.to_dict("records"))

    resp = client.get("/screener/breakouts", params={"flagged_only": "false"})
    assert resp.json() == []
