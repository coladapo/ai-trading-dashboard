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

# Sidebar – Timeframe Selector
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])

# Refresh Button
if st.sidebar.button("🔁 Refresh Data"):
    st.cache_data.clear()

# List of tickers
tickers = ["QBTS", "RGTI", "IONQ"]

# Function: Fetch latest news headline from Finnhub
@st.cache_data(ttl=300)
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

# Function: Get vibe score from OpenAI
async def get_vibe_score(headline):
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
        return f"Error: {e}"

# Main Dashboard
st.title("📊 AI-Powered Day Trading Dashboard")

for ticker in tickers:
    st.subheader(ticker)

    # Skip cache for price data to keep it real-time
    try:
        df = yf.download(ticker, period=timeframe, progress=False)
        if df.empty:
            st.warning("No price data available.")
            continue

        fig, ax = plt.subplots()
        ax.plot(df.index, df['Close'], label=f'{ticker} Close Price', color='dodgerblue')
        ax.set_title(f"{ticker} Close Price")
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        ax.legend()
        fig.autofmt_xdate()
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")
        continue

    # Headline + Vibe Score + AI Reasoning
    headline = fetch_headline(ticker)
    st.markdown(f"**📰 Headline:** _{headline}_")

    response = st.experimental_sync(get_vibe_score)(headline)
    if "Score:" in response:
        try:
            score_line = response.split("\n")[0]
            score = score_line.replace("Score:", "").strip()
            st.markdown(f"**🧠 Vibe Score:** `{score}`")

            st.markdown("**💬 Reasoning:**")
            st.markdown("\n".join(response.split("\n")[1:]))
        except:
            st.markdown(f"**Vibe Score:** {response}")
    else:
        st.markdown(f"**Vibe Score:** {response}")
