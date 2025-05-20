import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from openai import OpenAI
import time

# Set up OpenAI and Finnhub
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# Sidebar: Chart timeframe + refresh
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔄 Refresh Data")

# Tickers to track
tickers = ["QBTS", "RGTI", "IONQ"]

# Optional cache clearing for live updates
@st.cache_data(ttl=900, show_spinner=False)
def get_stock_data(ticker, timeframe):
    return yf.download(ticker, period=timeframe)

# Finnhub headline fetch
def fetch_headline(ticker):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        news = response.json()
        if news and isinstance(news, list) and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return "No recent headline found."
    except Exception as e:
        return f"Error fetching news: {e}"

# OpenAI Vibe Score & Reasoning
def get_vibe_score_and_reasons(headline):
    prompt = f"""
Analyze this stock market news headline:
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
            temperature=0.4
        )
        response = res.choices[0].message.content.strip()
        lines = response.splitlines()
        score_line = next((line for line in lines if "Score" in line), None)
        reasoning_lines = [line for line in lines if line.startswith("-")]

        score = int("".join(filter(str.isdigit, score_line)))
        return score, reasoning_lines
    except Exception as e:
        return None, [f"❌ Error: {e}"]

# Clear cache if user hits refresh
if refresh:
    get_stock_data.clear()

# Dashboard Title
st.markdown("# 📊 AI-Powered Day Trading Dashboard")

# Main Ticker Loop
for ticker in tickers:
    st.subheader(ticker)
    try:
        df = get_stock_data(ticker, timeframe)

        if df.empty or "Close" not in df.columns:
            st.warning(f"No price data available for {ticker} with timeframe '{timeframe}'.")
            continue

        fig, ax = plt.subplots()
        ax.plot(df.index, df["Close"], color="dodgerblue", linewidth=2)
        ax.set_title(f"{ticker} Close Price")
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        fig.autofmt_xdate()
        st.pyplot(fig)

        # Headline & Vibe
        headline = fetch_headline(ticker)
        st.markdown(f"📰 **Headline:** *{headline}*")

        vibe_score, reasons = get_vibe_score_and_reasons(headline)
        if vibe_score is not None:
            st.markdown(f"🧠 **Vibe Score:** `{vibe_score}`")

            st.markdown("💬 **Reasoning:**")
            for reason in reasons:
                st.markdown(f"- {reason}")

            # Signal
            if vibe_score >= 8:
                st.markdown("🤖 **AI Signal:** 📈 **Buy**")
            elif vibe_score <= 3:
                st.markdown("🤖 **AI Signal:** 📉 **Sell**")
            else:
                st.markdown("🤖 **AI Signal:** 🤖 **Hold**")
        else:
            st.markdown("❌ Could not generate Vibe Score.")

        st.markdown("---")

    except Exception as e:
        st.error(f"⚠️ Error for {ticker}: {e}")
