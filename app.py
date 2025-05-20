import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from openai import OpenAI

# === API Setup ===
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# === UI ===
st.set_page_config(page_title="AI Trading Dashboard", layout="wide")
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔁 Refresh Data")

# === Tickers ===
tickers = ["QBTS", "RGTI", "IONQ"]

# === Caching with Refresh Logic ===
@st.cache_data(ttl=30 if not refresh else 0, show_spinner=False)
def fetch_price_data(ticker, period):
    data = yf.download(ticker, period=period, interval="5m" if period == "1d" else "1d")
    return data.reset_index()

@st.cache_data(ttl=1800 if not refresh else 0, show_spinner=False)
def fetch_headline(ticker):
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
    response = requests.get(url)
    news = response.json()
    if news and isinstance(news, list):
        return news[0]["headline"]
    return "No recent news found."

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

# === Display per Ticker ===
st.title("📊 AI-Powered Day Trading Dashboard")

for ticker in tickers:
    st.subheader(ticker)
    try:
        df = fetch_price_data(ticker, timeframe)
        fig, ax = plt.subplots()
        ax.plot(df['Datetime' if timeframe == "1d" else 'Date'], df['Close'], color="dodgerblue", linewidth=2)
        ax.set_title(f"{ticker} Close Price", fontsize=14)
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        ax.tick_params(axis='x', rotation=45)
        st.pyplot(fig)

        # --- News + Analysis ---
        headline = fetch_headline(ticker)
        st.markdown(f"📰 **Headline:** _{headline}_")

        response = get_vibe_score(headline)
        score, reasons = parse_vibe_response(response)

        st.markdown(f"🧠 **Vibe Score:** <span style='color:mediumseagreen;font-weight:bold'>{score}</span>", unsafe_allow_html=True)

        if reasons:
            st.markdown("💬 **Reasoning:**")
            for reason in reasons:
                clean_reason = reason.lstrip("-• ").strip()
                st.markdown(f"- {clean_reason}")
        else:
            st.markdown("*Unable to parse AI reasoning.*")

        st.divider()

    except Exception as e:
        st.error(f"⚠️ Failed to load data for {ticker}: {e}")
