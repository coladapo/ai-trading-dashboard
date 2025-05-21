import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta
from openai import OpenAI, OpenAIError

# === API Keys from Streamlit Cloud Secrets ===
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
@st.cache_data(ttl=60 if not refresh else 0, show_spinner=False)
def fetch_price_data(ticker, period):
    try:
        interval = "5m" if period == "1d" else "1d"
        df = yf.download(ticker, period=period, interval=interval)
        if df.empty or "Close" not in df.columns:
            return pd.DataFrame()
        df = df.reset_index()
        df['sma'] = df['Close'].rolling(window=10).mean()
        return df
    except Exception:
        return pd.DataFrame()

# === Fetch Headline ===
@st.cache_data(ttl=1800 if not refresh else 0, show_spinner=False)
def fetch_headline(ticker):
    today = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={from_date}&to={today}&token={finnhub_api_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            news = response.json()
            if news and isinstance(news, list) and len(news) > 0:
                return news[0]["headline"]
            return "No recent news found."
        return "❌ Finnhub API error"
    except:
        return "❌ News fetch error"

# === Analyze Headline Sentiment ===
def get_vibe_score(headline):
    prompt = f"""Analyze this stock market news headline:
"{headline}"

Rate it from 1 (very bearish) to 10 (very bullish). Then summarize your reasoning in 2–3 bullet points starting with "-".

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
    except OpenAIError:
        return "Score: N/A\n- OpenAI API error."

def parse_vibe_response(response):
    try:
        lines = response.splitlines()
        score_line = next((line for line in lines if "Score:" in line), None)
        score = int(score_line.split(":")[1].strip()) if score_line else None
        reasons = [line for line in lines if line.strip().startswith("-")]
        return score, reasons
    except:
        return None, []

# === Display Section ===
st.markdown("## 🧠 AI Trading Watchlist")

cols = st.columns(3)
for i, ticker in enumerate(tickers):
    if i % 3 == 0 and i != 0:
        cols = st.columns(3)
    with cols[i % 3]:
        st.subheader(ticker)
        df = fetch_price_data(ticker, timeframe)

        # === Chart ===
        if not df.empty and df["Close"].notna().sum() > 0:
            x = df['Datetime'] if 'Datetime' in df else df['Date'] if 'Date' in df else df.index
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x, y=df["Close"], mode="lines", name="Price"))
            fig.add_trace(go.Scatter(x=x, y=df["sma"], mode="lines", name="SMA (10)"))
            fig.update_layout(height=250, margin=dict(l=0, r=0, t=20, b=0), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📉 No valid price data found.")

        # === News & Vibe Score ===
        headline = fetch_headline(ticker)
        st.markdown(f"**Latest Headline:** {headline}")
        if headline and not headline.startswith("❌") and headline != "No recent news found.":
            vibe_response = get_vibe_score(headline)
            score, reasons = parse_vibe_response(vibe_response)
            if score:
                st.metric("Vibe Score", score)
                st.markdown("\n".join(reasons))
            else:
                st.info("⚠️ Unable to parse vibe score.")
        else:
            st.info("📰 No news to analyze.")
