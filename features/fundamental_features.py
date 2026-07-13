"""
Computes fundamental features (EPS growth, revenue growth, margin trend,
dividend yield change) from the financial_reports table.
"""
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import database


def get_fundamental_features(symbol):
    """
    Returns the latest fundamental snapshot for a symbol as a dict, or
    None if insufficient report history exists (need at least 2 periods
    for YoY/QoQ comparisons).
    """
    conn = database.get_connection()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM financial_reports WHERE symbol = ? ORDER BY report_date ASC",
            conn, params=(symbol,),
        )
    finally:
        conn.close()

    if len(df) < 2:
        return None

    df["report_date"] = pd.to_datetime(df["report_date"])
    df = df.sort_values("report_date").reset_index(drop=True)

    latest = df.iloc[-1]
    prior = df.iloc[-2]

    eps_growth_qoq = _safe_pct_change(prior["eps"], latest["eps"])
    revenue_growth_qoq = _safe_pct_change(prior["revenue"], latest["revenue"])

    # YoY comparison: look back ~4 quarters if available
    yoy_row = df.iloc[-5] if len(df) >= 5 else None
    eps_growth_yoy = _safe_pct_change(yoy_row["eps"], latest["eps"]) if yoy_row is not None else None
    revenue_growth_yoy = _safe_pct_change(yoy_row["revenue"], latest["revenue"]) if yoy_row is not None else None

    net_margin = _safe_div(latest["net_profit"], latest["revenue"])
    prior_net_margin = _safe_div(prior["net_profit"], prior["revenue"])
    margin_trend = (net_margin - prior_net_margin) if (net_margin is not None and prior_net_margin is not None) else None

    return {
        "symbol": symbol,
        "latest_period": latest["period"],
        "eps_growth_qoq": eps_growth_qoq,
        "eps_growth_yoy": eps_growth_yoy,
        "revenue_growth_qoq": revenue_growth_qoq,
        "revenue_growth_yoy": revenue_growth_yoy,
        "net_margin": net_margin,
        "margin_trend": margin_trend,
        "dividend_per_share": latest["dividend_per_share"],
    }


def _safe_pct_change(old_val, new_val):
    if old_val in (None, 0) or pd.isna(old_val) or pd.isna(new_val):
        return None
    return (new_val - old_val) / abs(old_val)


def _safe_div(numerator, denominator):
    if denominator in (None, 0) or pd.isna(denominator) or pd.isna(numerator):
        return None
    return numerator / denominator
