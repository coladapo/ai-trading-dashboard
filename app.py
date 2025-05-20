import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from openai import OpenAI

# Set up OpenAI and Finnhub clients
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# Sidebar – Timeframe selector and Refresh button
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔄 Refresh Data")

# List of tickers
tickers = ["QBTS", "RGTI", "IONQ"]

# Function: Fetch latest news headline from Finnhub
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_headline(ticker):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        news = response.json()
        if news and isinstance(news, list) and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return "📰 No recent news found for ticker."
    except Exception as e:
        return f"⚠️ Error fetching news: {e}"

# Function: Get vibe score and reasoning from OpenAI
@st.cache_data(ttl=600, show_spinner=False)
def get_vibe_score(headline):
    prompt = f"""Analyze this stock market news headline:
"{headline}"

Rate it from 1 (very bearish) to 10 (very bullish). Then summarize your reasoning in 2–3 clear bullet points starting with "-".

Respond in this format:
Score: #
- Reason 1
- Reason 2
- Reason 3 (optional)
"""
    try:
        res = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"⚠️ OpenAI error: {e}"

# Function: Fetch price data
@st.cache_data(ttl=900, show_spinner=False)
def fetch_price_data(ticker, period):
    return yf.download(ticker, period=period, interval="30m")

# Clear cache manually if user clicks refresh
if refresh:
    st.cache_data.clear()

# Main UI
st.title("📊 AI-Powered Day Trading Dashboard")
for ticker in tickers:
    st.subheader(ticker)

    try:
        price_data = fetch_price_data(ticker, timeframe)
        price_data.reset_index(inplace=True)
        plt.figure(figsize=(8, 4))
        plt.plot(price_data["Date"], price_data["Close"], color="#1f77b4", linewidth=2)
        plt.title(f"{ticker} Close Price")
        plt.xlabel("Time")
        plt.ylabel("Price")
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(plt)
    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")
        continue

    # News and Vibe Score
    headline = fetch_headline(ticker)
    st.markdown(f"**📰 Headline:** *{headline}*")

    score_response = get_vibe_score(headline)
    if score_response.startswith("⚠️"):
        st.error(score_response)
        continue

    try:
        score_lines = score_response.strip().split("\n")
        score_line = score_lines[0].replace("Score:", "").strip()
        reasoning_lines = score_lines[1:]
        score = int(score_line)
        st.markdown(f"**🧠 Vibe Score:** <span style='color:limegreen'>{score}</span>", unsafe_allow_html=True)
        st.markdown("**💬 Reasoning:**")
        for line in reasoning_lines:
            if line.startswith("-"):
                st.markdown(f"- {line[1:].strip()}")

        # Basic AI Signal
        if score >= 8:
            st.markdown("**🤖 AI Signal:** 📈 Buy")
        elif score <= 3:
            st.markdown("**🤖 AI Signal:** 📉 Sell")
        else:
            st.markdown("**🤖 AI Signal:** 🤖 Hold")
    except Exception as e:
        st.error(f"Failed to analyze score for {ticker}: {e}")
