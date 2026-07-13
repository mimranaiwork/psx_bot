"""
FastAPI backend for the PSX AI Insights Bot web portal. Thin HTTP layer
over the existing pipeline modules (db.database, models.*, backtest.*,
signals.*, ingestion.*) -- no pipeline logic lives here.

Run:
    uvicorn api.main:app --reload --port 8000
"""
import sys
import os
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import database
from api.routers import symbols, signals, backtests, pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield


app = FastAPI(
    title="PSX AI Insights Bot API",
    description="Decision-support signals for PSX-listed stocks -- probability-weighted, "
                "not a guarantee. Price/fundamentals/news data sourced from Yahoo Finance "
                "(unofficial for PSX equities) unless loaded from a licensed CSV.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(symbols.router)
app.include_router(signals.router)
app.include_router(backtests.router)
app.include_router(pipeline.router)
