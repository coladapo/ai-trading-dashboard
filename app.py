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

# Function: Fetch latest news headline from Finnhub
def fetch_headline(ticker):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        news = response.json()
        if news and isinstance(news, list) and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return f"No recent news found for {ticker}"
    except Exception as e:
        return f"Error fetching news: {e}"

# Function: Get vibe score from OpenAI
def get_vibe_score(headline):
    prompt = f"Rate this stock market news headline from 1 (very bearish) to 10 (very bullish): {headline}"
    try:
        res = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        score = int(res.choices[0].message.content.strip())
        return score
    except Exception as e:
        return f"Error: {e}"

# Function: Generate AI signal
def generate_signal(score, volume_ratio):
    if isinstance(score, int):
        if score >= 8 and volume_ratio > 1.5:
            return "📈 Buy"
        elif score <= 3 and volume_ratio > 1.5:
            return "📉 Sell"
        else:
            return "⚠️ No recommendation"
    else:
        return "⚠️ No recommendation"

# Streamlit UI
st.title("📊 AI-Powered Day Trading Watchlist")

for ticker in tickers:
    st.subheader(ticker)

    try:
        # Fetch intraday stock data
        data = yf.download(ticker, period="5d", interval="30m")
        st.line_chart(data["Close"])

        # Volume trend analysis
        latest_volume = data["Volume"].iloc[-1]
        avg_volume = data["Volume"].mean()
        volume_ratio = latest_volume / avg_volume if avg_volume != 0 else 0

        # Show volume insights (optional - or remove this)
        # st.caption(f"🔍 Volume ratio: {volume_ratio:.2f}")

        # News + Vibe Score
        headline = fetch_headline(ticker)
        vibe_score = get_vibe_score(headline)
        signal = generate_signal(vibe_score, volume_ratio)

        # Display results
        st.markdown(f"📰 **Headline:** _{headline}_")
        st.markdown(f"🧠 **Vibe Score:** {vibe_score}")
        st.markdown(f"🤖 **AI Signal:** {signal}")
        st.markdown("---")

    except Exception as e:
        st.error(f"Failed to analyze {ticker}: {e}")
