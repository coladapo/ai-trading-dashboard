import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta
import requests
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
# Ensure sklearn is available if you plan to use more advanced clustering or ML,
# though cluster_price_levels is custom and doesn't directly use sklearn.
# from sklearn.cluster import AgglomerativeClustering # Example if you were to use it

# --- Global Configurations & Initializations ---

# NewsAPI Key Placeholder
NEWS_API_KEY = "YOUR_API_KEY" # <<< IMPORTANT: Replace with your actual NewsAPI key

# Initialize NLTK components
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

# --- 1. Data Pipeline ---
@st.cache_data(ttl=300)  # Cache stock data for 5 minutes
def get_stock_data(ticker, period="1y", interval="1d"):
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period, interval=interval)
    return hist

@st.cache_data(ttl=1800) # Cache news data for 30 minutes
def get_news_data(ticker, days_back=7, api_key=NEWS_API_KEY):
    if api_key == "YOUR_API_KEY":
        return {"error": "NewsAPI key not configured."}
    
    today = datetime.now()
    days_ago_date = today - timedelta(days=days_back)
    
    url = (f"https://newsapi.org/v2/everything?q={ticker}"
           f"&from={days_ago_date.strftime('%Y-%m-%d')}"
           f"&to={today.strftime('%Y-%m-%d')}"
           f"&sortBy=popularity&apiKey={api_key}")
    
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch news: {e}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred while fetching news: {e}"}

# --- 2. Technical Analysis Engine ---
def add_technical_indicators(df):
    df = df.copy()
    # SMA
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean() # Added SMA_20 for Bollinger Bands
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Histogram'] = df['MACD'] - df['Signal_Line']
    
    # Bollinger Bands
    df['BB_Middle'] = df['SMA_20'] # Often SMA_20 is used as the middle band
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * 2)
    df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * 2)
    
    return df

def cluster_price_levels(price_levels, threshold_pct=0.01):
    if not price_levels:
        return []
    
    price_levels = sorted(list(set(price_levels))) # Ensure unique and sorted
    if not price_levels: # Check again after set conversion if original was all duplicates
        return []
        
    clustered = []
    current_cluster = [price_levels[0]]
    
    for i in range(1, len(price_levels)):
        if (price_levels[i] - current_cluster[0]) / current_cluster[0] <= threshold_pct:
            current_cluster.append(price_levels[i])
        else:
            clustered.append(sum(current_cluster) / len(current_cluster))
            current_cluster = [price_levels[i]]
    
    if current_cluster: # Append the last cluster
        clustered.append(sum(current_cluster) / len(current_cluster))
    
    return clustered

def detect_support_resistance(df, window=10):
    df = df.copy()
    df['Local_Min_Check'] = df['Low'].rolling(window=window, center=True).min()
    df['Local_Max_Check'] = df['High'].rolling(window=window, center=True).max()

    df['Local_Min'] = df['Low'] == df['Local_Min_Check']
    df['Local_Max'] = df['High'] == df['Local_Max_Check']
    
    support_levels = df[df['Local_Min']]['Low'].tolist()
    resistance_levels = df[df['Local_Max']]['High'].tolist()
    
    support_levels = cluster_price_levels(support_levels)
    resistance_levels = cluster_price_levels(resistance_levels)
    
    return support_levels, resistance_levels

