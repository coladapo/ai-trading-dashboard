import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import pandas_ta as ta
from datetime import datetime

# === UI Setup ===
st.set_page_config(page_title="AI Trading Dashboard", layout="wide")
st.title("📊 AI-Powered Day Trading with Pattern Detection")
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
tickers = ["QBTS", "RGTI", "IONQ"]

# === Fetch Price Data ===
@st.cache_data(ttl=60)
def fetch_data(ticker, period):
    interval = "5m" if period == "1d" else "1d"
    df = yf.download(ticker, period=period, interval=interval)
    df = df.reset_index()
    df.ta.sma(length=20, append=True)
    df.ta.rsi(length=14, append=True)
    return df

# === Pattern Detection ===
def detect_pattern(df):
    try:
        recent = df.iloc[-3:]
        last_close = recent["Close"].iloc[-1]
        sma = recent["SMA_20"].mean()
        rsi = recent["RSI_14"].iloc[-1]

        if last_close > sma and rsi < 70:
            return "📈 Bullish Momentum forming"
        elif last_close < sma and rsi > 30:
            return "📉 Bearish pullback risk"
        elif rsi >= 70:
            return "⚠️ Overbought (watch for reversal)"
        elif rsi <= 30:
            return "🔻 Oversold (potential bounce)"
        else:
            return "🔎 No clear pattern"
    except:
        return "❌ Unable to analyze pattern"

# === Plotting and Display ===
for ticker in tickers:
    st.subheader(ticker)
    try:
        df = fetch_data(ticker, timeframe)

        fig, ax = plt.subplots()
        ax.plot(df["Datetime" if timeframe == "1d" else "Date"], df["Close"], label="Close", linewidth=2)
        ax.plot(df["Datetime" if timeframe == "1d" else "Date"], df["SMA_20"], label="SMA 20", linestyle="--")
        ax.set_title(f"{ticker} Price Chart")
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        ax.legend()
        ax.tick_params(axis='x', rotation=45)
        st.pyplot(fig)

        # === Pattern Insight ===
        insight = detect_pattern(df)
        st.markdown(f"**🧠 Pattern Insight:** {insight}")
        st.divider()

    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")
