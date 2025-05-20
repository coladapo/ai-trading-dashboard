import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from openai import OpenAI
from functools import lru_cache

# Set up OpenAI and Finnhub API keys
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# Sidebar – Timeframe selector + Refresh Button
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])

if st.sidebar.button("🔁 Refresh Data"):
    st.cache_data.clear()
    st.experimental_rerun()

# List of tickers to analyze
tickers = ["QBTS", "RGTI", "IONQ"]

# Function: Fetch latest headline using Finnhub API
def fetch_headline(ticker):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        news = response.json()
        if news and isinstance(news, list) and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return "No recent news found."
    except Exception as e:
        return f"Error fetching news: {e}"

# Function: Get Vibe Score and reasoning from OpenAI
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
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = res.choices[0].message.content.strip()

        lines = response_text.splitlines()
        score_line = next((line for line in lines if line.lower().startswith("score:")), "Score: 0")
        score = int(score_line.split(":")[1].strip())

        reasoning = "\n".join(line for line in lines if line.startswith("-"))
        return score, reasoning
    except Exception as e:
        return 0, f"⚠️ Error from OpenAI: {e}"

# Cached Function: Fetch stock data
@st.cache_data(ttl=900)  # Cache for 15 minutes
def get_stock_data(ticker, timeframe):
    return yf.download(ticker, period=timeframe)

# Main Display
st.title("📊 AI-Powered Day Trading Dashboard")

for ticker in tickers:
    st.subheader(ticker)

    try:
        df = get_stock_data(ticker, timeframe)
        if df.empty:
            st.warning("No data found.")
            continue

        fig, ax = plt.subplots()
        ax.plot(df.index, df["Close"], color="dodgerblue", linewidth=2)
        ax.set_title(f"{ticker} Close Price")
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        ax.tick_params(axis='x', labelrotation=30)
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")
        continue

    # Headline
    headline = fetch_headline(ticker)
    st.markdown(f"📰 **Headline:** *{headline}*")

    # Vibe Score + Reasoning
    score, reasoning = get_vibe_score(headline)
    st.markdown(f"🧠 **Vibe Score:** <span style='color:#0f0'>{score}</span>", unsafe_allow_html=True)
    st.markdown("💬 **Reasoning:**")
    st.markdown(f"<ul>{''.join(f'<li>{line[2:]}</li>' for line in reasoning.splitlines())}</ul>", unsafe_allow_html=True)

    # Simple AI Signal
    if score >= 8:
        signal = "📈 Buy"
    elif score <= 3:
        signal = "🔻 Sell"
    else:
        signal = "🤖 Hold"

    st.markdown(f"🧠 **AI Signal:** {signal}")
    st.markdown("---")