# --- 3. Signal Generation System ---
def generate_signals(df):
    signals = pd.DataFrame(index=df.index)
    signals['Price'] = df['Close']
    signals['Signal'] = 0  # 0 = no signal, 1 = buy, -1 = sell (legacy, composite is better)
    
    # SMA Crossover (Golden Cross / Death Cross)
    # Ensure SMA_50 and SMA_200 are present
    if 'SMA_50' in df.columns and 'SMA_200' in df.columns:
        signals.loc[(df['SMA_50'] > df['SMA_200']) & (df['SMA_50'].shift(1) <= df['SMA_200'].shift(1)), 'Signal'] = 1
        signals.loc[(df['SMA_50'] < df['SMA_200']) & (df['SMA_50'].shift(1) >= df['SMA_200'].shift(1)), 'Signal'] = -1
    
    # RSI Overbought/Oversold
    if 'RSI' in df.columns:
        signals.loc[df['RSI'] < 30, 'RSI_Signal'] = 1  # Oversold - Buy
        signals.loc[df['RSI'] > 70, 'RSI_Signal'] = -1  # Overbought - Sell
    
    # MACD Crossover
    if 'MACD' in df.columns and 'Signal_Line' in df.columns:
        signals.loc[(df['MACD'] > df['Signal_Line']) & (df['MACD'].shift(1) <= df['Signal_Line'].shift(1)), 'MACD_Signal'] = 1
        signals.loc[(df['MACD'] < df['Signal_Line']) & (df['MACD'].shift(1) >= df['Signal_Line'].shift(1)), 'MACD_Signal'] = -1
    
    # Bollinger Band Strategies
    if 'Close' in df.columns and 'BB_Lower' in df.columns and 'BB_Upper' in df.columns:
        signals.loc[df['Close'] < df['BB_Lower'], 'BB_Signal'] = 1
        signals.loc[df['Close'] > df['BB_Upper'], 'BB_Signal'] = -1
    
    # Composite Signal
    signal_cols = ['RSI_Signal', 'MACD_Signal', 'BB_Signal']
    for col in signal_cols:
        if col not in signals.columns: # If a source signal wasn't generated (e.g. missing RSI data)
            signals[col] = 0
        signals[col] = signals[col].fillna(0)
    
    signals['Composite_Signal_Sum'] = signals[signal_cols].sum(axis=1)
    signals['Composite_Signal_Count'] = signals[signal_cols].apply(lambda x: (x != 0).sum(), axis=1) # Count non-zero signals
    
    # Avoid division by zero if no signals are present for a row
    signals['Composite_Signal'] = signals.apply(
        lambda row: row['Composite_Signal_Sum'] / row['Composite_Signal_Count'] if row['Composite_Signal_Count'] > 0 else 0,
        axis=1
    )
    
    return signals

def backtest_strategy(signals_df, initial_capital=100000.0):
    # Ensure signals_df is not a view and can be modified
    signals = signals_df.copy()

    positions = pd.DataFrame(index=signals.index).fillna(0.0)
    # Determine trades: 1 for buy, -1 for sell action, 0 for hold
    positions['Trade'] = 0
    positions.loc[signals['Composite_Signal'] >= 0.5, 'Trade'] = 1  # Buy signal
    positions.loc[signals['Composite_Signal'] <= -0.5, 'Trade'] = -1 # Sell signal

    # Convert trade signals to actual positions (1 for long, 0 for flat)
    # Assumption: We are either long or flat. We don't hold short positions in this simple model.
    # A buy signal means enter long. A sell signal means exit long position.
    current_position = 0
    position_series = []
    for i in range(len(positions)):
        trade = positions['Trade'].iloc[i]
        if current_position == 0 and trade == 1: # Buy to enter
            current_position = 1
        elif current_position == 1 and trade == -1: # Sell to exit
            current_position = 0
        position_series.append(current_position)
    positions['Position'] = position_series
    
    # Calculate portfolio
    portfolio = pd.DataFrame(index=signals.index)
    portfolio['Holdings_Value'] = positions['Position'] * signals['Price'] # Value of stock held
    portfolio['Position_Change'] = positions['Position'].diff().fillna(positions['Position'].iloc[0] if not positions.empty else 0)

    # Calculate cash changes
    # When Position_Change is 1 (buy): cash decreases by Price
    # When Position_Change is -1 (sell): cash increases by Price
    portfolio['Cash_Change'] = -portfolio['Position_Change'] * signals['Price']
    portfolio['Cash'] = initial_capital + portfolio['Cash_Change'].cumsum()
    
    portfolio['Total'] = portfolio['Cash'] + portfolio['Holdings_Value']
    portfolio['Returns'] = portfolio['Total'].pct_change().fillna(0.0)
    
    # Performance metrics
    if portfolio['Returns'].std() == 0: # Avoid division by zero if no volatility
        sharpe_ratio = 0.0
    else:
        sharpe_ratio = portfolio['Returns'].mean() / portfolio['Returns'].std() * np.sqrt(252) # Annualized
    
    cumulative_max = portfolio['Total'].cummax()
    drawdown = (portfolio['Total'] - cumulative_max) / cumulative_max
    max_drawdown = drawdown.min()
    
    return portfolio, sharpe_ratio, max_drawdown

