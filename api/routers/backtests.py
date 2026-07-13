import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Optional

from fastapi import APIRouter, Query

from db import database

router = APIRouter(tags=["backtests"])


@router.get("/backtests")
def list_backtests(symbol: Optional[str] = Query(default=None)):
    df = database.get_backtest_runs(symbol)
    return json.loads(df.to_json(orient="records"))
