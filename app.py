import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
from openai import OpenAI

# 🔐 API keys
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# 📅 Sidebar UI
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔄 Refresh Data")

# 🧾 Watchlist
tickers = ["QBTS", "RGTI", "IONQ"]

# 📰 Latest News Headline
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
            return "⚠️ No recent news found."
    except Exception as e:
        return f"⚠️ Error fetching news: {e}"

# 🧠 Vibe Score
@st.cache_data(ttl=600, show_spinner=False)
def get_vibe_score(headline):
    prompt = f"""Analyze this stock market news headline:
\"{headline}\"

Rate it from 1 (very bearish) to 10 (very bullish). Then summarize your reasoning in 2–3 clear bullet points starting with "-".

Respond in this format:
Score: #
- Reason 1
- Reason 2
- Reason 3 (optional)
"""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error fetching Vibe Score: {e}"

# 📈 Fetch chart data
@st.cache_data(ttl=30 if not refresh else 0, show_spinner=False)
def get_stock_data(ticker, timeframe):
    df = yf.download(ticker, period=timeframe)
    df = df.reset_index()
    return df

# 📊 App layout
st.title("📊 AI-Powered Day Trading Dashboard")

for ticker in tickers:
    st.subheader(ticker)

    try:
        df = get_stock_data(ticker, timeframe)
        fig = px.line(df, x="Date", y="Close", title=f"{ticker} Close Price")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")
        continue

    # 📰 Headline
    headline = fetch_headline(ticker)
    st.markdown(f"📰 **Headline:** *{headline}*")

    # 🧠 Vibe Score + Breakdown
    vibe = get_vibe_score(headline)
    if vibe.startswith("Score:"):
        lines = vibe.splitlines()
        score_line = lines[0]
        reasoning = "\n".join(lines[1:])
        st.markdown(f"🧠 **Vibe Score:** {score_line.split(':')[1].strip()}")
        st.markdown("💬 **Reasoning:**")
        st.markdown(reasoning)
    else:
        st.markdown(vibe)
