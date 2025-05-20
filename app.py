import streamlit as st
import yfinance as yf
import requests
from openai import OpenAI
from datetime import datetime
import matplotlib.pyplot as plt

# --- API KEYS ---
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# --- Sidebar Controls ---
st.sidebar.title("📅 Chart Settings")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
interval = "5m" if timeframe == "1d" else "1d"

tickers = ["QBTS", "RGTI", "IONQ"]

# --- Fetch headline ---
def fetch_headline(ticker):
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={today}&to={today}&token={finnhub_api_key}"
        res = requests.get(url)
        news = res.json()
        if news and isinstance(news, list) and "headline" in news[0]:
            return news[0]["headline"]
        else:
            return f"No recent news found for {ticker}"
    except Exception as e:
        return f"Error fetching news: {e}"

# --- AI prompt for score + reasoning ---
def get_vibe_score_and_reasoning(headline):
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

# --- App Layout ---
st.title("📊 AI-Powered Day Trading Dashboard")

for ticker in tickers:
    st.subheader(ticker)

    # Fetch and chart price data
    try:
        data = yf.download(ticker, period=timeframe, interval=interval)
        close_prices = data["Close"]

        # --- Color-coded chart ---
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(close_prices.index, close_prices, label="Price", color="blue")

        min_price = close_prices.min()
        max_price = close_prices.max()
        price_range = max_price - min_price
        sell_zone = min_price + 0.33 * price_range
        buy_zone = min_price + 0.66 * price_range

        ax.axhspan(min_price, sell_zone, color='red', alpha=0.1, label='Sell Zone')
        ax.axhspan(sell_zone, buy_zone, color='gray', alpha=0.1, label='Neutral Zone')
        ax.axhspan(buy_zone, max_price, color='green', alpha=0.1, label='Buy Zone')

        ax.set_title(f"{ticker} Price Chart")
        ax.set_ylabel("Price")
        ax.legend(loc="upper left")
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Chart error for {ticker}: {e}")
        continue

    # Fetch and analyze headline
    headline = fetch_headline(ticker)
    st.markdown(f"📰 **Headline:** _{headline}_")

    response = get_vibe_score_and_reasoning(headline)
    if response.startswith("Error"):
        st.warning(response)
        continue

    try:
        lines = response.splitlines()
        score_line = next((line for line in lines if "Score:" in line), None)
        score = int(score_line.split(":")[1].strip()) if score_line else None
        reasoning = "\n".join([line for line in lines if line.startswith("-")])

        st.markdown(f"🧠 **Vibe Score:** `{score}`")
        st.markdown(f"📝 **Reasoning:**\n{reasoning}")

        if score is not None:
            if score >= 8:
                st.markdown("🤖 **AI Signal:** 📈 Buy")
            elif score <= 3:
                st.markdown("🤖 **AI Signal:** 📉 Sell")
            else:
                st.markdown("🤖 **AI Signal:** 🤖 Hold")
        else:
            st.markdown("🤖 **AI Signal:** ⚠️ No recommendation")

    except Exception as e:
        st.error(f"Response parsing error: {e}")
