import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime
from openai import OpenAI

# === API Setup ===
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# === UI ===
st.set_page_config(page_title="AI Trading Watchlist", layout="wide")
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔁 Refresh Data")

# === Tickers ===
tickers = ["QBTS", "RGTI", "IONQ"]

# === Fetch Price Data ===
@st.cache_data(ttl=30 if not refresh else 0, show_spinner=False)
def fetch_price_data(ticker, period):
    interval = "5m" if period == "1d" else "1d"
    df = yf.download(ticker, period=period, interval=interval)
    df = df.reset_index()
    df['sma'] = df['Close'].rolling(window=10).mean()
    return df

# === Fetch News Headline ===
@st.cache_data(ttl=1800 if not refresh else 0, show_spinner=False)
def fetch_headline(ticker):
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
    response = requests.get(url)
    news = response.json()
    if news and isinstance(news, list):
        return news[0]["headline"]
    return "No recent news found."

# === Vibe Score ===
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
    res = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    output = res.choices[0].message.content.strip()
    return output

def parse_vibe_response(response):
    try:
        lines = response.splitlines()
        score_line = next((line for line in lines if "Score:" in line), None)
        score = int(score_line.split(":")[1].strip()) if score_line else None
        reasons = [line for line in lines if line.strip().startswith("-")]
        return score, reasons
    except:
        return None, []

# === Display ===
st.title("
