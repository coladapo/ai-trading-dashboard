import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
from openai import OpenAI

# Load secrets from Streamlit Cloud
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# --- UI setup ---
st.set_page_config(page_title="AI Trading Watchlist", layout="wide")
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔄 Refresh Data")

# --- Tickers to Watch ---
tickers = ["QBTS", "RGTI", "IONQ", "CRVW", "DBX", "TSM"]

@st.cache_data(ttl=30)
def fetch_price_data(ticker, period):
    try:
        interval = "1h" if period in ["1d", "5d"] else "1d"
        df = yf.download(ticker, period=period, interval=interval)
        df.reset_index(inplace=True)
        df["SMA (10)"] = df["Close"].rolling(window=10).mean()
        return df
    except Exception:
        return None

@st.cache_data(ttl=1800)
def fetch_news_headline(ticker):
    try:
        today = datetime.today().date()
        from_date = today - timedelta(days=7)
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={from_date}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data:
                return data[0].get("headline", "No headline found.")
            return "⚠️ No recent news found."
        return "❌ Error fetching news."
    except:
        return "❌ Error fetching news."

def get_vibe_score(headline):
    try:
        res = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "Rate the sentiment of this headline from 1 (negative) to 10 (positive)."},
                      {"role": "user", "content": headline}]
        )
        return res.choices[0].message.content.strip()
    except:
        return "N/A"

# --- Layout ---
cols = st.columns(3)
for i, ticker in enumerate(tickers):
    col = cols[i % 3]
    with col:
        st.subheader(ticker)
        
        df = fetch_price_data(ticker, timeframe)
        if df is not None and not df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"], mode="lines", name="Price"))
            fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA (10)"], mode="lines", name="SMA (10)"))
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=250)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Could not load chart.")

        # Headline and Vibe
        headline = fetch_news_headline(ticker)
        st.markdown(f"**Latest Headline:** {headline}")
        score = get_vibe_score(headline) if "❌" not in headline and "⚠️" not in headline else "N/A"
        st.info(f"Vibe Score: {score}")
        st.caption("No news to analyze." if score == "N/A" else "")
