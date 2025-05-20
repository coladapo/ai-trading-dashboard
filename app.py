import streamlit as st
import yfinance as yf
import requests
from openai import OpenAI

# Set up OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Tickers to track
tickers = ["QBTS", "RGTI", "IONQ"]

# Function to fetch the latest headline from Finnhub
def fetch_headline(ticker):
    try:
        from datetime import date
        today = date.today().isoformat()
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={st.secrets['FINNHUB_API_KEY']}"
        response = requests.get(url)
        news = response.json()
        if news and isinstance(news, list) and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return f"No recent news found for {ticker}"
    except Exception as e:
        return f"Error fetching news: {e}"

# Function to analyze sentiment using OpenAI
def get_vibe_score(headline):
    prompt = f"Rate this headline from 1 (very bearish) to 10 (very bullish): {headline}"
    try:
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

# Streamlit UI
st.title("📊 AI-Powered Day Trading Watchlist")

for ticker in tickers:
    st.subheader(ticker)

    # Fetch recent intraday data
    data = yf.download(ticker, period="5d", interval="5m")
    st.line_chart(data["Close"])

    # Volume signal
    avg_volume = round(data["Volume"].mean(), 2)
    latest_volume = round(data["Volume"].iloc[-1], 2)
    volume_alert = latest_volume > avg_volume * 1.5

    # Show volume data
    st.write(f"🔊 Volume: {latest_volume} (avg: {avg_volume})")

    # Headline + Sentiment
    headline = fetch_headline(ticker)
    st.write(f"📰 Headline: _{headline}_")
    vibe = get_vibe_score(headline)
    st.write(f"🧠 Vibe Score: {vibe}")

    # AI Signal Logic
    try:
        vibe_score = int(vibe)
        if vibe_score >= 8 and volume_alert:
            recommendation = "📈 Strong Buy (volume spike)"
        elif vibe_score >= 8:
            recommendation = "📈 Buy"
        elif vibe_score <= 3:
            recommendation = "📉 Sell"
        else:
            recommendation = "🤖 Hold"
    except:
        recommendation = "⚠️ No recommendation"

    st.write(f"🤖 AI Signal: {recommendation}")
    st.markdown("---")
