import streamlit as st
import yfinance as yf
from openai import OpenAI
import requests
from datetime import datetime

# Set up OpenAI and Finnhub clients
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# List of tickers
tickers = ["QBTS", "RGTI", "IONQ"]

# Function: Fetch latest news headline from Finnhub
def fetch_headline(ticker):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        news = response.json()
        if news and isinstance(news, list) and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return f"No recent news found for {ticker}"
    except Exception as e:
        return f"Error fetching news: {e}"

# Function: Get vibe score from OpenAI
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

# Function: Translate score to signal
def get_signal(score):
    try:
        vibe = int(score)
        if vibe >= 8:
            return "📈 Buy"
        elif vibe <= 3:
            return "📉 Sell"
        else:
            return "🤖 Hold"
    except:
        return "⚠️ No recommendation"

# Streamlit UI
st.title("📊 AI-Powered Day Trading Watchlist")

for ticker in tickers:
    st.subheader(ticker)

    try:
        data = yf.download(ticker, period="5d", interval="30m")
        st.line_chart(data["Close"])

        headline = fetch_headline(ticker)
        score = get_vibe_score(headline)
        signal = get_signal(score)

        st.markdown(f"📰 **Headline:** *{headline}*")
        st.markdown(f"🧠 **Vibe Score:** {score}")
        st.markdown(f"🤖 **AI Signal:** {signal}")
    except Exception as e:
        st.error(f"Failed to analyze {ticker}: {e}")