# --- 4. Risk Management System ---
def calculate_position_size(account_size, risk_per_trade_pct, entry_price, stop_price):
    if entry_price == stop_price or entry_price == 0 or stop_price == 0 : # Avoid division by zero or nonsensical calculation
        return 0
    
    risk_amount = account_size * (risk_per_trade_pct / 100.0)
    risk_per_share = abs(entry_price - stop_price)
    if risk_per_share == 0: # Avoid division by zero
        return 0
    position_size = risk_amount / risk_per_share
    
    return position_size

def calculate_kelly_criterion(win_rate, win_loss_ratio):
    if win_loss_ratio == 0: # Avoid division by zero
        return 0
    kelly_pct = win_rate - ((1 - win_rate) / win_loss_ratio)
    return min(kelly_pct, 0.2) # Cap Kelly at 20%

@st.cache_data(ttl=300) # Cache ATR calculation briefly
def calculate_atr_stop_loss(df_input, atr_periods=14, atr_multiplier=2):
    df = df_input.copy() # Ensure we're working with a copy
    # Calculate True Range (TR)
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    
    df['ATR'] = df['TR'].rolling(window=atr_periods, min_periods=1).mean() # Use min_periods=1 to get values earlier
    
    df['Long_Stop'] = df['Close'] - (df['ATR'] * atr_multiplier)
    df['Short_Stop'] = df['Close'] + (df['ATR'] * atr_multiplier)
    
    return df

# --- 5. News Sentiment Analysis ---
@st.cache_data(ttl=1800) # Cache sentiment analysis results
def analyze_news_sentiment(news_items_json):
    analyzer = SentimentIntensityAnalyzer()
    
    if "error" in news_items_json or 'articles' not in news_items_json or not news_items_json['articles']:
        return 0  # Neutral if no news or error
    
    sentiments = []
    for article in news_items_json['articles']:
        if article and 'title' in article and article['title'] and 'description' in article and article['description']:
            text = article['title'] + ' ' + article['description']
            sentiment_score = analyzer.polarity_scores(text)
            sentiments.append(sentiment_score['compound']) # Compound score is a good summary
    
    if not sentiments:
        return 0 # Neutral if no valid articles processed
    
    avg_sentiment = sum(sentiments) / len(sentiments)
    # Scale -1 to 1 into 1 to 5
    # scaled_sentiment = ((avg_sentiment + 1) / 2) * 4 + 1 
    # Let's return the raw average compound score first, scaling can be done in UI if needed
    return round(avg_sentiment, 3)


@st.cache_data(ttl=1800) # Cache for 30 minutes
def get_news_for_date(ticker, date_str, api_key=NEWS_API_KEY):
    """Fetches news for a specific ticker on a specific date."""
    if api_key == "YOUR_API_KEY":
        return {"error": "NewsAPI key not configured."}
    
    # NewsAPI requires date in YYYY-MM-DD format
    url = (f"https://newsapi.org/v2/everything?q={ticker}"
           f"&from={date_str}&to={date_str}"
           f"&sortBy=popularity&apiKey={api_key}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error fetching news for {ticker} on {date_str}: {e}")
        return {"error": f"Failed to fetch news for date: {e}"}
    except Exception as e:
        st.error(f"Unexpected error fetching news for {ticker} on {date_str}: {e}")
        return {"error": f"An unexpected error occurred: {e}"}


