"""
Central configuration for the PSX AI Insights Bot.
Keep all tunable parameters here so behavior can be adjusted without
touching pipeline logic.
"""
import os

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "psx_bot.db")
PRICES_DIR = os.path.join(DATA_DIR, "prices")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
MODELS_DIR = os.path.join(DATA_DIR, "models")

for d in (DATA_DIR, PRICES_DIR, REPORTS_DIR, MODELS_DIR):
    os.makedirs(d, exist_ok=True)

# --- Trading cost assumptions (used in backtesting) ---
BROKERAGE_FEE_PCT = 0.0015      # 0.15% per side, adjust to your broker's actual rate
SLIPPAGE_PCT = 0.001            # 0.1% assumed slippage per trade
CDC_FEE_PCT = 0.0001            # approximate CDC/other regulatory charges

# --- Model / signal parameters ---
PREDICTION_HORIZON_DAYS = 5     # single fixed horizon: predict 5-day forward move
MOVE_THRESHOLD_PCT = 0.02       # label as "up" if forward move > +2%, "down" if < -2%
MIN_TRAINING_ROWS = 250         # minimum rows required before training is allowed

# --- Confidence bucket thresholds (based on model predicted probability) ---
CONFIDENCE_HIGH = 0.70
CONFIDENCE_MODERATE = 0.55
# below CONFIDENCE_MODERATE -> "Low"

# --- Backtesting ---
BACKTEST_MIN_YEARS = 2
WALK_FORWARD_TRAIN_WINDOW_DAYS = 500
WALK_FORWARD_TEST_WINDOW_DAYS = 60

# --- LLM synthesis (optional layer) ---
# Set ANTHROPIC_API_KEY as an environment variable to enable the LLM
# rationale layer. If unset, the system falls back to a template-based
# rationale generator so the pipeline still works end-to-end.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LLM_MODEL = "claude-sonnet-4-6"

# --- Fundamental rule thresholds ---
EPS_GROWTH_POSITIVE_THRESHOLD = 0.15   # +15% YoY EPS growth => positive flag
EPS_GROWTH_NEGATIVE_THRESHOLD = -0.10  # -10% YoY EPS growth => negative flag

# --- Pre-breakout screener thresholds ---
# Flags a "coiling" setup: tight volatility (Bollinger squeeze) near recent
# resistance, with volume starting to build and momentum not yet
# overextended. A rule-based pattern match, not a prediction -- see
# backtest/breakout_backtest.py for whether this setup actually precedes
# real breakouts historically before trusting it.
BREAKOUT_SQUEEZE_LOOKBACK_DAYS = 120    # window for the bb_width percentile rank
BREAKOUT_RESISTANCE_LOOKBACK_DAYS = 50  # window for the rolling high ("resistance")
BREAKOUT_SQUEEZE_PERCENTILE = 0.20      # bb_width in bottom 20% of its own trailing range
BREAKOUT_RESISTANCE_PCT = 0.03          # within 3% of the trailing high
BREAKOUT_VOLUME_RATIO = 1.2             # volume >= 1.2x its 30-day average
BREAKOUT_RSI_MIN = 45                   # momentum floor -- not already rolling over
BREAKOUT_RSI_MAX = 70                   # momentum ceiling -- not already overbought/extended
BREAKOUT_MIN_CHECKS = 3                 # how many of the 4 checks must pass to flag
