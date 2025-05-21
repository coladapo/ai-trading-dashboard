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
        interval = "5m" if period in ["1d", "5d"] else "1d"
        data = yf.download(ticker, period=period, interval=interval)
        if data.empty:
            return pd.DataFrame()
        
        # Reset index to make Date a column
        data = data.reset_index()
        
        # Make sure Datetime column exists and is properly formatted
        if 'Date' in data.columns and 'Datetime' not in data.columns:
            data.rename(columns={'Date': 'Datetime'}, inplace=True)
            
        # Calculate SMA
        data['sma'] = data['Close'].rolling(window=10).mean()
        
        return data
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

# === Display ===
st.title("AI Trading Watchlist")
cols = st.columns(len(tickers))

for i, ticker in enumerate(tickers):
    with cols[i]:
        st.subheader(ticker)
        
        df = fetch_price_data(ticker, timeframe)
        
        if not df.empty and len(df) > 1:  # Need at least 2 points to draw a line
            x_col = 'Datetime' if 'Datetime' in df.columns else 'Date' if 'Date' in df.columns else None
            
            if x_col is not None:
                # Create the figure with specific size and margins
                fig = go.Figure()
                
                # Add price line
                fig.add_trace(go.Scatter(
                    x=df[x_col],
                    y=df['Close'],
                    mode='lines',
                    name='Price',
                    line=dict(color='#1f77b4', width=2)
                ))
                
                # Add SMA line
                fig.add_trace(go.Scatter(
                    x=df[x_col],
                    y=df['sma'],
                    mode='lines',
                    name='SMA (10)',
                    line=dict(color='#ff7f0e', width=1.5, dash='dot')
                ))
                
                # Update the layout for better visualization
                fig.update_layout(
                    height=300,
                    margin=dict(l=0, r=0, t=30, b=0),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(
                        showgrid=False,
                        title=None,
                        rangeslider=dict(visible=False)
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(230,230,230,0.3)'
                    ),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom", 
                        y=1.02, 
                        xanchor="right", 
                        x=1
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"Date column not found in data for {ticker}")
        else:
            st.info(f"Insufficient price data found for {ticker}.")
        
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
