import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from openai import OpenAI

# Set up API clients
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# Sidebar for timeframe selection
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox(
    "Select timeframe",
    options=["1d", "5d", "1mo", "3mo", "6mo", "1y"],
    index=0
)

# List of tickers to track
tickers = ["QBTS", "RGTI", "IONQ"]

# Function: Fetch news headline from Finnhub
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

# Function: Get Vibe Score from OpenAI
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
        response = res.choices[0].message.content.strip()
        lines = response.split("\n")
        score_line = next((line for line in lines if line.startswith("Score:")), None)
        reasoning_lines = [line for line in lines if line.startswith("-")]
        
        if score_line:
            score = int(score_line.split(":")[1].strip())
        else:
            score = "N/A"

        return score, reasoning_lines
    except Exception as e:
        return "N/A", [f"Error: {e}"]

# Function: Determine signal based on score
def get_signal(score):
    if isinstance(score, int):
        if score >= 8:
            return ("📈 Buy", "green")
        elif score <= 3:
            return ("📉 Sell", "red")
        else:
            return ("🤖 Hold", "gray")
    return ("⚠️ No recommendation", "orange")

# Title
st.title("📊 AI-Powered Day Trading Dashboard")

# Main loop for tickers
for ticker in tickers:
    st.subheader(ticker)

    try:
        data = yf.download(ticker, period=timeframe, interval="5m")
        fig, ax = plt.subplots()
        ax.plot(data.index, data['Close'], color='dodgerblue', linewidth=2)
        ax.set_title(f"{ticker} Close Price")
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%m-%d %H:%M"))
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)

        # News and AI Sentiment
        headline = fetch_headline(ticker)
        st.markdown(f"📰 **Headline:** *{headline}*")

        score, reasons = get_vibe_score(headline)
        st.markdown(f"\n
:brain: **Vibe Score:** <span style='color:green'><b>{score}</b></span>", unsafe_allow_html=True)

        st.markdown("**💬 Reasoning:**")
        for reason in reasons:
            st.markdown(f"- {reason}")

        signal_text, signal_color = get_signal(score)
        st.markdown(f"\n
:robot_face: **AI Signal:** <span style='color:{signal_color}'><b>{signal_text}</b></span>", unsafe_allow_html=True)

        st.markdown("---")

    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")