@st.cache_data(ttl=3600) # Cache for 1 hour
def correlate_news_price(ticker, period="3mo", api_key=NEWS_API_KEY):
    stock_data = get_stock_data(ticker, period=period)
    if stock_data.empty:
        return None, pd.DataFrame() # Return None for correlation if no stock data

    sentiment_data = []
    dates = stock_data.index
    
    # Ensure dates are timezone-naive if they are timezone-aware from yfinance
    if dates.tz is not None:
        dates = dates.tz_localize(None)

    for date_obj in dates:
        date_str = date_obj.strftime('%Y-%m-%d')
        news = get_news_for_date(ticker, date_str, api_key=api_key)
        sentiment = analyze_news_sentiment(news) # analyze_news_sentiment returns a single score
        sentiment_data.append({'date': date_obj, 'sentiment': sentiment}) # Use date_obj for proper join
    
    if not sentiment_data:
        return None, stock_data # Return stock_data even if no sentiment

    sentiment_df = pd.DataFrame(sentiment_data).set_index('date')
    
    combined_df = stock_data.join(sentiment_df)
    combined_df['sentiment'] = combined_df['sentiment'].fillna(0) # Fill missing sentiment with neutral
    
    combined_df['Next_Day_Return'] = combined_df['Close'].pct_change().shift(-1) # pct_change(1) is more explicit
    
    if 'sentiment' in combined_df.columns and 'Next_Day_Return' in combined_df.columns and not combined_df[['sentiment', 'Next_Day_Return']].isnull().all().all():
        correlation = combined_df['sentiment'].corr(combined_df['Next_Day_Return'])
    else:
        correlation = None
        
    return correlation, combined_df


# --- Streamlit UI Implementation ---
st.set_page_config(
    page_title="AI Trading Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 AI-Enhanced Trading Platform")

# Sidebar controls
st.sidebar.title("⚙️ Controls")
timeframe = st.sidebar.selectbox(
    "Select Chart Timeframe",
    options=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
    index=5 # Default to 1y
)

# Add refresh button
if st.sidebar.button("🔄 Refresh All Data"):
    st.cache_data.clear()
    st.success("Data cache cleared. Reloading...")
    # st.experimental_rerun() # Use st.rerun() in newer Streamlit versions

# Stock tickers for dashboard - allow user input
default_tickers = "QBTS,RGTI,IONQ,CRVW,DBX,TSM"
user_tickers = st.sidebar.text_input("Enter Stock Tickers (comma-separated)", default_tickers)
tickers = [ticker.strip().upper() for ticker in user_tickers.split(',') if ticker.strip()]


# --- Main Dashboard Display Function ---
def create_stock_chart_display(ticker, container, tf):
    data = get_stock_data(ticker, period=tf, interval="1d") # Use selected timeframe
    
    if data.empty:
        container.warning(f"Could not retrieve data for {ticker}.")
        return

    # Add SMA_10 for basic chart
    data = add_technical_indicators(data) # Get SMA_10 and others if needed
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data.index, y=data['Close'], mode='lines', name='Price', line=dict(color='#3366CC')
    ))
    if 'SMA_10' in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index, y=data['SMA_10'], mode='lines', name='SMA (10)', line=dict(color='#FF9900')
        ))
    
    fig.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=40, b=10), # Adjusted top margin for title
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_rangeslider_visible=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    )
    
    # News and Sentiment for main dashboard item
    news_data = get_news_data(ticker, days_back=3) # Get recent news
    vibe_score = analyze_news_sentiment(news_data)
    
    headline_text = "No recent headlines."
    if "articles" in news_data and news_data["articles"]:
        headline_text = news_data["articles"][0].get("title", "Headline not available.")
    elif "error" in news_data:
        headline_text = f"⚠️ {news_data['error']}"


    with container:
        st.subheader(f"{ticker}")
        st.plotly_chart(fig, use_container_width=True)
        
        # Sentiment and News in columns for better layout
        col_sent, col_news_link = st.columns([1,3])
        with col_sent:
            # Display vibe_score with color based on value
            if vibe_score > 0.2:
                vibe_color = "green"
                vibe_emoji = "😊"
            elif vibe_score < -0.2:
                vibe_color = "red"
                vibe_emoji = "😟"
            else:
                vibe_color = "gray"
                vibe_emoji = "😐"
            st.markdown(f"**Vibe Score:** <span style='color:{vibe_color};'>{vibe_score:.2f} {vibe_emoji}</span>", unsafe_allow_html=True)

        with col_news_link:
            st.caption(f"📰 {headline_text}")
            if "articles" in news_data and news_data["articles"] and "url" in news_data["articles"][0]:
                 st.markdown(f"[Read more]({news_data['articles'][0]['url']})", unsafe_allow_html=True)


# --- Main Dashboard Layout ---
if tickers:
    st.header("🚀 Main Dashboard")
    num_columns = min(len(tickers), 3) # Max 3 columns
    cols = st.columns(num_columns)
    for i, ticker in enumerate(tickers):
        create_stock_chart_display(ticker, cols[i % num_columns], timeframe)
