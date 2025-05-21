import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from openai import OpenAI

# === Try pandas_ta ===
try:
    import pandas_ta as ta
    ta_enabled = True
except ImportError:
    ta_enabled = False

# === Secrets ===
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# === UI Setup ===
st.set_page_config(page_title="AI Trading Watchlist", layout="wide")
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔁 Refresh Data")
tickers = ["QBTS", "RGTI", "IONQ", "CRWV", "DBX", "TSM"]

# === Fetch Price Data ===
@st.cache_data(ttl=30 if not refresh else 0, show_spinner=False)
def fetch_price_data(ticker, period):
    interval = "5m" if period == "1d" else "1d"
    df = yf.download(ticker, period=period, interval=interval)
    return df.reset_index()

# === Fetch Headline ===
@st.cache_data(ttl=1800 if not refresh else 0, show_spinner=False)
def fetch_headline(ticker):
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
    response = requests.get(url)
    news = response.json()
    if news and isinstance(news, list):
        return news[0]["headline"]
    return "No recent news found."

# === Vibe Score via GPT ===
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
    return res.choices[0].message.content.strip()

def parse_vibe_response(response):
    try:
        lines = response.splitlines()
        score_line = next((line for line in lines if "Score:" in line), None)
        score = int(score_line.split(":")[1].strip()) if score_line else None
        reasons = [line for line in lines if line.strip().startswith("-")]
        return score, reasons
    except:
        return None, []

# === Pattern Detection ===
def detect_pattern(df):
    try:
        if not ta_enabled or "Close" not in df:
            return None
        df['sma_fast'] = df['Close'].rolling(window=5).mean()
        df['sma_slow'] = df['Close'].rolling(window=20).mean()
        if df['sma_fast'].iloc[-1] > df['sma_slow'].iloc[-1] and df['sma_fast'].iloc[-2] <= df['sma_slow'].iloc[-2]:
            return "Golden Cross"
        elif df['sma_fast'].iloc[-1] < df['sma_slow'].iloc[-1] and df['sma_fast'].iloc[-2] >= df['sma_slow'].iloc[-2]:
            return "Death Cross"
        return None
    except Exception:
        return None

# === Main App ===
st.title("📊 AI-Powered Day Trading Watchlist")

for ticker in tickers:
    try:
        df = fetch_price_data(ticker, timeframe)
        headline = fetch_headline(ticker)
        vibe_response = get_vibe_score(headline)
        score, reasons = parse_vibe_response(vibe_response)
        score_display = f" ({score}/10)" if score else ""

        with st.expander(f"{ticker}{score_display}", expanded=False):
            # === Chart ===
            fig, ax = plt.subplots()
            time_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
            ax.plot(df[time_col], df['Close'], color="dodgerblue", linewidth=2)
            ax.set_title(f"{ticker} Close Price")
            ax.set_xlabel("Time")
            ax.set_ylabel("Price")
            ax.tick_params(axis='x', rotation=45)
            st.pyplot(fig)

            # === News + Vibe ===
            st.markdown(f"📰 **Headline:** _{headline}_")

            if score:
                st.markdown(f"🧠 **Vibe Score:** <span style='color:mediumseagreen;font-weight:bold'>{score}</span>", unsafe_allow_html=True)
            if reasons:
                st.markdown("💬 **Reasoning:**")
                for r in reasons:
                    st.markdown(f"- {r.lstrip('- ').strip()}")
            else:
                st.markdown("*No reasoning available.*")

            # === Pattern ===
            pattern = detect_pattern(df)
            if pattern:
                emoji = "📈" if "Golden" in pattern else "📉"
                st.markdown(f"📊 **AI Signal:** {emoji} {pattern}")
            elif not ta_enabled:
                st.info("📭 Pattern detection unavailable (pandas_ta not installed)")

    except Exception as e:
        st.error(f"⚠️ Failed to load data for {ticker}: {e}")
