import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
from openai import OpenAI

# Set up OpenAI and Finnhub clients
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# Sidebar – Timeframe selector and Refresh button
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔁 Refresh Data")

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
            return "🚫 No recent news found for ticker."
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
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error getting score: {e}"

# Function: Fetch stock data from yfinance
@st.cache_data(ttl=900, show_spinner=False)
def get_stock_data(ticker, period):
    df = yf.download(ticker, period=period, interval="30m" if period == "1d" else "1d")
    df.reset_index(inplace=True)
    df.rename(columns={"Date": "date", "Close": "close"}, inplace=True)
    return df

# Function: Parse score and reasoning
def parse_vibe(vibe_raw):
    lines = vibe_raw.strip().split("\n")
    score_line = next((line for line in lines if "Score:" in line), "Score: ?")
    score = score_line.replace("Score:", "").strip()
    reasons = [line.strip("- ") for line in lines if line.strip().startswith("-")]
    return score, reasons

# Main
st.title("📊 AI-Powered Day Trading Dashboard")

for ticker in tickers:
    st.subheader(ticker)

    try:
        df = get_stock_data(ticker, timeframe)
        if df.empty:
            st.warning("No data found.")
            continue

        fig = px.line(df, x="date", y="close", title=f"{ticker} Close Price")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")
        continue

    headline = fetch_headline(ticker)
    st.markdown(f"📰 **Headline:** *{headline}*")

    vibe_raw = get_vibe_score(headline)
    score, reasons = parse_vibe(vibe_raw)

    st.markdown(f"**🧠 Vibe Score:** `{score}`")
    st.markdown("**💬 Reasoning:**")
    for reason in reasons:
        st.markdown(f"- {reason}")

    score_int = int(score) if score.isdigit() else 0
    if score_int >= 8:
        st.markdown("**🤖 AI Signal:** 📈 Buy")
    elif score_int >= 5:
        st.markdown("**🤖 AI Signal:** 🤖 Hold")
    else:
        st.markdown("**🤖 AI Signal:** 📉 Sell")
