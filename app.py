import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta
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
@st.cache_data(ttl=30 if not refresh else 0, show_spinner=False)
def fetch_price_data(ticker, period):
    try:
        interval = "5m" if period == "1d" else "1d"
        df = yf.download(ticker, period=period, interval=interval)
        if df.empty:
            return None
        df["Date"] = df.index
        df["sma"] = df["Close"].rolling(window=10).mean()
        return df.reset_index(drop=True)
    except Exception as e:
        return None

# === Fetch News Headline ===
@st.cache_data(ttl=1800 if not refresh else 0, show_spinner=False)
def fetch_news_headline(ticker):
    today = datetime.today().date()
    last_week = today - timedelta(days=7)

    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={last_week}&to={today}&token={finnhub_api_key}"
    response = requests.get(url)

    if response.status_code != 200:
        return "❌ Error fetching news.", None

    news_data = response.json()
    if not news_data:
        return "⚠️ No recent news found.", None

    top_news = news_data[0]
    return top_news.get("headline", "No headline."), top_news.get("summary", "")

# === Analyze Vibe ===
def get_vibe_score(headline):
    try:
        res = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Rate this headline from 1 to 10 on market optimism. Then summarize its importance in 2 bullet points."},
                {"role": "user", "content": headline},
            ]
        )
        return res.choices[0].message.content
    except Exception:
        return "❌ Error generating vibe."

# === Layout ===
st.title("AI Trading Watchlist")
cols = st.columns(len(tickers))

for i, ticker in enumerate(tickers):
    df = fetch_price_data(ticker, timeframe)
    with cols[i]:
        st.subheader(ticker)

        if df is None or "Close" not in df.columns:
            st.warning("No data available.")
            continue

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], mode="lines", name="Price"))
        fig.add_trace(go.Scatter(x=df["Date"], y=df["sma"], mode="lines", name="SMA (10)"))
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=250)
        st.plotly_chart(fig, use_container_width=True)

        headline, summary = fetch_news_headline(ticker)
        st.markdown(f"**Latest Headline:** {headline}")

        if summary:
            vibe_response = get_vibe_score(headline)
            st.markdown(f"**Vibe Score**\n{vibe_response}")
        else:
            st.info("No news to analyze.")