else:
    st.info("Please enter some stock tickers in the sidebar to display data.")

st.markdown("---") # Separator

# --- Enhanced Features ---

# 1. Advanced Technical Analysis
if st.sidebar.checkbox("🔬 Show Advanced Technical Analysis", value=False):
    st.header("🔬 Advanced Technical Analysis")
    if not tickers:
        st.warning("Please enter tickers in the sidebar to use this feature.")
    else:
        analysis_ticker = st.selectbox("Select Ticker for Detailed Analysis", tickers, key="adv_analysis_ticker")
        if analysis_ticker:
            data_adv = get_stock_data(analysis_ticker, period="1y", interval="1d") # Use 1y for better TA context
            if not data_adv.empty:
                data_adv = add_technical_indicators(data_adv)
                
                tab_price, tab_osc, tab_patterns = st.tabs(["📈 Price & Moving Averages", "📊 Oscillators", "📉 Patterns & Levels"])
                
                with tab_price:
                    st.subheader(f"Price, MAs & Bollinger Bands for {analysis_ticker}")
                    fig_price = go.Figure()
                    fig_price.add_trace(go.Candlestick(
                        x=data_adv.index, open=data_adv['Open'], high=data_adv['High'],
                        low=data_adv['Low'], close=data_adv['Close'], name='Candlestick'
                    ))
                    for sma_period in [20, 50, 200]:
                        if f'SMA_{sma_period}' in data_adv.columns:
                            fig_price.add_trace(go.Scatter(
                                x=data_adv.index, y=data_adv[f'SMA_{sma_period}'], 
                                name=f'SMA {sma_period}', line=dict(width=1.5)
                            ))
                    if 'BB_Upper' in data_adv.columns and 'BB_Lower' in data_adv.columns:
                        fig_price.add_trace(go.Scatter(
                            x=data_adv.index, y=data_adv['BB_Upper'], name='Upper BB', 
                            line=dict(width=1, dash='dash', color='rgba(152,251,152,0.7)'))) # Light green
                        fig_price.add_trace(go.Scatter(
                            x=data_adv.index, y=data_adv['BB_Lower'], name='Lower BB', 
                            line=dict(width=1, dash='dash', color='rgba(255,182,193,0.7)'), # Light red
                            fill='tonexty', fillcolor='rgba(127,127,127,0.1)'))
                    fig_price.update_layout(height=500, xaxis_rangeslider_visible=False, title_text="Price and Key Moving Averages")
                    st.plotly_chart(fig_price, use_container_width=True)

                with tab_osc:
                    st.subheader(f"Oscillators for {analysis_ticker}")
                    if 'RSI' in data_adv.columns:
                        fig_rsi = go.Figure()
                        fig_rsi.add_trace(go.Scatter(x=data_adv.index, y=data_adv['RSI'], name='RSI'))
                        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)", annotation_position="bottom right")
                        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)", annotation_position="bottom right")
                        fig_rsi.update_layout(title_text="Relative Strength Index (RSI)", height=300)
                        st.plotly_chart(fig_rsi, use_container_width=True)
                    
                    if 'MACD' in data_adv.columns and 'Signal_Line' in data_adv.columns and 'MACD_Histogram' in data_adv.columns:
                        fig_macd = go.Figure()
                        fig_macd.add_trace(go.Scatter(x=data_adv.index, y=data_adv['MACD'], name='MACD', line_color='blue'))
                        fig_macd.add_trace(go.Scatter(x=data_adv.index, y=data_adv['Signal_Line'], name='Signal Line', line_color='orange'))
                        fig_macd.add_trace(go.Bar(x=data_adv.index, y=data_adv['MACD_Histogram'], name='Histogram', marker_color='grey'))
                        fig_macd.update_layout(title_text="MACD", height=300)
                        st.plotly_chart(fig_macd, use_container_width=True)
                
                with tab_patterns:
                    st.subheader(f"Support & Resistance for {analysis_ticker}")
                    support, resistance = detect_support_resistance(data_adv, window=15) # window can be adjusted
                    if support:
                        st.write("Support Levels (recent):", ", ".join([f"${s_level:.2f}" for s_level in sorted(list(set(support)), reverse=True)[:5]]))
                    else:
                        st.write("No significant support levels detected with current settings.")
                    if resistance:
                        st.write("Resistance Levels (recent):", ", ".join([f"${r_level:.2f}" for r_level in sorted(list(set(resistance)))[:5]]))
                    else:
                        st.write("No significant resistance levels detected with current settings.")
                    
                    # Visualization of S/R on price chart
                    fig_sr = go.Figure()
                    fig_sr.add_trace(go.Candlestick(
                        x=data_adv.index, open=data_adv['Open'], high=data_adv['High'],
                        low=data_adv['Low'], close=data_adv['Close'], name='Price'
                    ))
                    for s_level in sorted(list(set(support)), reverse=True)[:3]: # Show top 3 S
                        fig_sr.add_hline(y=s_level, line_dash="dash", line_color="green", annotation_text=f"Support ${s_level:.2f}")
                    for r_level in sorted(list(set(resistance)))[:3]: # Show top 3 R
                        fig_sr.add_hline(y=r_level, line_dash="dash", line_color="red", annotation_text=f"Resistance ${r_level:.2f}")
                    fig_sr.update_layout(height=500, xaxis_rangeslider_visible=False, title_text="Price with Detected Support/Resistance")
                    st.plotly_chart(fig_sr, use_container_width=True)
            else:
                st.error(f"Could not fetch data for {analysis_ticker} to perform advanced analysis.")

