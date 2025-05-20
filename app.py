import streamlit as st
import yfinance as yf
import requests
from datetime import datetime
import pandas as pd
from openai import OpenAI
import matplotlib.pyplot as plt

# Setup page layout
st.set_page_config(layout="wide")
st.title("📊 AI-Powered Day Trading Dashboard")

# Sidebar for timeframe selection
st.sidebar.header("🗓️ Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])

# API Keys from Streamlit Secrets
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_key = st.secrets["FINNHUB_API_KEY"]

# List of tickers to analyze
tickers = ["QBTS", "RGTI", "IONQ"]

# === FUNCTIONS ===

def fetch_headline(ticker):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_key}"
        response = requests.get(url)
        news = response.json()
        if news and isinstance(news, list) and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return f"No news found for {ticker} today"
    except Exception as e:
        return f"Error fetching news: {e}"

def get_vibe_score_and_reasoning(headline):
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
        content = res.choices[0].message.content.strip()
        score_line, *reason_lines = content.split("\n")
        score = int(score_line.replace("Score:", "").strip())
        reasons = [line.strip("- ").strip() for line in reason_lines if line.strip()]
        return score, reasons
    except Exception as e:
        return "N/A", [f"Error: {e}"]

def get_signal(score):
    if isinstance(score, int):
        if score >= 8:
            return "📈 Buy"
        elif score <= 3:
            return "📉 Sell"
        else:
            return "🤖 Hold"
    return "⚠️ No recommendation"

# === MAIN LOOP ===

for ticker in tickers:
    st.subheader(ticker)
    try:
        df = yf.download(ticker, period=timeframe, interval="5m" if timeframe == "1d" else "1d")
        if df.empty or "Close" not in df:
            raise ValueError("No price data available.")

        # Plot chart using matplotlib
        fig, ax = plt.subplots()
        ax.plot(df.index, df["Close"], color="deepskyblue", linewidth=2)
        ax.set_title(f"{ticker} Close Price", fontsize=14)
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        ax.grid(True, linestyle="--", linewidth=0.5)
        st.pyplot(fig)

        # Headline, Score, Reasoning
        headline = fetch_headline(ticker)
        score, reasoning = get_vibe_score_and_reasoning(headline)
        signal = get_signal(score)

        st.markdown(f"📰 **Headline:** *{headline}*")
        st.markdown(f"🧠 **Vibe Score:** `{score}`")
        st.markdown("💬 **Reasoning:**")
        for r in reasoning:
            st.markdown(f"- {r}")
        st.markdown(f"🤖 **AI Signal:** {signal}")
        st.markdown("---")

    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")
