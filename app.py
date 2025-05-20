# Function to get color based on signal
def get_chart_color(score):
    try:
        score = int(score)
        if score >= 8:
            return "green"
        elif score <= 3:
            return "red"
        else:
            return "orange"
    except:
        return "gray"

# Chart rendering
try:
    df = yf.download(ticker, period=timeframe, interval="5m" if timeframe == "1d" else "1d")
    if df.empty or "Close" not in df:
        raise ValueError("No close price data available.")

    # Get vibe score for color logic
    headline = fetch_headline(ticker)
    vibe = get_vibe_score(headline)
    if "Score:" in vibe:
        score_line = vibe.split("Score:")[1].split("\n")[0].strip()
        chart_color = get_chart_color(score_line)
    else:
        score_line = "N/A"
        chart_color = "gray"

    # Plot chart
    fig, ax = plt.subplots()
    ax.plot(df.index, df["Close"], color=chart_color, linewidth=2)
    ax.set_title(f"{ticker} Close Price", fontsize=14)
    ax.set_xlabel("Time", fontsize=10)
    ax.set_ylabel("Price", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.tick_params(axis='x', labelrotation=30)
    st.pyplot(fig)

    # Display headline
    st.markdown(f"📰 **Headline:** *{headline}*")

    # Display score
    if "Score:" in vibe:
        reasoning = "\n".join(vibe.split("Score:")[1].split("\n")[1:]).strip()
        st.markdown(f"🧠 **Vibe Score:** `{score_line}`")
        st.markdown("💬 **Reasoning:**")
        st.markdown(reasoning)
    else:
        st.markdown(f"🧠 **Vibe Score:** *{vibe}*")

    # AI signal
    try:
        score = int(score_line)
        if score >= 8:
            ai_signal = "📈 Buy"
        elif score <= 3:
            ai_signal = "📉 Sell"
        else:
            ai_signal = "🤖 Hold"
    except:
        ai_signal = "⚠️ No recommendation"

    st.markdown(f"🤖 **AI Signal:** {ai_signal}")

except Exception as e:
    st.error(f"Chart error for {ticker}: {e}")