# 2. Signal Generator & Trading Strategy
if st.sidebar.checkbox("🚦 Show Trading Signals & Backtest", value=False):
    st.header("🚦 Trading Signals & Backtest")
    if not tickers:
        st.warning("Please enter tickers in the sidebar to use this feature.")
    else:
        strategy_ticker = st.selectbox("Select Ticker for Signals & Backtest", tickers, key="signals_ticker_select")
        if strategy_ticker:
            data_strat = get_stock_data(strategy_ticker, period="2y", interval="1d") # Longer period for backtest
            if not data_strat.empty:
                data_strat_ta = add_technical_indicators(data_strat.copy())
                signals_df = generate_signals(data_strat_ta)
                
                st.subheader(f"Recent Trading Signals for {strategy_ticker}")
                recent_signals = signals_df.tail(15).copy() # Show more recent signals
                
                def get_signal_text(composite_signal_val):
                    if composite_signal_val >= 0.6: return "🟢 Strong Buy"
                    if composite_signal_val >= 0.3: return "🟡 Buy"
                    if composite_signal_val <= -0.6: return "🔴 Strong Sell"
                    if composite_signal_val <= -0.3: return "🟠 Sell"
                    return "⚪ Neutral"
                
                recent_signals['Signal Interpretation'] = recent_signals['Composite_Signal'].apply(get_signal_text)
                st.dataframe(recent_signals[['Price', 'Composite_Signal', 'Signal Interpretation']].rename(
                    columns={'Price': 'Close Price', 'Composite_Signal': 'Score'}))

                # Visualize signals on chart
                fig_sig = go.Figure()
                fig_sig.add_trace(go.Candlestick(
                    x=data_strat_ta.index, open=data_strat_ta['Open'], high=data_strat_ta['High'],
                    low=data_strat_ta['Low'], close=data_strat_ta['Close'], name='Price'
                ))
                
                buy_markers = signals_df[signals_df['Composite_Signal'] >= 0.5] # Threshold from backtest logic
                sell_markers = signals_df[signals_df['Composite_Signal'] <= -0.5]

                if not buy_markers.empty:
                    fig_sig.add_trace(go.Scatter(
                        x=buy_markers.index, y=data_strat_ta.loc[buy_markers.index]['Low'] * 0.98, # Place below low
                        mode='markers', marker=dict(symbol='triangle-up', size=12, color='rgba(0,255,0,0.8)'), name='Buy Signal'
                    ))
                if not sell_markers.empty:
                    fig_sig.add_trace(go.Scatter(
                        x=sell_markers.index, y=data_strat_ta.loc[sell_markers.index]['High'] * 1.02, # Place above high
                        mode='markers', marker=dict(symbol='triangle-down', size=12, color='rgba(255,0,0,0.8)'), name='Sell Signal'
                    ))
                fig_sig.update_layout(height=500, xaxis_rangeslider_visible=False, title_text=f"Price Chart with Buy/Sell Signals for {strategy_ticker}")
                st.plotly_chart(fig_sig, use_container_width=True)
                
                st.subheader(f"Backtest Performance for {strategy_ticker} (Composite Strategy)")
                initial_cap = st.number_input("Initial Capital for Backtest:", value=100000.0, min_value=1000.0, step=1000.0)
                portfolio_bt, sharpe_bt, max_dd_bt = backtest_strategy(signals_df, initial_capital=initial_cap)
                
                if portfolio_bt.empty:
                    st.warning("Backtest could not be completed. Not enough data or no trades.")
                else:
                    # Show key metrics
                    final_value = portfolio_bt['Total'].iloc[-1]
                    total_return_pct = ((final_value / initial_cap) - 1) * 100
                    
                    bt_col1, bt_col2, bt_col3, bt_col4 = st.columns(4)
                    bt_col1.metric("Final Portfolio Value", f"${final_value:,.2f}")
                    bt_col2.metric("Total Return", f"{total_return_pct:.2f}%")
                    bt_col3.metric("Annualized Sharpe Ratio", f"{sharpe_bt:.2f}")
                    bt_col4.metric("Max Drawdown", f"{max_dd_bt*100:.2f}%")
                    
                    # Show equity curve
                    fig_equity = go.Figure()
                    fig_equity.add_trace(go.Scatter(x=portfolio_bt.index, y=portfolio_bt['Total'], name='Portfolio Value', line_color='cyan'))
                    fig_equity.update_layout(title_text="Backtest Equity Curve", height=400)
                    st.plotly_chart(fig_equity, use_container_width=True)
            else:
                st.error(f"Could not fetch data for {strategy_ticker} to run strategy.")

