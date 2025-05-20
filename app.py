import streamlit as st
import yfinance as yf
from openai import OpenAI
import requests
from datetime import datetime
import pandas as pd

# Set up OpenAI and Finnhub clients
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# Sidebar: Chart timeframe
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])

# Set chart interval based on timeframe
interval_map = {
    "1d": "5m",
    "5d": "15m",
    "1mo": "60m",
    "3mo": "1d",
    "6mo": "1d",
    "1y": "1d"
}
interval = interval_map.get(timeframe, "1d")

# List of tickers to analyze
tickers = ["QBTS", "RGTI", "IONQ"]

# Cache vibe scores for headlines
@st.cache_data(show_spinner=False)
def get_vibe_score_cached(headline):
    prompt = f"Rate this stock market news headline from 1 (very bearish) to 10 (very bullish), and explain why: {headline}"
    try:
        res = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

# Get latest headline from Finnhub
def fetch_headline(ticker):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        news = response.json()
        if news and isinstance(news, list) and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return "No recent headline found."
    except Exception as e:
        return f"Error fetching news: {e}"

# Determine recommendation based on score
def recommend_from_score(score_text):
    try:
        score = int("".join(filter(str.isdigit, score_text.split()[0])))
        if score >= 8:
            return "📈 Buy"
        elif score <= 3:
            return "📉 Sell"
        else:
            return "🤖 Hold"
    except:
        return "⚠️ No recommendation"

# App layout
st.title("📊 AI-Powered Day Trading Watchlist")

for ticker in tickers:
    st.subheader(ticker)

    try:
        # Price chart
        data = yf.download(ticker, period=timeframe, interval=interval)
        st.line_chart(data["Close"])

        # Headline
        headline = fetch_headline(ticker)
        st.markdown(f"📰 **Headline:** *{headline}*")

        # AI analysis
        vibe = get_vibe_score_cached(headline)
        st.markdown(f"🧠 **Vibe Score:** {vibe}")
        st.markdown(f"🤖 **AI Signal:** {recommend_from_score(vibe)}")

    except Exception as e:
        st.error(f"Failed to analyze {ticker}: {e}")
