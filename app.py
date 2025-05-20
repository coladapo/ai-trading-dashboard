import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from openai import OpenAI
from functools import lru_cache
import time

# Setup API clients
openai_client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])
finnhub_api_key = st.secrets['FINNHUB_API_KEY']

# Sidebar
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ['1d', '5d', '1mo', '3mo', '6mo', '1y'])
refresh = st.sidebar.button("🔄 Refresh Data")

# List of tickers
tickers = ["QBTS", "RGTI", "IONQ"]

def fetch_headline(ticker):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        response = requests.get(url)
        news = response.json()
        if news and isinstance(news, list) and 'headline' in news[0]:
            return news[0]['headline']
        else:
            return "No recent news"
    except Exception as e:
        return f"Error fetching headline: {e}"

@st.cache_data(ttl=30 if timeframe == '1d' else 3600, show_spinner=False)
def fetch_price_data(ticker, tf):
    df = yf.download(ticker, period=tf, interval='5m' if tf == '1d' else '1d')
    df.reset_index(inplace=True)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df.dropna(subset=['Date'], inplace=True)
    df.sort_values('Date', inplace=True)
    return df

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
        return f"Error: {e}"

def display_ticker_section(ticker):
    st.subheader(ticker)
    try:
        df = fetch_price_data(ticker, timeframe)
        if df.empty or df['Close'].isnull().all():
            st.warning("⚠️ No price data available.")
            return

        # Plot
        fig, ax = plt.subplots()
        ax.plot(df['Date'], df['Close'], color='dodgerblue', linewidth=2)
        ax.set_title(f"{ticker} Close Price")
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d' if timeframe != '1d' else '%m-%d %H:%M'))
        plt.xticks(rotation=45)
        st.pyplot(fig)

        # Headline + Score
        headline = fetch_headline(ticker)
        st.markdown(f"**📰 Headline:** *{headline}*")

        ai_response = get_vibe_score(headline)
        if ai_response.startswith("Error"):
            st.markdown(f"**💬 Error in AI response:** {ai_response}")
            return

        lines = ai_response.splitlines()
        score_line = next((l for l in lines if "Score:" in l), "Score: -")
        reasons = [l for l in lines if l.startswith("-")]

        score = score_line.split(":")[-1].strip()
        st.markdown(f"**🧠 Vibe Score:** :green[{score}]")
        st.markdown("**💬 Reasoning:**")
        for reason in reasons:
            st.markdown(f"- {reason[1:].strip()}")

        # Recommendation
        try:
            score_num = int(score)
            if score_num >= 8:
                signal = "📈 Buy"
            elif score_num <= 3:
                signal = "📉 Sell"
            else:
                signal = "🤖 Hold"
            st.markdown(f"**📡 AI Signal:** {signal}")
        except:
            st.markdown("**📡 AI Signal:** ⚠️ Unable to determine.")

    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")

# Refresh handling
if refresh:
    st.cache_data.clear()
    st.experimental_rerun()

# Run app
st.title("📊 AI-Powered Day Trading Dashboard")
for ticker in tickers:
    display_ticker_section(ticker)
