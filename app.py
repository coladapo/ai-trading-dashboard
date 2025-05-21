import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta
from openai import OpenAI

# === API Setup ===
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
finnhub_api_key = st.secrets["FINNHUB_API_KEY"]

# === UI ===
st.set_page_config(page_title="AI Trading Watchlist", layout="wide")
st.sidebar.header("📅 Chart Timeframe")
timeframe = st.sidebar.selectbox("Select timeframe", ["1d", "5d", "1mo", "3mo", "6mo", "1y"])
refresh = st.sidebar.button("🔁 Refresh Data")

# === Tickers ===
tickers = ["QBTS", "RGTI", "IONQ"]

# === Fetch Price Data ===
@st.cache_data(ttl=30 if not refresh else 0, show_spinner=False)
def fetch_price_data(ticker, period):
    try:
        interval = "5m" if period == "1d" else "1d"
        df = yf.download(ticker, period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        
        df = df.reset_index()
        df['sma'] = df['Close'].rolling(window=10).mean()
        return df
    except Exception as e:
        st.error(f"Error fetching price data for {ticker}: {str(e)}")
        return pd.DataFrame()

# === Fetch News Headline ===
@st.cache_data(ttl=1800 if not refresh else 0, show_spinner=False)
def fetch_headline(ticker):
    try:
        # Use a 30-day window to increase chances of finding news
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        url = f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from={start_date.strftime('%Y-%m-%d')}&to={end_date.strftime('%Y-%m-%d')}&token={finnhub_api_key}"
        response = requests.get(url)
        
        if response.status_code != 200:
            st.warning(f"API error: {response.status_code} - {response.text}")
            return "No recent news found."
            
        news = response.json()
        if news and isinstance(news, list) and len(news) > 0:
            # Sort by date to get the most recent news
            news.sort(key=lambda x: x.get("datetime", 0), reverse=True)
            return news[0]["headline"]
        return "No recent news found."
    except Exception as e:
        st.error(f"Error fetching news for {ticker}: {str(e)}")
        return "Error fetching news."

# === Vibe Score ===
def get_vibe_score(headline):
    if headline == "No recent news found." or headline == "Error fetching news.":
        return None

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
        output = res.choices[0].message.content.strip()
        return output
    except Exception as e:
        st.error(f"Error getting vibe score: {str(e)}")
        return None

def parse_vibe_response(response):
    if not response:
        return None, []
    
    try:
        lines = response.splitlines()
        score_line = next((line for line in lines if "Score:" in line), None)
        score = int(score_line.split(":")[1].strip()) if score_line else None
        reasons = [line for line in lines if line.strip().startswith("-")]
        return score, reasons
    except Exception as e:
        st.error(f"Error parsing vibe response: {str(e)}")
        return None, []

# === For debugging ===
def debug_api_keys():
    # Check if API keys are available (don't show full keys)
    if "OPENAI_API_KEY" in st.secrets:
        key = st.secrets["OPENAI_API_KEY"]
        masked_key = key[:4] + "*" * (len(key) - 8) + key[-4:] if len(key) > 8 else "****"
        st.sidebar.success(f"OpenAI API Key: {masked_key}")
    else:
        st.sidebar.error("OpenAI API Key not found")
    
    if "FINNHUB_API_KEY" in st.secrets:
        key = st.secrets["FINNHUB_API_KEY"]
        masked_key = key[:4] + "*" * (len(key) - 8) + key[-4:] if len(key) > 8 else "****"
        st.sidebar.success(f"Finnhub API Key: {masked_key}")
    else:
        st.sidebar.error("Finnhub API Key not found")

# Uncomment this line to check API keys (for debugging only)
# debug_api_keys()

# === Display ===
st.title("AI Trading Watchlist")
cols = st.columns(len(tickers))

for i, ticker in enumerate(tickers):
    with cols[i]:
        st.subheader(ticker)
        
        df = fetch_price_data(ticker, timeframe)
        if not df.empty:
            fig = go.Figure()
            
            # Determine the x-axis column
            x_col = None
            if 'Datetime' in df.columns:
                x_col = 'Datetime'
            elif 'Date' in df.columns:
                x_col = 'Date'
            
            if x_col:
                fig.add_trace(go.Scatter(
                    x=df[x_col],
                    y=df['Close'],
                    mode='lines',
                    name='Price'
                ))
                fig.add_trace(go.Scatter(
                    x=df[x_col],
                    y=df['sma'],
                    mode='lines',
                    name='SMA (10)'
                ))
                fig.update_layout(
                    height=300, 
                    margin=dict(l=0, r=0, t=25, b=0),
                    xaxis_title=None,
                    yaxis_title=None,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("Could not determine date column in dataframe")
        else:
            st.info("No price data found.")
            
        headline = fetch_headline(ticker)
        st.write(f"**Latest Headline:** {headline}")
        
        if headline != "No recent news found." and headline != "Error fetching news.":
            vibe_response = get_vibe_score(headline)
            score, reasons = parse_vibe_response(vibe_response)
            
            if score:
                st.metric("Vibe Score", score, delta=None)
                for reason in reasons:
                    st.markdown(reason)
            else:
                st.info("Unable to analyze headline sentiment.")
        else:
            st.info("No news to analyze.")
