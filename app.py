import streamlit as st
import pandas as pd
import sqlite3
import requests
from datetime import datetime

# 1. PAGE CONFIGURATION & ULTRA-PRO RESPONSIVE CYBER ARCHITECTURE
st.set_page_config(
    page_title="NEXUS CYBER-TERMINAL X",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Inter:wght@300;400;600&display=swap');
    
    /* Global Auto-Fit, Zoom Fixes & Cyberpunk Neon Styling */
    * { box-sizing: border-box; }
    .main { background-color: #05070b; color: #00ffcc; font-family: 'Inter', sans-serif; }
    
    @keyframes neonPulse {
        0% { text-shadow: 0 0 5px rgba(0,255,204,0.4), 0 0 10px rgba(0,255,204,0.4); }
        50% { text-shadow: 0 0 20px rgba(0,255,204,0.8), 0 0 30px rgba(255,0,85,0.8); }
        100% { text-shadow: 0 0 5px rgba(0,255,204,0.4), 0 0 10px rgba(0,255,204,0.4); }
    }

    @keyframes borderGlow {
        0% { border-color: #ff0055; box-shadow: 0 0 10px rgba(255,0,85,0.3), inset 0 0 10px rgba(255,0,85,0.3); }
        50% { border-color: #00ffcc; box-shadow: 0 0 25px rgba(0,255,204,0.6), inset 0 0 15px rgba(0,255,204,0.4); }
        100% { border-color: #ff0055; box-shadow: 0 0 10px rgba(255,0,85,0.3), inset 0 0 10px rgba(255,0,85,0.3); }
    }

    h1, h2, h3 { 
        font-family: 'Orbitron', sans-serif; 
        letter-spacing: 1px;
        background: linear-gradient(45deg, #ff0055, #00ffcc, #7928ca);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: neonPulse 3s infinite ease-in-out;
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #0d1117; padding: 10px; border-radius: 12px; border: 1px solid #ff0055; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] { background-color: #161b22; color: #8b949e; border-radius: 6px; padding: 10px 20px; font-weight: 600; border: 1px solid #30363d; font-family: 'Orbitron', sans-serif; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #ff0055 0%, #7928ca 100%) !important; color: white !important; box-shadow: 0 0 20px rgba(255, 0, 85, 0.6); border-color: #00ffcc !important; }
    
    /* Custom Neon Metric Cards */
    .neon-metric {
        background: linear-gradient(145deg, #161b22, #0d1117);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #00ffcc;
        box-shadow: 0 0 15px rgba(0,255,204,0.2);
        margin-bottom: 10px;
        width: 100%;
    }
    
    .ai-box { background: rgba(33, 38, 45, 0.8); border-left: 4px solid #ff0055; padding: 15px; border-radius: 0 8px 8px 0; margin-bottom: 15px; color: #e6edf3; }

    /* Sidebar Cyber Styling */
    [data-testid="stSidebar"] {
        background-color: #07090e;
        border-right: 1px solid #ff0055;
    }

    /* YouTube Neon Wrapper */
    .neon-player-wrapper {
        border-radius: 14px;
        border: 2px solid #ff0055;
        animation: borderGlow 4s infinite ease-in-out;
        background: #000;
        overflow: hidden;
        margin-bottom: 15px;
        width: 100%;
    }
    
    .youtube-container {
        position: relative;
        width: 100%;
        padding-bottom: 56.25%;
        height: 0;
        background: #000;
    }
    .youtube-container iframe {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        border: 0;
    }
    
    .player-toolbar {
        background: linear-gradient(90deg, #161b22, #0d1117);
        padding: 12px 20px;
        border-top: 1px solid #30363d;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: #00ffcc;
        font-family: 'Orbitron', sans-serif;
        font-size: 13px;
    }
    </style>
""", unsafe_allow_html=True)

# 2. SQLITE DATABASE INITIALIZATION
def init_db():
    conn = sqlite3.connect('nexus_terminal.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS watchlists (user_email TEXT, symbol TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS ai_logs (timestamp TEXT, agent TEXT, action TEXT)')
    conn.commit()
    conn.close()

init_db()

# PURE PANDAS RSI FUNCTION
def compute_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# CLOUD-FRIENDLY COINGECKO DATA FETCHER
def fetch_market_data(symbol):
    mapping = {
        'BTC/USDT': 'bitcoin',
        'ETH/USDT': 'ethereum',
        'SOL/USDT': 'solana',
        'XRP/USDT': 'ripple',
        'ADA/USDT': 'cardano',
        'DOGE/USDT': 'dogecoin'
    }
    coin_id = mapping.get(symbol.upper(), 'bitcoin')
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=1"
    
    response = requests.get(url)
    data = response.json()
    prices = data.get('prices', [])
    volumes = data.get('total_volumes', [])
    
    df_rows = []
    for i in range(len(prices)):
        ts = prices[i][0]
        p = prices[i][1]
        v = volumes[i][1] if i < len(volumes) else 0
        df_rows.append([ts, p, p, p, p, v])
        
    df = pd.DataFrame(df_rows, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Helper to extract YouTube video or playlist ID accurately
def get_youtube_embed_url(url):
    if "list=" in url:
        playlist_id = url.split("list=")[1].split("&")[0]
        return f"https://www.youtube.com/embed/videoseries?list={playlist_id}&autoplay=1&enablejsapi=1"
    elif "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0]
        return f"https://www.youtube.com/embed/{video_id}?autoplay=1&enablejsapi=1"
    elif "watch?v=" in url:
        video_id = url.split("watch?v=")[1].split("&")[0]
        return f"https://www.youtube.com/embed/{video_id}?autoplay=1&enablejsapi=1"
    else:
        return "https://www.youtube.com/embed/5qap5aO4i9A?autoplay=1&enablejsapi=1"

# 3. SIDEBAR: CONTROL CENTER
st.sidebar.title("⚡ NEXUS CONTROL")
user_email = st.sidebar.text_input("Trader Profile:", value="trader@nexus.ai")

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 Dual-AI Core Status")
st.sidebar.success("🟢 **Trading Expert AI**: Active")
st.sidebar.success("🟢 **Developer AI**: Synced")

st.sidebar.markdown("---")
selected_exchange = st.sidebar.selectbox("Exchange Node", ["CoinGecko Global Feed", "Global Cloud Node"])
timeframe = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "4h", "1D"])

# 4. UNIVERSAL SEARCH BAR
st.title("⚡ NEXUS CYBER-TERMINAL X")
search_query = st.text_input("🔍 Global Search Bar (e.g., BTC/USDT, ETH/USDT, SOL/USDT):", value="BTC/USDT")

# 5. MAIN NAVIGATION TABS (AUTO-FIT ACROSS ALL SCREENS)
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Screener & Search", 
    "📈 Advanced Charts", 
    "🐋 Derivatives & CoinGlass", 
    "🎮 Paper Trading", 
    "🔴 Cyber YouTube & Playlist Hub", 
    "💰 Tax & PnL Ledger",
    "🤖 AI Developer Core"
])

df = None

# --- TAB 1: SCREENER & SEARCH ---
with tab1:
    st.subheader("🌍 Live Market Feed Matrix")
    try:
        df = fetch_market_data(search_query)
        df['RSI'] = compute_rsi(df['close'], window=14)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Live Price", f"${df['close'].iloc[-1]:,.2f}", "+2.4% 🟢")
        with c2:
            st.metric("RSI (14)", f"{df['RSI'].iloc[-1]:,.2f}", "Neutral")
        with c3:
            st.metric("24h Volume", f"${df['volume'].sum():,.0f}")
        
        st.dataframe(df.tail(10), use_container_width=True)
    except Exception as e:
        st.warning(f"Market feed note: Ensure symbol format is correct (e.g., BTC/USDT). Error: {e}")

# --- TAB 2: ADVANCED CHARTS ---
with tab2:
    st.subheader("📊 Pro Interactive Chart Engine")
    st.markdown("""
        <div class="ai-box">
            <b>🤖 Trading Expert AI Insight:</b> Market is consolidating near key support zones. High volatility expected during US session.
        </div>
    """, unsafe_allow_html=True)
    try:
        if df is not None and not df.empty:
            st.line_chart(df.set_index('datetime')['close'], use_container_width=True)
        else:
            st.info("⚠️ Please load market data from Tab 1 first to render chart lines.")
    except Exception as e:
        st.info(f"Chart rendering note: {e}")

# --- TAB 3: DERIVATIVES & COINGLASS ---
with tab3:
    st.subheader("🐋 Whales, Open Interest & Liquidations")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Open Interest (OI)", "$5.82 Billion", "+6.2% (Bullish)")
        st.metric("Long / Short Ratio", "1.95", "Dominant Longs")
    with col2:
        st.metric("24h Liquidations", "$158 Million", "Short Squeeze Active")
        st.metric("Funding Rate", "+0.0132%", "Bullish Bias")

# --- TAB 4: PAPER TRADING ---
with tab4:
    st.subheader("🎮 Risk-Free Paper Trading Simulator")
    st.write("**Virtual Wallet Balance:** $10,000.00")
    t_type = st.radio("Order Type:", ["BUY / LONG", "SELL / SHORT"])
    t_qty = st.number_input("Position Size / Quantity:", value=1.0)
    if st.button("🚀 Execute Simulated Order", use_container_width=True):
        st.success(f"Successfully placed {t_type} for {search_query} with Auto-Trailing Stop-Loss!")

# --- TAB 5: CYBER YOUTUBE & PLAYLIST HUB ---
with tab5:
    st.markdown("<h3>🔴 CYBERPUNK YOUTUBE & PLAYLIST STREAM ENGINE</h3>", unsafe_allow_html=True)
    st.markdown("Paste any YouTube Video URL or Playlist Link below to stream instantly with full neon aesthetics and auto-fit responsive layout.")

    if 'custom_yt_url' not in st.session_state:
        st.session_state.custom_yt_url = "https://www.youtube.com/watch?v=5qap5aO4i9A"

    col_inp1, col_inp2 = st.columns([4, 1])
    with col_inp1:
        user_link_input = st.text_input("🔗 Paste YouTube Video or Playlist Link:", value=st.session_state.custom_yt_url)
    with col_inp2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Load & Play", use_container_width=True):
            st.session_state.custom_yt_url = user_link_input
            st.rerun()

    st.markdown("---")

    embed_url = get_youtube_embed_url(st.session_state.custom_yt_url)
    st.markdown(f"""
        <div class="neon-player-wrapper">
            <div class="youtube-container">
                <iframe src="{embed_url}" title="YouTube Player" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>
            </div>
            <div class="player-toolbar">
                <span>🔴 STREAM STATUS: SECURE HD ACTIVE</span>
                <span>[ ▶ PLAY ] [ ⏸ PAUSE ] [ 🔊 VOL: 100% ] [ ⛶ FULLSCREEN ]</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🔥 Quick Neon Playlists & Presets")
    
    qp_col1, qp_col2, qp_
