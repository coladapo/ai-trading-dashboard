import streamlit as st
import yfinance as yf
from openai import OpenAI
import requests
from datetime import datetime
import pandas as pd
import streamlit.components.v1 as components

# Force sidebar to open by default
components.html(
    "<script>document.querySelector('section[data-testid=stSidebar]').style.display = 'block';</script>",
    height=0
)

# Set up API keys
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# Sidebar settings
st.sidebar.title("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
interval_map = {
    "1d": "5m",
    "5d": "15m",
    "1mo": "30m",
    "3mo": "1h",
    "6mo": "1d",
    "1y": "1d"
}
interval = interval_map[timeframe]

# Watchlist
tickers = ["QBTS", "RGTI", "IONQ"]

# Functions
def fetch_headline(ticker):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        res = requests.get(url).json()
        if res and isinstance(res, list) and "headline" in res[0]:
            return res[0]["headline"]
        else:
            return f"No news for {ticker} today."
    except Exception as e:
        return f"Error: {e}"

def get_vibe_score(headline):
    prompt = f"Rate this stock market news headline from 1 (very bearish) to 10 (very bullish): {headline}"
    try:
        res = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

def interpret_signal(vibe):
    try:
        score = int(vibe)
        if score >= 8:
            return "📈 Buy"
        elif score <= 3:
            return "🔻 Sell"
        else:
            return "🤖 Hold"
    except:
        return "⚠️ No recommendation"

# App layout
st.title("📊 AI-Powered Day Trading Watchlist")

for ticker in tickers:
    st.subheader(ticker)

    try:
        data = yf.download(ticker, period=timeframe, interval=interval)
        st.line_chart(data["Close"])

        headline = fetch_headline(ticker)
        vibe = get_vibe_score(headline)
        signal = interpret_signal(vibe)

        st.markdown(f"📰 **Headline:** *{headline}*")
        st.markdown(f"🧠 **Vibe Score:** `{vibe}`")
        st.markdown(f"🤖 **AI Signal:** {signal}")
        st.markdown("---")

    except Exception as e:
        st.error(f"Failed to analyze {ticker}: {e}")
