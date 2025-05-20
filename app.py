import streamlit as st
import yfinance as yf
from openai import OpenAI
import os

# Set up OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Tickers to track
tickers = ["QBTS", "RGTI", "IONQ"]

# Function to analyze headline sentiment
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
    data = yf.download(ticker, period="1d", interval="5m")
    st.line_chart(data["Close"])

    # Example headline + AI sentiment
    example_headline = f"{ticker} just posted strong quantum advancement news"
    vibe = get_vibe_score(example_headline)
    st.write(f"🧠 Vibe Score: **{vibe}** based on: _{example_headline}_")
    st.markdown("---")
