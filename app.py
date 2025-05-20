import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import date
from openai import OpenAI
import ta

# Initialize OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Your Finnhub API Key
FINNHUB_API_KEY = st.secrets["FINNHUB_API_KEY"]

# Your stock tickers
tickers = ["QBTS", "RGTI", "IONQ"]

# === Get headline from Finnhub ===
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

# === Vibe Score using OpenAI ===
def get_vibe_score(headline):
    prompt = f"Rate this headline from 1 (very bearish) to 10 (very bullish): {headline}"
    try:
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return float(res.choices[0].message.content.strip())
    except Exception as e:
        return 5.0  # neutral default

# === Calculate RSI Score ===
def calculate_rsi_score(data):
    rsi = ta.momentum.RSIIndicator(close=data["Close"]).rsi()
    latest_rsi = rsi.iloc[-1]
    # Normalize: lower RSI = higher score
    return (100 - latest_rsi) / 100, latest_rsi

# === Calculate Momentum Score ===
def calculate_momentum_score(data):
    recent_close = data["Close"].iloc[-1]
    past_close = data["Close"].iloc[-10] if len(data) >= 10 else recent_close
    pct_change = ((recent_close - past_close) / past_close) * 100
    return min(max((pct_change + 5) / 10, 0), 1), pct_change  # Normalize: range 0–1

# === Composite Signal Generator ===
def generate_final_signal(vibe, momentum, rsi_score):
    final_score = 0.4 * (vibe / 10) + 0.3 * momentum + 0.3 * rsi_score
    if final_score >= 0.7:
        return "📈 BUY", final_score
    elif final_score <= 0.3:
        return "📉 SELL", final_score
    else:
        return "⏸ HOLD", final_score

# === Streamlit Interface ===
st.title("📊 Pro-Style AI Trading Dashboard")

for ticker in tickers:
    st.subheader(f"{ticker} Analysis")

    data = yf.download(ticker, period="7d", interval="30m")
    st.line_chart(data["Close"])

    headline = fetch_headline(ticker)
    vibe = get_vibe_score(headline)
    rsi_score, rsi_value = calculate_rsi_score(data)
    momentum_score, pct_change = calculate_momentum_score(data)
    signal, final_score = generate_final_signal(vibe, momentum_score, rsi_score)

    st.write(f"📰 Headline: _{headline}_")
    st.write(f"🧠 Vibe Score: **{vibe:.1f}**")
    st.write(f"📉 RSI: **{rsi_value:.1f}**, RSI Score: {rsi_score:.2f}")
    st.write(f"📈 Momentum: **{pct_change:.2f}%**, Momentum Score: {momentum_score:.2f}")
    st.write(f"🤖 Composite Score: **{final_score:.2f}**")
    st.markdown(f"### 💡 Final AI Signal: **{signal}**")
    st.markdown("---")
