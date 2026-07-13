import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from db import database

router = APIRouter(tags=["signals"])


@router.get("/signals/latest")
def latest_signals():
    df = database.get_latest_signals()
    return json.loads(df.to_json(orient="records"))


@router.get("/signals-log")
def signals_log(symbol: Optional[str] = Query(default=None)):
    df = database.get_signals_log(symbol)
    return json.loads(df.to_json(orient="records"))


@router.get("/symbols/{symbol}/signal")
def latest_signal_for_symbol(symbol: str):
    df = database.get_signals_log(symbol)
    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No logged signal for {symbol} yet. POST /symbols/{symbol}/signal to generate one.",
        )
    return json.loads(df.iloc[[0]].to_json(orient="records"))[0]