# 3. Risk Management Dashboard
if st.sidebar.checkbox("🛡️ Show Risk Management Tools", value=False):
    st.header("🛡️ Risk Management Calculator")
    
    rm_col1, rm_col2 = st.columns([1,1]) # Equal width columns
    
    with rm_col1:
        st.subheader("Position Sizing (ATR Stop)")
        account_size_rm = st.number_input("Your Account Size ($)", value=100000.0, step=1000.0, min_value=0.0, key="rm_acc_size")
        risk_pct_rm = st.slider("Max Risk Per Trade (%)", min_value=0.1, max_value=5.0, value=1.0, step=0.1, key="rm_risk_pct")
        
        if not tickers:
            st.info("Enter tickers in the sidebar to calculate position sizes.")
        else:
            for i, ticker_rm in enumerate(tickers):
                st.markdown(f"--- \n**{ticker_rm}**")
                data_rm = get_stock_data(ticker_rm, period="30d", interval="1d") # Shorter period for current price & ATR
                if not data_rm.empty:
                    current_price_rm = data_rm['Close'].iloc[-1]
                    data_rm_atr = calculate_atr_stop_loss(data_rm.copy()) # Pass a copy
                    
                    if not data_rm_atr.empty and 'Long_Stop' in data_rm_atr.columns and not data_rm_atr['Long_Stop'].empty:
                        stop_price_rm = data_rm_atr['Long_Stop'].iloc[-1]
                        if pd.isna(stop_price_rm): # Handle NaN stop loss if ATR is NaN
                            st.warning(f"ATR Stop Loss for {ticker_rm} could not be calculated (likely insufficient data).")
                            position_size_rm = 0
                            dollar_amount_rm = 0
                        else:
                            position_size_rm = calculate_position_size(account_size_rm, risk_pct_rm, current_price_rm, stop_price_rm)
                            dollar_amount_rm = position_size_rm * current_price_rm
                        
                        st.metric(label=f"Calculated Shares for {ticker_rm}", value=f"{int(position_size_rm)} shares")
                        st.markdown(f"Position Value: **${dollar_amount_rm:,.2f}**")
                        st.markdown(f"Entry: ${current_price_rm:.2f} | ATR Stop: ${stop_price_rm:.2f} | Risk Amount: **${account_size_rm * risk_pct_rm/100.0:,.2f}**")
                    else:
                        st.warning(f"Could not calculate ATR stop loss for {ticker_rm}.")
                else:
                    st.error(f"Could not retrieve data for {ticker_rm} for risk calculation.")
    
    with rm_col2:
        st.subheader("Kelly Criterion (Example)")
        win_rate_kelly = st.slider("Estimated Win Rate (0.0-1.0)", 0.0, 1.0, 0.55, 0.01, key="kelly_wr")
        win_loss_ratio_kelly = st.number_input("Estimated Win/Loss Ratio (e.g., 1.5 for avg win = 1.5 * avg loss)", 0.1, 10.0, 1.5, 0.1, key="kelly_wlr")
        kelly_fraction = calculate_kelly_criterion(win_rate_kelly, win_loss_ratio_kelly)
        st.metric("Kelly Criterion Optimal Fraction (capped at 20%)", f"{kelly_fraction*100:.1f}% of Capital")
        st.caption("Note: Kelly Criterion can be aggressive. Use with caution and consider fractional Kelly.")

        st.subheader("Portfolio Exposure (Placeholder)")
        if tickers:
            # Placeholder for portfolio allocation - assumes equal weight for now
            num_t = len(tickers)
            values = [100.0/num_t for _ in tickers] if num_t > 0 else []
            fig_pie = go.Figure(data=[go.Pie(labels=tickers, values=values, hole=.3, textinfo='percent+label')])
            fig_pie.update_layout(height=300, title_text="Example Portfolio Allocation")
            st.plotly_chart(fig_pie, use_container_width=True)
            
            total_risk_exposure = risk_pct_rm * num_t # Simplistic if all positions taken with max risk
            st.warning(f"Max potential portfolio risk if all entered: {total_risk_exposure:.1f}% (based on selected Risk Per Trade & {num_t} tickers)")
        else:
            st.info("Enter tickers to see example portfolio allocation.")

