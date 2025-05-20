import streamlit as st
import yfinance as yf
from openai import OpenAI
import requests
from datetime import datetime
import pandas as pd

# Setup API clients
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# Ticker list
tickers = ["QBTS", "RGTI", "IONQ"]

# Timeframe + interval mapping
st.sidebar.title("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
interval_map = {
    "1d": "5m",
    "5d": "15m",
    "1mo": "30m",
    "3mo": "1h",
    "6mo": "1d",
    "1y": "1d"
}
interval = interval_map[timeframe]

# Functions
def fetch_headline(ticker):
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        news = response.json()
        if isinstance(news, list) and len(news) > 0 and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return f"No recent news for {ticker}"
    except Exception as e:
        return f"Error fetching news: {e}"

def get_vibe_score(headline):
    prompt = f"Rate this stock market news headline from 1 (very bearish) to 10 (very bullish): {headline}"
    try:
        res = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        score_text = res.choices[0].message.content.strip()
        score = int(''.join(filter(str.isdigit, score_text)))
        return score
    except Exception as e:
        return None

def generate_signal(score):
    if score is None:
        return "⚠️ No recommendation"
    elif score >= 8:
        return "📈 Buy"
    elif score <= 3:
        return "📉 Sell"
    else:
        return "⏸️ Hold"

# UI
st.title("📊 AI-Powered Day Trading Watchlist")

for ticker in tickers:
    st.subheader(ticker)

    try:
        # Chart + data
        data = yf.download(ticker, period=timeframe, interval=interval)
        st.line_chart(data["Close"])

        # Headline & signal
        headline = fetch_headline(ticker)
        vibe_score = get_vibe_score(headline)
        signal = generate_signal(vibe_score)

        st.markdown(f"📰 **Headline:** *{headline}*")
        st.markdown(f"🧠 **Vibe Score:** `{vibe_score if vibe_score is not None else 'Error'}`")
        st.markdown(f"🤖 **AI Signal:** {signal}")
        st.markdown("---")

    except Exception as e:
        st.error(f"Failed to analyze {ticker}: {e}")
