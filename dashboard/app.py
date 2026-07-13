"""
Streamlit dashboard for the PSX AI Insights Bot.
Run with: streamlit run dashboard/app.py
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from db import database
from signals import signal_engine
from features import technical_features

st.set_page_config(page_title="PSX AI Insights Bot", layout="wide")

st.title("PSX AI Insights Bot")
st.caption("Decision-support dashboard — signals are probability-weighted, not guarantees. "
           "Always verify against your own research before trading.")

database.init_db()

# --- Symbol selector ---
conn = database.get_connection()
symbols_df = pd.read_sql_query("SELECT DISTINCT symbol FROM price_history ORDER BY symbol", conn)
conn.close()

if symbols_df.empty:
    st.warning("No price data loaded yet. Run `python main.py demo` or load real data first "
               "(see README.md).")
    st.stop()

symbol = st.sidebar.selectbox("Symbol", symbols_df["symbol"].tolist())

# --- Price chart with technical indicators ---
price_df = database.get_price_history(symbol)
feat_df = technical_features.compute_all(price_df)

col1, col2 = st.columns([3, 1])

with col1:
    st.subheader(f"{symbol} — Price & Indicators")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=feat_df["trade_date"], open=feat_df["open"], high=feat_df["high"],
        low=feat_df["low"], close=feat_df["close"], name="Price"
    ))
    fig.add_trace(go.Scatter(x=feat_df["trade_date"], y=feat_df["sma_50"],
                              name="SMA 50", line=dict(width=1)))
    fig.add_trace(go.Scatter(x=feat_df["trade_date"], y=feat_df["sma_200"],
                              name="SMA 200", line=dict(width=1)))
    fig.update_layout(height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("RSI (14-day)")
    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=feat_df["trade_date"], y=feat_df["rsi_14"], name="RSI"))
    fig_rsi.add_hline(y=70, line_dash="dot", line_color="red")
    fig_rsi.add_hline(y=30, line_dash="dot", line_color="green")
    fig_rsi.update_layout(height=250)
    st.plotly_chart(fig_rsi, use_container_width=True)

with col2:
    st.subheader("Current Signal")
    if st.button("Generate Signal", type="primary"):
        try:
            with st.spinner("Generating signal..."):
                result = signal_engine.generate_signal(symbol)
            signal_color = {"BUY": "green", "SELL": "red", "HOLD": "gray"}[result["signal"]]
            st.markdown(f"### :{signal_color}[{result['signal']}]")
            st.markdown(f"**Confidence:** {result['confidence']}")
            st.markdown("**Rationale:**")
            st.info(result["rationale"])
        except ValueError as e:
            st.error(str(e))
            st.caption("Train a model first: `python main.py train --symbol " + symbol + "`")

    st.divider()
    st.caption(
        "⚠️ This is decision support, not financial advice. Every signal is "
        "logged below for honest accuracy tracking — check the track record "
        "before trusting any single call."
    )

# --- Track record ---
st.subheader("Signal History & Track Record")
signals_df = database.get_signals_log(symbol)

if signals_df.empty:
    st.info("No signals generated yet for this symbol.")
else:
    scored = signals_df.dropna(subset=["outcome_correct"])
    if not scored.empty:
        accuracy = scored["outcome_correct"].mean()
        st.metric("Historical directional accuracy (scored signals only)",
                   f"{accuracy:.1%}", help="Based on BUY/SELL signals where the "
                   "prediction horizon has already elapsed. HOLD signals aren't scored.")
    else:
        st.caption("No signals have completed their prediction horizon yet — "
                   "run `python main.py update-outcomes --symbol " + symbol + "` periodically.")

    st.dataframe(
        signals_df[["signal_date", "signal", "confidence", "fundamental_flag",
                     "actual_forward_return", "outcome_correct"]],
        use_container_width=True,
    )

# --- Recent announcements ---
st.subheader("Recent Announcements")
conn = database.get_connection()
ann_df = pd.read_sql_query(
    "SELECT announced_at, category, raw_text FROM announcements WHERE symbol = ? "
    "ORDER BY announced_at DESC LIMIT 10",
    conn, params=(symbol,),
)
conn.close()

if ann_df.empty:
    st.caption("No announcements loaded for this symbol yet.")
else:
    st.dataframe(ann_df, use_container_width=True)
