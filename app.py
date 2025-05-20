import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
from openai import OpenAI

# 🔐 API keys from Streamlit secrets
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# 📅 Sidebar settings
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔄 Refresh Data")

# 🧠 Watchlist tickers
tickers = ["QBTS", "RGTI", "IONQ"]

# 📰 News headline fetcher
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

# 🤖 AI Vibe Score
@st.cache_data(ttl=600, show_spinner=False)
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
        return f"⚠️ Error from OpenAI: {e}"

# 📊 Stock data loader
@st.cache_data(ttl=300, show_spinner=False)
def get_stock_data(ticker, tf):
    df = yf.download(ticker, period=tf, interval="5m" if tf == "1d" else "1d")
    df = df.reset_index()
    df.rename(columns={df.columns[0]: "Datetime"}, inplace=True)  # Ensure datetime column is named properly
    return df

# 🔄 Refresh cache manually
if refresh:
    st.cache_data.clear()

# 📋 Dashboard Title
st.title("📊 AI-Powered Day Trading Dashboard")

# 🔁 Loop through tickers
for ticker in tickers:
    st.subheader(ticker)

    # News
    headline = fetch_headline(ticker)
    st.markdown(f"📰 **Headline:** *{headline}*")

    # Vibe Score
    analysis = get_vibe_score(headline)
    if "Score:" in analysis:
        lines = analysis.split("\n")
        score_line = next((line for line in lines if line.startswith("Score:")), "Score: ?")
        reasons = [line for line in lines if line.startswith("-")]
        score = score_line.split(":")[1].strip()

        st.markdown(f"🧠 **Vibe Score:** {score}")
        st.markdown("💬 **Reasoning:**")
        for r in reasons:
            st.markdown(f"- {r[1:].strip()}")
    else:
        st.warning("⚠️ Could not parse AI response.")
        st.text(analysis)

    # Chart
    try:
        df = get_stock_data(ticker, timeframe)
        fig = px.line(df, x="Datetime", y="Close", title=f"{ticker} Close Price")
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=400)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")
    
