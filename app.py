import streamlit as st
import yfinance as yf
import requests
from datetime import datetime
from openai import OpenAI
import os

# Setup API clients
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# Sidebar timeframe selector
st.sidebar.title("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=0)

# Chart intervals based on timeframe
intervals = {
    "1d": "5m",
    "5d": "15m",
    "1mo": "30m",
    "3mo": "1d",
    "6mo": "1d",
    "1y": "1d"
}
interval = intervals[timeframe]

# Tickers
tickers = ["QBTS", "RGTI", "IONQ"]

# Streamlit app title
st.title("📊 AI-Powered Day Trading Watchlist")

# Helper: fetch headline
def fetch_headline(ticker):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        news = response.json()
        if news and isinstance(news, list) and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return "No recent news found"
    except Exception as e:
        return f"Error fetching news: {e}"

# Helper: analyze vibe
def get_vibe_score_and_reasoning(headline):
    prompt = f"""Analyze the sentiment of this market news headline:
"{headline}"

First, give me a score from 1 (very bearish) to 10 (very bullish).
Then provide a brief reason for your score on a new line starting with "Reason:"."""
    try:
        res = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        output = res.choices[0].message.content.strip()
        lines = output.split("\n")
        score = "N/A"
        reason = "No explanation provided."
        for line in lines:
            if line.strip().isdigit():
                score = int(line.strip())
            elif "Reason:" in line:
                reason = line.split("Reason:")[-1].strip()
        return score, reason
    except Exception as e:
        return "N/A", f"Error analyzing vibe: {e}"

# Display chart + insights
for ticker in tickers:
    st.subheader(ticker)
    try:
        data = yf.download(ticker, period=timeframe, interval=interval)
        st.line_chart(data["Close"])

        headline = fetch_headline(ticker)
        score, reason = get_vibe_score_and_reasoning(headline)

        st.markdown(f"📰 **Headline:** *{headline}*")
        st.markdown(f"🧠 **Vibe Score:** `{score}`")
        st.markdown(f"✍️ **Reasoning:** {reason}")

        if isinstance(score, int):
            if score >= 8:
                signal = "📈 Buy"
            elif score <= 3:
                signal = "🔻 Sell"
            else:
                signal = "🤖 Hold"
        else:
            signal = "⚠️ No recommendation"

        st.markdown(f"🤖 **AI Signal:** {signal}")

    except Exception as e:
        st.error(f"Failed to analyze {ticker}: {e}")
