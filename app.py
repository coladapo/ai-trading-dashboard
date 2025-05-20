import streamlit as st
import yfinance as yf
import requests
from openai import OpenAI
from datetime import datetime

# Set up API clients
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# Sidebar chart timeframe
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])

# List of tickers
tickers = ["QBTS", "RGTI", "IONQ"]

# Fetch the latest headline
def fetch_headline(ticker):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        res = requests.get(url)
        news = res.json()
        if news and isinstance(news, list) and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return f"No recent news found for {ticker}"
    except Exception as e:
        return f"Error fetching news: {e}"

# Analyze headline
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
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

# App layout
st.title("📊 AI-Powered Day Trading Watchlist")

for ticker in tickers:
    st.subheader(ticker)

    # Chart
    try:
        data = yf.download(ticker, period=timeframe, interval="5m" if timeframe == "1d" else "1d")
        st.line_chart(data["Close"])
    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")
        continue

    # Headline
    headline = fetch_headline(ticker)
    st.markdown(f"📰 **Headline:** _{headline}_")

    # Vibe Score + Reasoning
    result = get_vibe_score_and_reasoning(headline)
    if result.startswith("Error"):
        st.markdown(f"🧠 **Vibe Score:** {result}")
        st.markdown("🤖 **AI Signal:** ⚠️ No recommendation")
        continue

    try:
        lines = result.splitlines()
        score_line = next((line for line in lines if "Score:" in line), None)
        score = int(score_line.split(":")[1].strip()) if score_line else None
        reasons = "\n".join([line for line in lines if line.startswith("-")])

        st.markdown(f"🧠 **Vibe Score:** `{score}`")
        st.markdown(f"📝 **Reasoning:**\n{reasons}")

        if score >= 8:
            st.markdown("🤖 **AI Signal:** 📈 Buy")
        elif score <= 3:
            st.markdown("🤖 **AI Signal:** 📉 Sell")
        else:
            st.markdown("🤖 **AI Signal:** 🤖 Hold")

    except Exception as e:
        st.error(f"Response parsing error: {e}")
