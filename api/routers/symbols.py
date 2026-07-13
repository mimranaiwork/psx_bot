import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException

from db import database
from features import technical_features

router = APIRouter(tags=["symbols"])


@router.get("/symbols")
def list_symbols():
    df = database.get_price_symbols_summary()
    return json.loads(df.to_json(orient="records"))


@router.get("/symbols/{symbol}/prices")
def get_symbol_prices(symbol: str):
    price_df = database.get_price_history(symbol)
    if price_df.empty:
        raise HTTPException(status_code=404, detail=f"No price history found for {symbol}.")

    enriched = technical_features.compute_all(price_df)
    # NaN (indicator warm-up rows) -> null via a JSON round-trip, not Python's
    # non-standard NaN literal.
    return json.loads(enriched.to_json(orient="records", date_format="iso"))
