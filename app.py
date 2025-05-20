
import streamlit as st
import yfinance as yf
import openai
import os

# Load API keys securely from Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Tickers to track
tickers = ["QBTS", "RGTI", "IONQ"]

def get_vibe_score(headline):
    prompt = f"Rate this headline from 1 (very bearish) to 10 (very bullish): {headline}"
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

st.title("📊 AI-Powered Day Trading Watchlist")

for ticker in tickers:
    st.subheader(ticker)
    data = yf.download(ticker, period="1d", interval="5m")
    st.line_chart(data["Close"])

    example_headline = f"{ticker} just posted strong quantum advancement news"
    vibe = get_vibe_score(example_headline)
    st.write(f"🧠 Vibe Score: **{vibe}** based on: _{example_headline}_")
    st.markdown("---")
