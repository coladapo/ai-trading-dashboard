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

# Sidebar - Timeframe selection
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
        response = res.choices[0].message.content.strip()
        lines = response.split("\n")
        score_line = next((line for line in lines if line.lower().startswith("score")), "Score: ?")
        score = ''.join([c for c in score_line if c.isdigit()]) or "?"
        reasoning = "\n".join(line for line in lines if line.startswith("-"))
        return score, reasoning
    except Exception as e:
        return "?", f"Error: {e}"

# Function: Determine recommendation
def get_signal(vibe_score):
    try:
        score = int(vibe_score)
        if score >= 8:
            return "📈 Buy"
        elif score <= 3:
            return "🔻 Sell"
        else:
            return "🤖 Hold"
    except:
        return "⚠️ No recommendation"

# Main dashboard
st.title("📊 AI-Powered Day Trading Dashboard")

for ticker in tickers:
    st.subheader(ticker)

    # Fetch price data
    try:
        interval = "5m" if timeframe == "1d" else "1d"
        df = yf.download(ticker, period=timeframe, interval=interval)

        if df.empty:
            st.warning(f"No data for {ticker}")
            continue

        # Format x-axis
        df = df.reset_index()
        df["Formatted Time"] = df["Datetime" if "Datetime" in df else "Date"].dt.strftime("%m-%d %H:%M" if interval == "5m" else "%m-%d")

        # Plot chart
        fig, ax = plt.subplots()
        ax.plot(df["Formatted Time"], df["Close"], label=f"{ticker} Close Price", linewidth=2, color="dodgerblue")
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        ax.set_title(f"{ticker} Close Price")
        ax.tick_params(axis='x', labelrotation=45)
        st.pyplot(fig)

        # News
        headline = fetch_headline(ticker)
        st.markdown(f"📰 **Headline:** _{headline}_")

        # Vibe score + reasoning
        vibe_score, reasoning = get_vibe_score_and_reasoning(headline)
        st.markdown(f"🧠 **Vibe Score:** `{vibe_score}`")
        st.markdown("💬 **Reasoning:**")
        st.markdown(reasoning)

        # Recommendation
        signal = get_signal(vibe_score)
        st.markdown(f"🤖 **AI Signal:** {signal}")

    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")
