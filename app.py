import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
from openai import OpenAI

# === Secrets ===
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# === UI Setup ===
st.set_page_config(page_title="AI Trading Watchlist", layout="wide")
st.sidebar.header("🗓️ Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔄 Refresh Data")

# === Tickers ===
tickers = ["QBTS", "RGTI", "IONQ", "CRWV", "DBX", "TSM"]

# === Fetch Price Data ===
@st.cache_data(ttl=30 if not refresh else 0)
def fetch_price_data(ticker, period):
    try:
        interval = "5m" if period == "1d" else "1d"
        df = yf.download(ticker, period=period, interval=interval)
        df = df.reset_index()
        df["sma"] = df["Close"].rolling(window=10).mean()
        return df
    except Exception as e:
        return None

# === Fetch News ===
def fetch_news_headline(ticker):
    today = datetime.today().date()
    last_week = today - timedelta(days=7)

    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={last_week}&to={today}&token={finnhub_api_key}"
    response = requests.get(url)

    if response.status_code != 200:
        return "❌ Error fetching news.", None

    news_data = response.json()
    if not news_data:
        return "No recent news found.", None

    return news_data[0]["headline"], news_data[0]["summary"]

# === Analyze Vibe ===
def get_vibe_score(text):
    try:
        res = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Rate the tone of this stock news headline from 1 (very negative) to 10 (very positive). Just return the number."},
                {"role": "user", "content": text}
            ]
        )
        score = res.choices[0].message.content.strip()
        return int(score)
    except:
        return None

# === Display ===
st.title("📈 AI Trading Watchlist")
cols = st.columns(3)

for i, ticker in enumerate(tickers):
    col = cols[i % 3]
    with col:
        st.subheader(ticker)

        df = fetch_price_data(ticker, timeframe)
        if df is not None and not df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], mode="lines", name="Price"))
            fig.add_trace(go.Scatter(x=df["Date"], y=df["sma"], mode="lines", name="SMA (10)"))
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("⚠️ Price data not available.")

        headline, summary = fetch_news_headline(ticker)
        st.markdown(f"**Latest Headline:** {headline}")

        if summary:
            score = get_vibe_score(headline)
            if score:
                st.markdown(f"**Vibe Score**: {score}")
                st.markdown(f"🔍 {summary}")
            else:
                st.warning("Could not calculate vibe score.")
        else:
            st.info("No news to analyze.")
