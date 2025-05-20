import streamlit as st
import yfinance as yf
from openai import OpenAI
import requests
from datetime import datetime
import pandas as pd

# 🔐 Load API keys securely from Streamlit secrets
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# 📈 Stocks to track
tickers = ["QBTS", "RGTI", "IONQ"]

# 🔍 Fetch the latest news headline from Finnhub
def fetch_headline(ticker):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        news = response.json()
        if news and isinstance(news, list) and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return f"No recent news for {ticker}"
    except Exception as e:
        return f"Error fetching news: {e}"

# 🤖 Analyze sentiment using OpenAI
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

# 📊 AI trading recommendation logic
def generate_signal(score):
    if score is None:
        return "⚠️ No recommendation"
    elif score >= 8:
        return "📈 Buy"
    elif score <= 3:
        return "📉 Sell"
    else:
        return "⏸️ Hold"

# 🚀 Streamlit UI
st.title("📊 AI-Powered Day Trading Watchlist")

for ticker in tickers:
    st.subheader(ticker)

    try:
        # Load data
        data = yf.download(ticker, period="5d", interval="30m")
        st.line_chart(data["Close"])

        # 🔁 Volume trend logic
        latest_volume = data["Volume"].iloc[-1] if not data["Volume"].empty else 0
        avg_volume = data["Volume"].mean() if not data["Volume"].empty else 0
        volume_ratio = float(latest_volume) / float(avg_volume) if avg_volume else 0

        # 📰 News & Sentiment
        headline = fetch_headline(ticker)
        vibe_score = get_vibe_score(headline)
        signal = generate_signal(vibe_score)

        # 📋 Display results
        st.markdown(f"🐋 **Volume Spike Ratio:** `{volume_ratio:.2f}`")
        st.markdown(f"📰 **Headline:** *{headline}*")
        st.markdown(f"🧠 **Vibe Score:** `{vibe_score if vibe_score is not None else 'Error'}`")
        st.markdown(f"🤖 **AI Signal:** {signal}")
        st.markdown("---")

    except Exception as e:
        st.error(f"Failed to analyze {ticker}: {e}")
