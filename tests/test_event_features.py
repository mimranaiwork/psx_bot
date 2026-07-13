from db import database
from features import event_features


def _insert_announcement(symbol, announced_at, category, raw_text):
    conn = database.get_connection()
    conn.execute(
        "INSERT INTO announcements (symbol, announced_at, category, raw_text, source_url) "
        "VALUES (?, ?, ?, ?, ?)",
        (symbol, announced_at, category, raw_text, "test"),
    )
    conn.commit()
    conn.close()


def test_no_announcements_returns_defaults(test_db):
    feats = event_features.get_event_features("NOPE")
    assert feats["recent_announcement_count"] == 0
    assert feats["has_earnings_announcement"] is False
    assert feats["has_negative_hint"] is False
    assert feats["categories_seen"] == []


def test_old_announcement_outside_lookback_window_is_excluded(test_db):
    _insert_announcement("SYM", "2020-01-01 00:00:00", "earnings", "quarterly results announced")
    feats = event_features.get_event_features("SYM", as_of_date="2026-07-13", lookback_days=30)
    assert feats["recent_announcement_count"] == 0


def test_recent_earnings_announcement_detected(test_db):
    _insert_announcement("SYM", "2026-07-01 00:00:00", "earnings", "quarterly results announced, EPS up")
    feats = event_features.get_event_features("SYM", as_of_date="2026-07-13", lookback_days=30)
    assert feats["recent_announcement_count"] == 1
    assert feats["has_earnings_announcement"] is True
    assert "earnings" in feats["categories_seen"]


def test_negative_hint_keyword_detected(test_db):
    _insert_announcement("SYM", "2026-07-05 00:00:00", "other", "Company reports a loss for the quarter")
    feats = event_features.get_event_features("SYM", as_of_date="2026-07-13", lookback_days=30)
    assert feats["has_negative_hint"] is True


def test_positive_text_does_not_trigger_negative_hint(test_db):
    _insert_announcement("SYM", "2026-07-05 00:00:00", "dividend", "Board declares cash dividend")
    feats = event_features.get_event_features("SYM", as_of_date="2026-07-13", lookback_days=30)
    assert feats["has_negative_hint"] is False


def test_window_start_boundary_is_inclusive(test_db):
    # as_of_date=2026-07-13, lookback_days=30 -> window_start=2026-06-13
    _insert_announcement("SYM", "2026-06-13 00:00:00", "other", "boundary case")
    feats = event_features.get_event_features("SYM", as_of_date="2026-07-13", lookback_days=30)
    assert feats["recent_announcement_count"] == 1
