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

# Sidebar controls
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
interval_map = {
    "1d": "5m",
    "5d": "15m",
    "1mo": "30m",
    "3mo": "1h",
    "6mo": "1h",
    "1y": "1d"
}
interval = interval_map[timeframe]

# Tickers to track
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

# Function: Get vibe score and reasoning from OpenAI
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
        score_line = next((line for line in reply.splitlines() if line.startswith("Score:")), None)
        score = int(score_line.split(":")[1].strip()) if score_line else 0
        reasons = "\n".join([line for line in reply.splitlines() if line.startswith("-")])
        return score, reasons
    except Exception as e:
        return 0, f"Error analyzing headline: {e}"

# Function: Get AI trading recommendation
def get_ai_signal(score):
    if score >= 8:
        return "
