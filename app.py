import streamlit as st
import yfinance as yf
import requests
from datetime import date
from openai import OpenAI
import os

# Setup OpenAI and Finnhub clients
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
FINNHUB_API_KEY = st.secrets["FINNHUB_API_KEY"]

# Tickers to track
tickers = ["QBTS", "RGTI", "IONQ"]

# === Fetch latest headline from Finnhub ===
def fetch_headline(ticker):
    today = date.today().isoformat()
    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={FINNHUB_API_KEY}"
    try:
        response = requests.get(url)
        news = response.json()
        if news and isinstance(news, list) and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return f"No recent news found for {ticker}"
    except Exception as e:
        return f"Error fetching news: {e}"

# === Analyze the sentiment of the headline ===
def get_vibe_score(headline):
    prompt = f"Rate this stock headline from 1 (very bearish) to 10 (very bullish): {headline}"
    try:
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return int(res.choices[0].message.content.strip())
    except Exception as e:
        return f"Error: {e}"

# === Map sentiment score to a trading signal ===
def generate_recommendation(score):
    if isinstance(score, int):
        if score >= 8:
            return "📈 Buy"
        elif score <= 3:
            return "📉 Sell"
        else:
            return "⏸ Hold"
    else:
        return "⚠️ No recommendation"

# === Streamlit UI ===
st.title("📊 AI-Powered Day Trading Watchlist")

for ticker in tickers:
    st.subheader(ticker)

    # Price chart
    data = yf.download(ticker, period="1d", interval="5m")
    st.line_chart(data["Close"])

    # News + AI analysis
    headline = fetch_headline(ticker)
    score = get_vibe_score(headline)
    recommendation = generate_recommendation(score)

    st.write(f"🧠 Vibe Score: **{score}**")
    st.write(f"📰 Headline: _{headline}_")
    st.write(f"🤖 AI Signal: **{recommendation}**")
    st.markdown("---")
