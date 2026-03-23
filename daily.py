import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Page Configuration ---
st.set_page_config(page_title="Market Pulse AI", layout="wide")

st.title("📈 Market Pulse: Real-Time Sector Analysis")
st.markdown("Automated technical analysis for leading stocks across major sectors.")

# --- 1. Define Sectors and Tickers ---
SECTORS = {
    "Technology": ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL"],
    "Financials": ["JPM", "V", "MA", "BAC", "GS"],
    "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
    "Cons. Discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE"],
    "Communication": ["GOOGL", "META", "NFLX", "TMUS", "DIS"]
}

# --- 2. Technical Analysis Logic ---
def get_indicators(df):
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # SMAs
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

def get_signal(row):
    score = 0
    if row['Close'] > row['SMA200']: score += 1
    if row['RSI'] < 30: score += 1
    if row['RSI'] > 70: score -= 1
    if row['MACD'] > row['Signal']: score += 1
    
    if score >= 2: return "🔥 Strong Buy"
    if score == 1: return "✅ Buy"
    if score == 0: return "Neutral"
    return "⚠️ Sell"

# --- 3. Sidebar UI ---
st.sidebar.header("Control Panel")
selected_sector = st.sidebar.selectbox("Select Sector", list(SECTORS.keys()))
update_interval = st.sidebar.selectbox("Refresh Interval", ["Manual", "1 Hour", "Daily"])

if st.sidebar.button('🔄 Refresh Data'):
    st.cache_data.clear()

# --- 4. Main Data Fetching ---
@st.cache_data(ttl=3600) # Cache data for 1 hour
def load_data(tickers):
    data_list = []
    for ticker in tickers:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        df = get_indicators(df)
        last_row = df.iloc[-1]
        data_list.append({
            "Ticker": ticker,
            "Price": round(float(last_row['Close']), 2),
            "RSI": round(float(last_row['RSI']), 2),
            "SMA 200": round(float(last_row['SMA200']), 2),
            "Signal": get_signal(last_row),
            "Raw_Data": df
        })
    return data_list

# --- 5. Display Dashboard ---
with st.spinner('Fetching live market data...'):
    market_data = load_data(SECTORS[selected_sector])

# Metric Cards
cols = st.columns(len(market_data))
for i, stock in enumerate(market_data):
    with cols[i]:
        st.metric(label=stock['Ticker'], value=f"${stock['Price']}", delta=stock['Signal'])

# Detailed Table
st.subheader(f"Detailed Analysis: {selected_sector}")
df_display = pd.DataFrame(market_data).drop(columns=['Raw_Data'])

# Styling the Table
def color_signal(val):
    color = 'green' if 'Buy' in val else 'red' if 'Sell' in val else 'gray'
    return f'color: {color}; font-weight: bold'

st.table(df_display.style.applymap(color_signal, subset=['Signal']))

# --- 6. Interactive Charting ---
st.subheader("Technical Charting")
selected_ticker = st.selectbox("Select Ticker for Deep Dive", SECTORS[selected_sector])
stock_record = next(item for item in market_data if item["Ticker"] == selected_ticker)
plot_df = stock_record['Raw_Data'].tail(100)

fig = go.Figure()
fig.add_trace(go.Candlestick(x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], 
                low=plot_df['Low'], close=plot_df['Close'], name="Price"))
fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA50'], name="SMA 50", line=dict(color='orange')))
fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA200'], name="SMA 200", line=dict(color='blue')))

fig.update_layout(title=f"{selected_ticker} Price Action & Moving Averages", xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

st.info("The data updates automatically based on your cache settings. Click 'Refresh Data' to force an update.")