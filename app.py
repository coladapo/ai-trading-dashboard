import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
from openai import OpenAI

# Load secrets
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# UI
st.set_page_config(page_title="AI Trading Watchlist", layout="wide")
st.sidebar.header("🗓️ Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔄 Refresh Data")

# Tickers to track
tickers = ["QBTS", "RGTI", "IONQ", "CRVW", "DBX", "TSM"]

# === Functions ===

@st.cache_data(ttl=3600)
def fetch_price_data(ticker, period):
    try:
        interval = "1d" if period != "1d" else "5m"
        df = yf.download(ticker, period=period, interval=interval)
        df.reset_index(inplace=True)
        df["sma"] = df["Close"].rolling(window=10).mean()
        return df
    except Exception:
        return None

@st.cache_data(ttl=1800)
def fetch_news_headline(ticker):
    today = datetime.today().date()
    last_week = today - timedelta(days=7)
    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={last_week}&to={today}&token={finnhub_api_key}"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            news_data = res.json()
            if news_data:
                return news_data[0].get("headline", "No headline found.")
    except Exception:
        pass
    return None

def get_vibe_score(headline):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"Rate this stock news from 1 (bad) to 10 (great) for traders: '{headline}' and briefly explain why."
            }]
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Vibe Score: N/A"

# === Display Grid ===
cols = st.columns(3)

for idx, ticker in enumerate(tickers):
    with cols[idx % 3]:
        st.subheader(ticker)

        df = fetch_price_data(ticker, timeframe)
        if df is not None and not df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], name="Price"))
            fig.add_trace(go.Scatter(x=df["Date"], y=df["sma"], name="SMA (10)"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ No chart data.")

        headline = fetch_news_headline(ticker)
        if headline:
            st.markdown(f"**Latest Headline:** {headline}")
            score = get_vibe_score(headline)
            st.info(score)
        else:
            st.error("❌ Error fetching news.")
            st.info("Vibe Score: N/A")
            st.write("No news to analyze.")
