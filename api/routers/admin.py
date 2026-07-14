"""
Admin/bulk-import endpoints. Not part of the pipeline -- these exist so
data collected elsewhere (e.g. locally, where Yahoo Finance doesn't
rate-limit the request's origin IP the way it does on shared cloud
hosting) can be pushed into a deployed instance without that instance
ever calling Yahoo itself.

Protected by a shared-secret header (ADMIN_TOKEN env var), checked via
constant-time comparison. Fails closed: if ADMIN_TOKEN isn't configured
on the server, these endpoints refuse all requests rather than being
open to anyone.
"""
import os
import sys
import secrets

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, Header, HTTPException

from db import database
from ingestion.financial_report_parser import save_report
from api.schemas import (
    ImportPricesRequest, ImportFundamentalsRequest,
    ImportBacktestRunsRequest, ImportSignalsRequest, ActionResult,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin_token(x_admin_token: str | None):
    expected = os.environ.get("ADMIN_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN not configured on this server.")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Token header.")


@router.post("/symbols/{symbol}/import-prices", response_model=ActionResult)
def import_prices(symbol: str, body: ImportPricesRequest, x_admin_token: str | None = Header(default=None)):
    _require_admin_token(x_admin_token)
    database.init_db()
    rows = [r.model_dump() for r in body.rows]
    n = database.upsert_price_rows(symbol, rows)
    return ActionResult(symbol=symbol, detail=f"Imported {n} price rows.", data={"rows": n})


@router.post("/symbols/{symbol}/import-fundamentals", response_model=ActionResult)
def import_fundamentals(symbol: str, body: ImportFundamentalsRequest, x_admin_token: str | None = Header(default=None)):
    _require_admin_token(x_admin_token)
    database.init_db()
    written = 0
    for row in body.rows:
        save_report({
            "symbol": symbol,
            "period": row.period,
            "report_date": row.report_date,
            "eps": row.eps,
            "revenue": row.revenue,
            "net_profit": row.net_profit,
            "dividend_per_share": row.dividend_per_share,
            "source_pdf": "bulk-import",
        })
        written += 1
    return ActionResult(symbol=symbol, detail=f"Imported {written} fundamentals rows.", data={"rows": written})


@router.post("/symbols/{symbol}/import-backtests", response_model=ActionResult)
def import_backtests(symbol: str, body: ImportBacktestRunsRequest, x_admin_token: str | None = Header(default=None)):
    _require_admin_token(x_admin_token)
    database.init_db()
    for row in body.rows:
        database.insert_backtest_run({"symbol": symbol, **row.model_dump()})
    return ActionResult(symbol=symbol, detail=f"Imported {len(body.rows)} backtest runs.", data={"rows": len(body.rows)})


@router.post("/symbols/{symbol}/import-signals", response_model=ActionResult)
def import_signals(symbol: str, body: ImportSignalsRequest, x_admin_token: str | None = Header(default=None)):
    _require_admin_token(x_admin_token)
    database.init_db()
    conn = database.get_connection()
    try:
        cur = conn.cursor()
        for row in body.rows:
            cur.execute(
                """
                INSERT INTO signals_log
                    (symbol, signal_date, signal, confidence, model_probability,
                     fundamental_flag, rationale, horizon_days, actual_forward_return, outcome_correct)
                VALUES (:symbol, :signal_date, :signal, :confidence, :model_probability,
                        :fundamental_flag, :rationale, :horizon_days, :actual_forward_return, :outcome_correct)
                """,
                {"symbol": symbol, **row.model_dump()},
            )
        conn.commit()
    finally:
        conn.close()
    return ActionResult(symbol=symbol, detail=f"Imported {len(body.rows)} signals.", data={"rows": len(body.rows)})
