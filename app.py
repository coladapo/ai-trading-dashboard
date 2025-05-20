import streamlit as st
import yfinance as yf
from openai import OpenAI
import requests
import datetime

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Finnhub API Key
finnhub_key = st.secrets["FINNHUB_API_KEY"]

# Tickers to track
tickers = ["QBTS", "RGTI", "IONQ"]

# Helper: fetch latest headline from Finnhub
def fetch_headline(ticker):
    today = datetime.date.today().isoformat()
    try:
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_key}"
        res = requests.get(url)
        news = res.json()
        if news and isinstance(news, list):
            return news[0]["headline"]
        else:
            return "No recent news"
    except Exception as e:
        return f"News error: {e}"

# Helper: analyze sentiment using OpenAI
def get_vibe_score(headline):
    prompt = f"Rate this headline from 1 (very bearish) to 10 (very bullish): {headline}"
    try:
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return int(res.choices[0].message.content.strip())
    except Exception as e:
        return f"Error: {e}"

# Helper: classify recommendation
def classify_signal(vibe, volume_ratio):
    if isinstance(vibe, int):
        if vibe >= 8 and volume_ratio > 1.2:
            return "📈 Buy"
        elif vibe <= 3 and volume_ratio > 1.2:
            return "📉 Sell"
        else:
            return "⚠️ No recommendation"
    else:
        return "⚠️ No recommendation"

# App UI
st.title("📊 AI-Powered Day Trading Watchlist")

for ticker in tickers:
    st.subheader(ticker)

    # Price chart
    data = yf.download(ticker, period="5d", interval="30m")
    st.line_chart(data["Close"])

    # Volume analysis
    avg_volume = data["Volume"].mean()
    latest_volume = data["Volume"].iloc[-1]
    volume_ratio = latest_volume / avg_volume if avg_volume else 0

    # Headline + sentiment
    headline = fetch_headline(ticker)
    vibe = get_vibe_score(headline)
    signal = classify_signal(vibe, volume_ratio)

    # Display results
    st.write(f"📄 **Headline:** *{headline}*")
    st.write(f"🧠 **Vibe Score:** {vibe}")
    st.write(f"🧭 **AI Signal:** {signal}")
    st.markdown("---")
