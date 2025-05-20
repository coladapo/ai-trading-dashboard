import streamlit as st
import yfinance as yf
from openai import OpenAI
import requests
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

# Set API keys
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# Sidebar timeframe selector
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox(
    "Select timeframe",
    options=["1d", "5d", "1mo", "3mo", "6mo", "1y"],
    index=0
)

# Tickers to analyze
tickers = ["QBTS", "RGTI", "IONQ"]

# Headline fetcher
def fetch_headline(ticker):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        news = response.json()
        if news and isinstance(news, list) and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return f"No recent news found for {ticker}"
    except Exception as e:
        return f"Error fetching news: {e}"

# Vibe scorer
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
        return f"Error: {e}"

# Plot and display logic
st.title("📊 AI-Powered Day Trading Dashboard")

for ticker in tickers:
    st.subheader(ticker)

    try:
        # Load data
        interval = "5m" if timeframe == "1d" else "1d"
        df = yf.download(ticker, period=timeframe, interval=interval)

        # Clean up data for plotting
        if df.empty or "Close" not in df:
            raise ValueError("No close price data available.")

        # Plot
        fig, ax = plt.subplots()
        ax.plot(df.index, df["Close"], color="skyblue", linewidth=2)
        ax.set_title(f"{ticker} Close Price")
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        ax.grid(True)
        st.pyplot(fig)

        # Headline + Vibe
        headline = fetch_headline(ticker)
        st.markdown(f"📰 **Headline:** *{headline}*")

        score_text = get_vibe_score(headline)
        if "Score:" in score_text:
            parts = score_text.split("Score:")
            score = parts[1].split("\n")[0].strip()
            reasons = "\n".join(parts[1].split("\n")[1:]).strip()
            st.markdown(f"🧠 **Vibe Score:** `{score}`")
            st.markdown(f"💬 **Reasoning:**\n{reasons}")
        else:
            st.markdown(f"🧠 **Vibe Score:** *{score_text}*")

        # Signal based on score
        try:
            score_int = int(score)
            if score_int >= 8:
                signal = "📈 Buy"
            elif score_int <= 3:
                signal = "📉 Sell"
            else:
                signal = "🤖 Hold"
        except:
            signal = "⚠️ No recommendation"
        st.markdown(f"🤖 **AI Signal:** {signal}")

    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")
