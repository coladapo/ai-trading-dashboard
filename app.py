import streamlit as st
import yfinance as yf
from openai import OpenAI
import requests
from datetime import date

# Set up OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Tickers to track
tickers = ["QBTS", "RGTI", "IONQ"]

# Fetch latest news headline from Finnhub
def fetch_headline(ticker):
    try:
        today = date.today().strftime('%Y-%m-%d')
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={st.secrets['FINNHUB_API_KEY']}"
        response = requests.get(url)
        news = response.json()
        if news and isinstance(news, list):
            return news[0]["headline"]
        else:
            return f"No recent news found for {ticker}"
    except Exception as e:
        return f"Error fetching news: {e}"

# Analyze sentiment with OpenAI
def get_vibe_score(headline):
    prompt = f"Rate this headline from 1 (very bearish) to 10 (very bullish): {headline}"
    try:
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return float(res.choices[0].message.content.strip())
    except Exception as e:
        return f"Error: {e}"

# Generate buy/sell signal
def get_signal(vibe):
    try:
        vibe = float(vibe)
        if vibe >= 8:
            return "🔼 BUY Signal"
        elif vibe <= 3:
            return "🔽 SELL Signal"
        else:
            return "⏸ HOLD"
    except:
        return "⚠️ Could not determine signal"

# Streamlit UI
st.title("📊 AI-Powered Day Trading Watchlist")

for ticker in tickers:
    st.subheader(ticker)

    # Fetch and plot stock data
    data = yf.download(ticker, period="1d", interval="5m")
    st.line_chart(data["Close"])

    # Fetch headline and analyze sentiment
    example_headline = fetch_headline(ticker)
    vibe = get_vibe_score(example_headline)
    signal = get_signal(vibe)

    st.write(f"🧠 Vibe Score: **{vibe}** based on: _{example_headline}_")
    st.write(f"📈 Suggested Action: **{signal}**")
    st.markdown("---")
