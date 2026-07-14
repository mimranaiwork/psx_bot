import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, Query

import config
from db import database
from features import breakout_features

router = APIRouter(tags=["screener"])

# Minimum rows for the most recent row to have a valid bb_width_percentile:
# 20 (Bollinger warm-up) + the squeeze lookback window itself.
MIN_ROWS_FOR_SCREENING = 20 + config.BREAKOUT_SQUEEZE_LOOKBACK_DAYS


@router.get("/screener/breakouts")
def screen_breakouts(flagged_only: bool = Query(default=True)):
    """
    Scans every loaded symbol for the pre-breakout "coiling" setup
    (Bollinger squeeze near resistance, volume building, momentum not
    yet overextended). Rule-based pattern match, not a prediction --
    see features/breakout_features.py.
    """
    symbols_df = database.get_price_symbols_summary()
    results = []
    for symbol in symbols_df["symbol"]:
        price_df = database.get_price_history(symbol)
        if len(price_df) < MIN_ROWS_FOR_SCREENING:
            continue
        result = breakout_features.get_breakout_signal(symbol, price_df)
        if result.get("is_pre_breakout") or not flagged_only:
            results.append(result)

    results.sort(key=lambda r: (-r.get("checks_passed", 0), r.get("pct_from_high", 1.0)))
    return results
