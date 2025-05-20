import streamlit as st
import yfinance as yf
import requests
from datetime import date
from openai import OpenAI
import numpy as np

# Set up secrets
openai_api_key = st.secrets["OPENAI_API_KEY"]
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

client = OpenAI(api_key=openai_api_key)
tickers = ["QBTS", "RGTI", "IONQ"]
today = date.today().strftime("%Y-%m-%d")

def fetch_headline(ticker):
    try:
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        news = response.json()
        if news and isinstance(news, list):
            return news[0]["headline"]
        else:
            return f"No recent news found for {ticker}"
    except Exception as e:
        return f"Error fetching news: {e}"

def get_vibe_score(headline):
    prompt = f"Rate this headline from 1 (very bearish) to 10 (very bullish): {headline}"
    try:
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return int(res.choices[0].message.content.strip())
    except Exception as e:
        return f"Error: {e}"

def generate_signal(vibe_score, volume_ratio):
    if isinstance(vibe_score, int):
        if vibe_score >= 8 and volume_ratio > 1.2:
            return "📈 Buy"
        elif vibe_score <= 3 and volume_ratio > 1.2:
            return "📉 Sell"
        else:
            return "⚠️ No recommendation"
    return "⚠️ No recommendation"

# --- UI ---
st.title("📊 AI-Powered Day Trading Watchlist")

for ticker in tickers:
    st.subheader(ticker)

    try:
        data = yf.download(ticker, period="5d", interval="30m")
        st.line_chart(data["Close"])

        # Volume ratio
        latest_volume = data["Volume"].iloc[-1]
        avg_volume = data["Volume"].mean()
        volume_ratio = 0 if np.isnan(avg_volume) or avg_volume == 0 else latest_volume / avg_volume

        # Headline & Vibe
        headline = fetch_headline(ticker)
        vibe = get_vibe_score(headline)
        signal = generate_signal(vibe, volume_ratio)

        # Display insights
        st.write(f"🐋 **Volume Ratio**: {volume_ratio:.2f}")
        st.write(f"📰 **Headline**: _{headline}_")
        st.write(f"🧠 **Vibe Score**: {vibe}")
        st.write(f"🤖 **AI Signal**: {signal}")
        st.markdown("---")

    except Exception as e:
        st.error(f"Failed to analyze {ticker}: {e}")
