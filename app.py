import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta
from openai import OpenAI

# === Secrets ===
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# === UI ===
st.set_page_config(page_title="AI Trading Watchlist", layout="wide")
st.sidebar.header("Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("Refresh Data")    # Plain text fallback
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("\ud83d\udd01 Refresh Data")

# === Tickers ===
tickers = ["QBTS", "RGTI", "IONQ", "CRWV", "DBX", "TSM"]

# === Interval Logic ===
def get_interval(period):
    return {
        "1d": "5m",
        "5d": "15m",
        "1mo": "30m",
        "3mo": "1h",
        "6mo": "1d",
        "1y": "1d"
    }.get(period, "1d")

# === Fetch Price Data ===
@st.cache_data(ttl=30 if not refresh else 0, show_spinner=False)
def fetch_price_data(ticker, period):
    interval = get_interval(period)
    df = yf.download(ticker, period=period, interval=interval)
    if df.empty:
        return pd.DataFrame()
    df = df.reset_index()
    sma_window = 3 if period in ["1d", "5d"] else 10
    df['sma'] = df['Close'].rolling(window=sma_window).mean()
    return df

# === Fetch Headline ===
@st.cache_data(ttl=1800 if not refresh else 0, show_spinner=False)
def fetch_headline(ticker):
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
    response = requests.get(url)
    try:
        news = response.json()
        if news and isinstance(news, list) and len(news) > 0:
            return news[0]["headline"]
    except:
        pass
    return "No recent news found."

# === Analyze Vibe ===
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
        print("OpenAI Error:", e)
        return None

# === Parse Vibe ===
def parse_vibe_response(response):
    try:
        lines = response.splitlines()
        score_line = next((line for line in lines if "Score:" in line), None)
        score = int(score_line.split(":")[1].strip()) if score_line else None
        reasons = [line for line in lines if line.strip().startswith("-")]
        return score, reasons
    except:
        return None, []

# === Render App ===
st.title("\ud83e\udde0 AI Trading Watchlist")

for i in range(0, len(tickers), 3):
    row_tickers = tickers[i:i+3]
    cols = st.columns(3)
    for j, ticker in enumerate(row_tickers):
        with cols[j]:
            st.subheader(ticker)
            df = fetch_price_data(ticker, timeframe)

            if not df.empty and "Close" in df.columns and df["Close"].dropna().shape[0] > 2:
                x_vals = df['Datetime'] if 'Datetime' in df else df['Date'] if 'Date' in df else df.index
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=x_vals,
                    y=df['Close'],
                    mode='lines',
                    name='Price'
                ))
                fig.add_trace(go.Scatter(
                    x=x_vals,
                    y=df['sma'],
                    mode='lines',
                    name='SMA (10)'
                ))
                fig.update_layout(height=300, margin=dict(l=0,r=0,t=25,b=0), xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("\ud83d\udcc9 No price data found.")

            headline = fetch_headline(ticker)
            st.write(f"**Latest Headline:** {headline}")

            if headline != "No recent news found.":
                vibe_response = get_vibe_score(headline)
                score, reasons = parse_vibe_response(vibe_response)
                if score:
                    st.metric("Vibe Score", score)
                    st.markdown("\n".join(reasons))
                else:
                    st.info("\u26a0\ufe0f Unable to analyze headline sentiment.")
            else:
                st.info("No news to analyze.")
