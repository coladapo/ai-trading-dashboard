import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from openai import OpenAI
import re

# Set up OpenAI and Finnhub clients
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# Sidebar – Timeframe selector
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])

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
            return "No recent news found."
    except Exception as e:
        return f"Error fetching news: {e}"

# Function: Get vibe score and explanation from OpenAI
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
        reply = res.choices[0].message.content.strip()
        score_match = re.search(r"Score: (\d+)", reply)
        reasoning = re.findall(r"- (.*)", reply)
        score = int(score_match.group(1)) if score_match else "N/A"
        return score, reasoning
    except Exception as e:
        return f"Error: {e}", []

# Function: Get AI trading signal
def get_signal(vibe_score):
    try:
        vibe_score = int(vibe_score)
        if vibe_score >= 8:
            return "📈 Buy"
        elif vibe_score <= 3:
            return "📉 Sell"
        else:
            return "🤖 Hold"
    except:
        return "⚠️ No recommendation"

# Dashboard title
st.markdown("""
# 📊 AI-Powered Day Trading Dashboard
""")

# Main loop
for ticker in tickers:
    st.subheader(ticker)
    try:
        # Fetch data
        data = yf.download(ticker, period=timeframe, interval="5m" if timeframe == "1d" else "1d")
        if data.empty:
            st.warning("No price data available.")
            continue

        # Plotting
        fig, ax = plt.subplots()
        ax.plot(data.index, data["Close"], color="#1f77b4")
        ax.set_title(f"{ticker} Close Price")
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        fig.autofmt_xdate()
        st.pyplot(fig)

        # News and Vibe
        headline = fetch_headline(ticker)
        vibe_score, reasoning = get_vibe_score_and_reasoning(headline)
        signal = get_signal(vibe_score)

        st.markdown(f"**📰 Headline:** *{headline}*")
        st.markdown(f"**🧠 Vibe Score:** <span style='color: green;'>{vibe_score}</span>", unsafe_allow_html=True)
        st.markdown("**💬 Reasoning:**")
        for point in reasoning:
            st.markdown(f"- {point}")
        st.markdown(f"**🤖 AI Signal:** {signal}")

    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")
    
