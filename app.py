import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
from openai import OpenAI

# ===== Secrets =====
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# ===== UI Setup =====
st.set_page_config(page_title="AI Trading Watchlist", layout="wide")
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔄 Refresh Data")

# ===== Tickers =====
tickers = ["QBTS", "RGTI", "IONQ", "CRVW", "DBX", "TSM"]

# ===== Fetch Price Data =====
@st.cache_data(ttl=30 if not refresh else 0, show_spinner=False)
def fetch_price_data(ticker, period):
    try:
        interval = "1d" if period in ["1d", "5d"] else "1d"
        df = yf.download(ticker, period=period, interval=interval)
        df = df.reset_index()
        df["sma"] = df["Close"].rolling(window=10).mean()
        return df
    except Exception as ex:
        return None

# ===== Fetch News Headline =====
@st.cache_data(ttl=1800 if not refresh else 0, show_spinner=False)
def fetch_news_headline(ticker):
    today = datetime.utcnow().date()
    last_week = today - timedelta(days=7)
    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={last_week}&to={today}&token={finnhub_api_key}"
    response = requests.get(url)

    if response.status_code != 200:
        return {"headline": "❌ Error fetching news.", "analysis": "No news to analyze."}

    news_data = response.json()
    if not news_data:
        return {"headline": "⚠️ No recent news found.", "analysis": "No news to analyze."}

    top_news = news_data[0]  # Pick the first item for now
    return {"headline": top_news["headline"], "summary": top_news["summary"]}

# ===== Analyze Vibe =====
def get_vibe_score(headline):
    try:
        res = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a financial sentiment analyst."},
                {"role": "user", "content": f"Rate the sentiment of this headline from 1 (bearish) to 10 (bullish): {headline}"},
            ]
        )
        return int([int(s) for s in res.choices[0].message.content.split() if s.isdigit()][0])
    except:
        return None

# ===== Layout: 3 columns per row =====
cols = st.columns(3)

for i, ticker in enumerate(tickers):
    with cols[i % 3]:
        st.subheader(ticker)

        df = fetch_price_data(ticker, timeframe)
        if df is not None and not df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], mode="lines", name="Price"))
            fig.add_trace(go.Scatter(x=df["Date"], y=df["sma"], mode="lines", name="SMA (10)"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ No price data.")

        news_data = fetch_news_headline(ticker)
        st.markdown(f"**Latest Headline:** {news_data['headline']}")

        vibe_score = get_vibe_score(news_data['headline'])
        st.info(f"Vibe Score: {vibe_score if vibe_score else 'N/A'}")

        st.write(news_data.get("analysis", news_data.get("summary", "No news to analyze.")))

    if (i + 1) % 3 == 0 and (i + 1) != len(tickers):
        cols = st.columns(3)