# 4. News Impact Analysis (Optional Feature)
if st.sidebar.checkbox("📰 Show News Sentiment Correlation", value=False):
    st.header("📰 News Sentiment vs. Price Correlation")
    if not tickers:
        st.warning("Please enter tickers in the sidebar to use this feature.")
    else:
        corr_ticker = st.selectbox("Select Ticker for News Correlation Analysis", tickers, key="corr_ticker_select")
        if corr_ticker:
            st.info(f"Fetching news and calculating correlation for {corr_ticker}. This may take a moment...")
            correlation, combined_df = correlate_news_price(corr_ticker, period="3mo") # 3 months of data
            
            if correlation is not None:
                st.metric(f"Sentiment / Next Day Return Correlation for {corr_ticker} (past 3mo)", f"{correlation:.3f}")
                
                if not combined_df.empty and 'sentiment' in combined_df.columns and 'Next_Day_Return' in combined_df.columns:
                    fig_corr = go.Figure()
                    # Sentiment (on primary y-axis)
                    fig_corr.add_trace(go.Scatter(x=combined_df.index, y=combined_df['sentiment'], name='Sentiment Score',
                                                  line=dict(color='orange')))
                    # Price (on secondary y-axis)
                    fig_corr.add_trace(go.Scatter(x=combined_df.index, y=combined_df['Close'], name='Close Price',
                                                  yaxis='y2', line=dict(color='lightblue')))

                    fig_corr.update_layout(
                        title_text=f"Sentiment Score and Price for {corr_ticker}",
                        height=450,
                        yaxis=dict(title='Sentiment Score'),
                        yaxis2=dict(title='Close Price', overlaying='y', side='right'),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_corr, use_container_width=True)
                    
                    # Allow download of combined data
                    csv = combined_df.to_csv().encode('utf-8')
                    st.download_button(
                        label="Download Correlation Data as CSV",
                        data=csv,
                        file_name=f'{corr_ticker}_sentiment_price_corr.csv',
                        mime='text/csv',
                    )
                else:
                    st.warning(f"Not enough data to plot correlation details for {corr_ticker}.")
            else:
                st.error(f"Could not calculate news sentiment correlation for {corr_ticker}.")


# --- Footer & Disclaimer ---
st.sidebar.markdown("---")
st.sidebar.info(
    "**Disclaimer:** This platform is for educational and informational purposes only. "
    "Not financial advice. Trading involves substantial risk of loss."
)
st.sidebar.markdown(f"Knowledge Packet Version: 1.0 | Last Update: May 2024")
