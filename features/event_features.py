"""
Extracts event-based features from the announcements table: recent
announcement categories, counts, and a simple sentiment proxy.
"""
import sys
import os
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import database

POSITIVE_CATEGORIES = {"earnings", "dividend", "bonus"}
NEGATIVE_HINTS = ["loss", "decline", "resignation", "default", "downgrade"]


def get_event_features(symbol, as_of_date=None, lookback_days=30):
    """
    Returns a dict summarizing recent announcement activity for `symbol`
    in the `lookback_days` window before `as_of_date` (defaults to today).
    """
    if as_of_date is None:
        as_of_date = datetime.now()
    elif isinstance(as_of_date, str):
        as_of_date = datetime.fromisoformat(as_of_date)

    window_start = as_of_date - timedelta(days=lookback_days)

    conn = database.get_connection()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM announcements WHERE symbol = ? ORDER BY announced_at DESC",
            conn, params=(symbol,),
        )
    finally:
        conn.close()

    if df.empty:
        return {
            "symbol": symbol,
            "recent_announcement_count": 0,
            "has_earnings_announcement": False,
            "has_negative_hint": False,
            "categories_seen": [],
        }

    df["announced_at"] = pd.to_datetime(df["announced_at"])
    recent = df[(df["announced_at"] >= window_start) & (df["announced_at"] <= as_of_date)]

    negative_hint = recent["raw_text"].str.lower().apply(
        lambda t: any(hint in t for hint in NEGATIVE_HINTS) if isinstance(t, str) else False
    ).any()

    return {
        "symbol": symbol,
        "recent_announcement_count": len(recent),
        "has_earnings_announcement": "earnings" in recent["category"].values,
        "has_negative_hint": bool(negative_hint),
        "categories_seen": recent["category"].unique().tolist(),
    }
