import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta
from openai import OpenAI

# Load secrets from Streamlit Cloud
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# UI Setup
st.set_page_config(page_title="AI Trading Watchlist", layout="wide")
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔄 Refresh Data")

# Tickers to Watch
tickers = ["QBTS", "RGTI", "IONQ", "CRVW", "DBX", "TSM"]

# === Fetch Price Data ===
@st.cache_data(ttl=30)
def fetch_price_data(ticker, period):
    try:
        interval = "1h" if period in ["1d", "5d"] else "1d"
        df = yf.download(ticker, period=period, interval=interval)
        if df.empty:
            return None
        df = df.copy()
        df["Date"] = df.index
        df["SMA (10)"] = df["Close"].rolling(window=10).mean()
        return df
    except Exception as e:
        print(f"⚠️ Error fetching price data for {ticker}: {e}")
        return None

# === Fetch News Headline ===
@st.cache_data(ttl=1800)
def fetch_news_headline(ticker):
    try:
        today = datetime.today().date()
        last_week = today - timedelta(days=7)
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={last_week}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            news_data = response.json()
            if not news_data:
                return "⚠️ No recent news found.", None
            return news_data[0].get("headline", "No headline"), news_data[0].get("summary", "")
        else:
            return "❌ Error fetching news.", None
    except Exception as e:
        print(f"❌ News error for {ticker}: {e}")
        return "❌ Error fetching news.", None

# === Analyze Vibe ===
def get_vibe_score(headline):
    try:
        res = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Rate the vibe of this headline from 1 to 10 (1 = very negative, 10 = very positive). Return only the number."},
                {"role": "user", "content": headline}
            ]
        )
        score = res.choices[0].message.content.strip()
        return int(score)
    except Exception as e:
        print(f"⚠️ OpenAI vibe error: {e}")
        return "N/A"

# === Layout ===
cols = st.columns(3)

for idx, ticker in enumerate(tickers):
    with cols[idx % 3]:
        st.subheader(ticker)

        df = fetch_price_data(ticker, timeframe) if refresh or True else None

        if df is not None:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], mode="lines", name="Price"))
            fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA (10)"], mode="lines", name="SMA (10)"))
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=250)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("📉 No chart data available.")

        # Headline
        headline, summary = fetch_news_headline(ticker)
        st.markdown(f"**Latest Headline:** {headline}")

        # Vibe
        vibe_score = get_vibe_score(headline) if "⚠️" not in headline and "❌" not in headline else "N/A"
        st.markdown(f"**Vibe Score:** {vibe_score}")

        # Summary
        st.info(summary or "No news to analyze.")

        # Row management
        if (idx + 1) % 3 == 0 and idx + 1 < len(tickers):
            cols = st.columns(3)  # new row
