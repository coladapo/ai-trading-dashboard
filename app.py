import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta
from openai import OpenAI, OpenAIError

# === Load API Keys from Streamlit Cloud Secrets ===
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# === Streamlit Page Config ===
st.set_page_config(page_title="🧠 AI Trading Watchlist", layout="wide")
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔁 Refresh Data")

# === Tickers to Watch ===
tickers = ["QBTS", "RGTI", "IONQ", "CRWV", "DBX", "TSM"]

# === Fetch Price Data ===
@st.cache_data(ttl=30 if not refresh else 0)
def fetch_price_data(ticker, period):
    interval = "5m" if period == "1d" else "1d"
    try:
        df = yf.download(ticker, period=period, interval=interval)
        if df.empty or "Close" not in df.columns:
            return pd.DataFrame()
        df = df.reset_index()
        df["sma"] = df["Close"].rolling(window=10).mean()
        return df
    except Exception as e:
        return pd.DataFrame()

# === Fetch Headline (Look back 7 days) ===
@st.cache_data(ttl=1800 if not refresh else 0)
def fetch_headline(ticker):
    today = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={from_date}&to={today}&token={finnhub_api_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            news = response.json()
            if isinstance(news, list) and len(news) > 0:
                return news[0]["headline"]
            else:
                return "No recent news found."
        else:
            return "❌ Finnhub API error"
    except Exception as e:
        return "❌ News error"

# === Analyze Headline Sentiment with OpenAI ===
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
    except OpenAIError as e:
        return "❌ OpenAI error"

def parse_vibe_response(response):
    try:
        lines = response.splitlines()
        score_line = next((line for line in lines if "Score:" in line), None)
        score = int(score_line.split(":")[1].strip()) if score_line else None
        reasons = [line for line in lines if line.strip().startswith("-")]
        return score, reasons
    except:
        return None, []

# === Display ===
st.title("🧠 AI Trading Watchlist")

cols = st.columns(3)
for idx, ticker in enumerate(tickers):
    col = cols[idx % 3]
    with col:
        st.subheader(ticker)
        df = fetch_price_data(ticker, timeframe)

        if not df.empty and "Close" in df.columns and df["Close"].notna().all():
            x_vals = df['Datetime'] if 'Datetime' in df else df['Date'] if 'Date' in df else df.index
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x_vals, y=df['Close'], mode="lines", name="Price"))
            fig.add_trace(go.Scatter(x=x_vals, y=df['sma'], mode="lines", name="SMA (10)"))
            fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📉 No price data found.")

        headline = fetch_headline(ticker)
        st.markdown(f"**Latest Headline:** {headline}")

        if "❌" not in headline and "No recent news" not in headline:
            vibe_response = get_vibe_score(headline)
            score, reasons = parse_vibe_response(vibe_response)
            if score:
                st.metric("Vibe Score", score)
                st.markdown("\n".join(reasons))
            else:
                st.info("⚠️ Unable to analyze sentiment.")
        else:
            st.info("No news to analyze.")

        if (idx + 1) % 3 == 0:
            cols = st.columns(3)
