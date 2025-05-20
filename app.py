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
            return "⚠️ No recent news found for ticker."
    except Exception as e:
        return f"⚠️ Error fetching news: {e}"

# Function: Get vibe score and reasoning from OpenAI
@st.cache_data(ttl=60, show_spinner=False)
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
        return f"⚠️ Error fetching Vibe Score: {e}"

# Function: Fetch historical price data
@st.cache_data(ttl=30)
def get_stock_data(ticker, tf):
    data = yf.download(ticker, period=tf)
    data.reset_index(inplace=True)
    data.columns = [col.lower() if isinstance(col, str) else col for col in data.columns]
    return data

# Function: Parse Vibe Score & Reasoning
def parse_vibe(vibe_output):
    lines = vibe_output.split("\n")
    score = None
    reasons = []
    for line in lines:
        if line.lower().startswith("score"):
            try:
                score = int("".join(filter(str.isdigit, line)))
            except:
                score = "❓"
        elif line.startswith("-"):
            reasons.append(line.strip("- "))
    return score, reasons

# UI Rendering
st.title("📊 AI-Powered Day Trading Dashboard")

for ticker in tickers:
    st.subheader(f"{ticker}")
    try:
        df = get_stock_data(ticker, timeframe)
        fig = px.line(df, x="date", y="close", title=f"{ticker} Close Price")
        st.plotly_chart(fig, use_container_width=True)

        headline = fetch_headline(ticker)
        st.markdown(f"**🗞 Headline:** *{headline}*")

        vibe_output = get_vibe_score(headline)
        score, reasons = parse_vibe(vibe_output)
        st.markdown(f"**🧠 Vibe Score:** <span style='color:limegreen;font-weight:bold'>{score}</span>", unsafe_allow_html=True)
        st.markdown("**💬 Reasoning:**")
        for r in reasons:
            st.markdown(f"- {r}")

        if isinstance(score, int):
            if score >= 8:
                st.markdown("**🤖 AI Signal:** 📈 Buy")
            elif score >= 5:
                st.markdown("**🤖 AI Signal:** 🤖 Hold")
            else:
                st.markdown("**🤖 AI Signal:** 📉 Sell")
        else:
            st.markdown("**🤖 AI Signal:** ⚠️ No recommendation")

    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")

# Refresh Button Logic
if refresh:
    st.cache_data.clear()
    st.experimental_rerun()
