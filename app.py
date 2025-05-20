import streamlit as st
import yfinance as yf
from openai import OpenAI
import requests
from datetime import datetime
import pandas as pd

# Set up OpenAI and Finnhub clients
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# List of tickers
tickers = ["QBTS", "RGTI", "IONQ"]

# Fetch latest news headline from Finnhub
def fetch_headline(ticker):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        news = response.json()
        if isinstance(news, list) and len(news) > 0 and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return "No recent news found"
    except Exception as e:
        return f"Error fetching news: {e}"

# Analyze sentiment using OpenAI
def get_vibe_score(headline):
    prompt = f"Rate this stock market news headline from 1 (very bearish) to 10 (very bullish): {headline}"
    try:
        res = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        score = res.choices[0].message.content.strip()
        return int(score)
    except Exception as e:
        return f"Error: {e}"

# Generate signal
def get_signal(vibe_score, volume_ratio):
    if isinstance(vibe_score, int):
        if vibe_score >= 8 and volume_ratio >= 1.5:
            return "📈 Buy"
        elif vibe_score <= 3 and volume_ratio >= 1.5:
            return "📉 Sell"
        else:
            return "⚠️ No recommendation"
    return "⚠️ No recommendation"

# Main App
st.title("📊 AI-Powered Day Trading Watchlist")

for ticker in tickers:
    try:
        st.subheader(ticker)

        # Price chart
        data = yf.download(ticker, period="5d", interval="30m")
        st.line_chart(data["Close"])

        # Volume spike detection
        if not data["Volume"].empty:
            latest_volume = data["Volume"].iloc[-1]
            avg_volume = data["Volume"].mean()
            volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 0
        else:
            volume_ratio = 0

        # Headline + sentiment
        headline = fetch_headline(ticker)
        vibe = get_vibe_score(headline)
        signal = get_signal(vibe, volume_ratio)

        # Display insights
        st.markdown(f"🐬 **Volume Spike**: {volume_ratio:.2f}x average")
        st.markdown(f"📰 **Headline**: *{headline}*")
        st.markdown(f"🧠 **Vibe Score**: {vibe}")
        st.markdown(f"🤖 **AI Signal**: {signal}")
        st.markdown("---")

    except Exception as e:
        st.error(f"Failed to analyze {ticker}: {e}")
