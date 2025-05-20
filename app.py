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

# 🎛️ Sidebar
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔁 Refresh Data")

# 📈 Tickers
tickers = ["QBTS", "RGTI", "IONQ"]

# 🔎 Fetch News Headline
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_headline(ticker):
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        news = response.json()
        if isinstance(news, list) and len(news) > 0 and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return "⚠️ No recent news found."
    except Exception as e:
        return f"⚠️ Error fetching news: {e}"

# 🧠 Get Vibe Score
@st.cache_data(ttl=600, show_spinner=False)
def get_vibe_score(headline):
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
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Error getting vibe score: {e}"

# 📊 Get and Clean Stock Data
@st.cache_data(ttl=30, show_spinner=False)
def get_stock_data(ticker, timeframe):
    df = yf.download(ticker, period=timeframe)
    df.columns.name = None  # Clear multi-index if present
    df = df.reset_index()  # Flatten 'Date' into a column
    return df

# 🖼️ Dashboard Title
st.title("📊 AI-Powered Day Trading Dashboard")

# 🚀 Main Display Loop
for ticker in tickers:
    st.subheader(ticker)

    try:
        df = get_stock_data(ticker, timeframe)
        df.columns = [col if isinstance(col, str) else col[1] for col in df.columns]  # Flatten if multiindex
        if "Date" in df.columns:
            df.rename(columns={"Date": "date"}, inplace=True)

        fig = px.line(df, x="date", y="Close", title=f"{ticker} Close Price")
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")
        continue

    # 📢 Headline & Vibe
    headline = fetch_headline(ticker)
    st.markdown(f"📰 **Headline:** _{headline}_")

    vibe = get_vibe_score(headline)
    try:
        lines = vibe.strip().splitlines()
        score_line = next((line for line in lines if "Score:" in line), "Score: N/A")
        reasoning_lines = [line for line in lines if line.startswith("-")]

        score = score_line.split(":")[-1].strip()
        st.markdown(f"🧠 **Vibe Score:** {score}")

        st.markdown("💬 **Reasoning:**")
        for reason in reasoning_lines:
            st.markdown(f"- {reason.lstrip('- ').strip()}")
    except Exception as e:
        st.warning(f"Could not parse vibe score: {e}")

    st.markdown("---")
