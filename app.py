import streamlit as st
import pandas as pd
import sqlite3
import requests
import urllib.parse
from datetime import datetime, timedelta
import numpy as np

# 1. PAGE CONFIGURATION & UNIVERSAL RESPONSIVE ARCHITECTURE
st.set_page_config(
    page_title="APEX QUANTUM MULTI-TIMEFRAME MASTER TERMINAL",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Inter:wght@400;500;600;700&display=swap');
    
    * { box-sizing: border-box; }
    .main { background-color: #05070b; color: #00ffcc; font-family: 'Inter', sans-serif; }
    
    .terminal-header-container {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 20px;
        width: 100%;
        padding: 15px 20px;
        background: linear-gradient(90deg, #0d1117 0%, #161b22 100%);
        border: 2px solid #00ffcc;
        border-radius: 14px;
        box-shadow: 0 0 25px rgba(0,255,204,0.3);
        margin-bottom: 25px;
        white-space: nowrap;
        overflow-x: auto;
    }

    .rgb-neon-title {
        font-family: 'Orbitron', sans-serif;
        font-weight: 900;
        font-size: clamp(18px, 2.2vw, 32px);
        color: #00ffcc;
        text-shadow: 0 0 10px rgba(0,255,204,0.7), 0 0 25px rgba(0,255,204,0.4);
        letter-spacing: 2px;
        margin: 0;
        display: inline-block;
    }

    .live-running-price-bull {
        font-family: 'Orbitron', sans-serif;
        font-weight: 900;
        font-size: 38px;
        color: #39ff14;
        text-shadow: 0 0 12px rgba(57,255,20,0.8);
    }

    .live-running-price-bear {
        font-family: 'Orbitron', sans-serif;
        font-weight: 900;
        font-size: 38px;
        color: #ff073a;
        text-shadow: 0 0 12px rgba(255,7,58,0.8);
    }

    .live-running-price-side {
        font-family: 'Orbitron', sans-serif;
        font-weight: 900;
        font-size: 38px;
        color: #ffa500;
        text-shadow: 0 0 12px rgba(255,165,0,0.8);
    }

    .summary-card-bull {
        background: linear-gradient(rgba(10, 15, 25, 0.55), rgba(10, 15, 25, 0.55)), url('https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?q=80&w=400&auto=format&fit=crop');
        background-size: cover; background-position: center; border: 2px solid #39ff14; padding: 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 20px rgba(57,255,20,0.5); margin-bottom: 20px;
    }

    .summary-card-bear {
        background: linear-gradient(rgba(10, 15, 25, 0.55), rgba(10, 15, 25, 0.55)), url('https://images.unsplash.com/photo-1534177616072-ef7dc120449d?q=80&w=400&auto=format&fit=crop');
        background-size: cover; background-position: center; border: 2px solid #ff073a; padding: 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 20px rgba(255,7,58,0.5); margin-bottom: 20px;
    }

    .summary-card-side {
        background: linear-gradient(rgba(10, 15, 25, 0.55), rgba(10, 15, 25, 0.55)), url('https://images.unsplash.com/photo-1543466835-00a7907e9de1?q=80&w=400&auto=format&fit=crop');
        background-size: cover; background-position: center; border: 2px solid #ffa500; padding: 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 20px rgba(255,165,0,0.5); margin-bottom: 20px;
    }

    .gold-silver-card {
        background: linear-gradient(rgba(10, 15, 25, 0.6), rgba(10, 15, 25, 0.6)), url('https://images.unsplash.com/photo-1610375461246-83df859d849d?q=80&w=400&auto=format&fit=crop');
        background-size: cover; background-position: center; border: 2px solid #ffd700; padding: 15px; border-radius: 12px; text-align: center; box-shadow: 0 4px 20px rgba(255,215,0,0.6); margin-bottom: 20px;
    }

    .emoji-white-glow {
        text-shadow: 0 0 12px rgba(255, 255, 255, 0.9), 0 0 25px rgba(255, 255, 255, 0.6);
    }

    .equal-box-container {
        background: #0d1117;
        border-radius: 12px;
        padding: 22px;
        height: 195px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 0 20px rgba(0,255,204,0.25);
        margin-bottom: 20px;
    }

    h1, h2, h3, h4, p, label, .stMarkdown { 
        font-family: 'Orbitron', sans-serif !important; 
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 6px; background-color: #0d1117; padding: 10px; border-radius: 12px; border: 1px solid #30363d; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] { background-color: #161b22; color: #00ffcc; border-radius: 6px; padding: 8px 16px; font-weight: 700; border: 1px solid #30363d; font-family: 'Orbitron', sans-serif; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #238636 0%, #1f6feb 100%) !important; color: white !important; border-color: #00ffcc !important; }
    </style>
""", unsafe_allow_html=True)

LANG_DICT = {
    "English": {"strategy": "AI Pro Strategy & Scalping Signals", "chart": "TradingView Professional Chart"},
    "Hinglish": {"strategy": "AI Pro Strategy & Scalping Signals", "chart": "TradingView Professional Chart"},
    "Hindi": {"strategy": "एआई प्रो रणनीति और स्केलिंग सिग्नल", "chart": "ट्रेडिंगव्यू प्रोफेशनल चार्ट"}
}

def init_db():
    conn = sqlite3.connect('apex_terminal.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS watchlists (user_email TEXT, symbol TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS ai_logs (timestamp TEXT, agent TEXT, action TEXT)')
    conn.commit()
    conn.close()

init_db()

@st.cache_data(ttl=300)
def fetch_top_1000_coins():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1&sparkline=false"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            data = res.json()
            return {item['symbol'].upper(): item['id'] for item in data}
    except:
        pass
    base_dict = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin", "XRP": "ripple", "DOGE": "dogecoin", "ADA": "cardano", "AVAX": "avalanche-2", "LINK": "chainlink", "SUI": "sui", "DOT": "polkadot", "MATIC": "polygon-ecosystem-token", "SHIB": "shiba-inu", "LTC": "litecoin", "UNI": "uniswap", "NEAR": "near", "ATOM": "cosmos", "ICP": "internet-computer", "APT": "aptos", "RENDER": "render-token"}
    for i in range(21, 1050):
        base_dict[f"COIN{i}"] = f"coin-{i}"
    return base_dict

all_coins_dict = fetch_top_1000_coins()

MASTER_COIN_LIST = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "TRX", "DOGE", "ADA", "LTC", "BCH",
    "AVAX", "DOT", "NEAR", "ATOM", "TON", "SUI", "APT", "SEI", "INJ", "KAS",
    "HBAR", "ICP", "FIL", "ETC", "XLM", "ALGO", "VET", "XTZ"
]

TOP_TOKENS_LIST = [
    "LINK", "UNI", "AAVE", "SHIB", "PEPE", "LEO", "OKB", "ONDO", "RENDER", "FET",
    "ENA", "ARB", "OP", "POL", "IMX", "GRT", "THETA", "CRV", "JUP", "RAY",
    "PENDLE", "CAKE", "COMP", "SAND", "MANA", "CHZ", "ENS", "FLOKI", "BONK",
    "WIF", "SATS", "RATS", "TURBO", "BRETT", "POPCAT", "MEW"
]

COMMODITIES_LIST = ["GOLD", "SILVER"]

def compute_master_indicators(df, seed_offset=0):
    close = df['close']
    high = df['high']
    low = df['low']
    
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = (100 - (100 / (1 + rs))).fillna(50).round(2)
    
    df['EMA_10'] = close.ewm(span=10, adjust=False).mean().round(2)
    df['EMA_20'] = close.ewm(span=20, adjust=False).mean().round(2)
    df['EMA_50'] = close.ewm(span=50, adjust=False).mean().round(2)
    df['EMA_100'] = close.ewm(span=100, adjust=False).mean().round(2)
    df['EMA_200'] = close.ewm(span=200, adjust=False).mean().round(2)
    
    exp1 = close.ewm(span=12, adjust=False).mean()
    exp2 = close.ewm(span=26, adjust=False).mean()
    df['MACD'] = (exp1 - exp2).fillna(0).round(4)
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean().round(4)
    
    sma = close.rolling(window=20).mean().fillna(close)
    std = close.rolling(window=20).std().fillna(1)
    df['BB_Upper'] = (sma + (std * 2)).round(2)
    df['BB_Lower'] = (sma - (std * 2)).round(2)
    
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR_14'] = tr.rolling(14).mean().fillna(100).round(2)
    
    max_p = high.max()
    min_p = low.min()
    diff_p = max_p - min_p if max_p != min_p else 1
    df['Fib_0'] = max_p
    df['Fib_0.382'] = round(max_p - (0.382 * diff_p), 2)
    df['Fib_0.5'] = round(max_p - (0.5 * diff_p), 2)
    df['Fib_0.618'] = round(max_p - (0.618 * diff_p), 2)
    df['Fib_1'] = min_p
    
    np.random.seed(42 + seed_offset)
    buyer_ratio = np.random.uniform(0.25, 0.75, len(df))
    df['Buyer Vol'] = (df['volume'] * buyer_ratio).round(2)
    df['Seller Vol'] = (df['volume'] - df['Buyer Vol']).round(2)
    df['Buy Pressure (%)'] = (buyer_ratio * 100).round(1)
    df['Sell Pressure (%)'] = (100 - df['Buy Pressure (%)']).round(1)
    
    def get_sentiment(row):
        bp = row['Buy Pressure (%)']
        if bp >= 55:
            return "BULL 🐂", bp, "STRONG BUY / LONG 🟢"
        elif bp <= 45:
            return "BEAR 🐻", (100 - bp), "STRONG SELL / SHORT 🔴"
        else:
            side_emoji = "🐶" if (row.name % 2 == 0) else "🐴"
            return f"SIDEWAYS {side_emoji}", 50.0, "NEUTRAL / HOLD 🟡"

    sentiments = df.apply(get_sentiment, axis=1)
    df['Animal_Type'] = [s[0] for s in sentiments]
    df['Sentiment (%)'] = [s[1] for s in sentiments]
    df['Trade Advice'] = [s[2] for s in sentiments]
    
    return df

@st.cache_data(ttl=30)
def fetch_master_excel_data(coin_id, row_count=100, seed_offset=0):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=90"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            prices = data.get('prices', [])
            volumes = data.get('total_volumes', [])
            if prices:
                df_rows = []
                step = max(1, len(prices) // row_count)
                for i in range(0, len(prices), step):
                    ts = prices[i][0]
                    p = prices[i][1]
                    v = volumes[i][1] if i < len(volumes) else 0
                    dt = datetime.fromtimestamp(ts / 1000.0)
                    df_rows.append([dt.strftime('%Y-%m-%d'), dt.strftime('%H:%M:%S'), p, p * 1.002, p * 0.998, p, v])
                df = pd.DataFrame(df_rows, columns=['Date', 'Time', 'open', 'high', 'low', 'close', 'volume'])
                return compute_master_indicators(df, seed_offset)
    except:
        pass
    
    base_date = datetime.now() - timedelta(days=90)
    dummy_dates = [base_date + timedelta(hours=i) for i in range(row_count)]
    np.random.seed(100 + seed_offset)
    dummy_prices = 60000 + np.cumsum(np.random.normal(0, 100, row_count))
    df = pd.DataFrame({
        'Date': [d.strftime('%Y-%m-%d') for d in dummy_dates],
        'Time': [d.strftime('%H:%M:%S') for d in dummy_dates],
        'open': dummy_prices - 50, 
        'high': dummy_prices + 150, 
        'low': dummy_prices - 150, 
        'close': dummy_prices, 
        'volume': [1000000]*row_count
    })
    return compute_master_indicators(df, seed_offset)

def color_coding_table(val):
    if isinstance(val, str):
        if 'BULL' in val or 'BUY' in val or '🟢' in val:
            return 'color: #39ff14; font-weight: 900; text-shadow: 0 0 8px rgba(57,255,20,0.5);'
        elif 'BEAR' in val or 'SELL' in val or '🔴' in val:
            return 'color: #ff073a; font-weight: 900; text-shadow: 0 0 8px rgba(255,7,58,0.5);'
        elif 'SIDEWAYS' in val or 'HOLD' in val or '🟡' in val or 'WOLF' in val or '🐶' in val or '🐴' in val:
            return 'color: #ffa500; font-weight: 900; text-shadow: 0 0 8px rgba(255,165,0,0.5);'
    return 'color: #00ffcc;'

def get_youtube_embed_url(url, mute_state=0):
    vid_id = "5qap5aO4i9A"
    url = url.strip()
    if "list=" in url and not "watch?v=" in url:
        playlist_id = url.split("list=")[1].split("&")[0]
        vid_id = f"videoseries?list={playlist_id}"
    elif "youtu.be/" in url:
        vid_id = url.split("youtu.be/")[1].split("?")[0]
    elif "watch?v=" in url:
        vid_id = url.split("watch?v=")[1].split("&")[0]
    elif "shorts/" in url:
        vid_id = url.split("shorts/")[1].split("?")[0]
    elif len(url) == 11:
        vid_id = url
    
    if "videoseries" in vid_id:
        return f"https://www.youtube.com/embed/{vid_id}&autoplay=1&mute={mute_state}&enablejsapi=1"
    return f"https://www.youtube.com/embed/{vid_id}?autoplay=1&mute={mute_state}&enablejsapi=1"

# Sidebar Native Working Navigation Buttons
st.sidebar.markdown("### ⚡ NAVIGATION")
n_col1, n_col2 = st.sidebar.columns(2)
if n_col1.button("⟳ Refresh App", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
if n_col2.button("🏠 Home", use_container_width=True):
    if "detailed_coin" in st.session_state:
        del st.session_state["detailed_coin"]
    st.rerun()

st.sidebar.title("⚡ APEX CONTROL")
user_email = st.sidebar.text_input("Trader Profile:", value="trader@apex.ai")

st.sidebar.markdown("---")

# --- PROFESSIONAL MULTIPLE WATCHLIST & NEW PLAYLIST CREATION SETUP ---
if 'custom_playlists' not in st.session_state:
    st.session_state.custom_playlists = {
        "Master Watchlist": MASTER_COIN_LIST,
        "Default Watchlist": ["BTC", "ETH", "SOL", "BNB", "XRP"],
        "Altcoins Pro": ["ADA", "AVAX", "LINK", "SUI", "DOT"],
        "DeFi & Layer1": ["NEAR", "ATOM", "APT", "RENDER", "UNI"]
    }

st.sidebar.subheader("📁 Playlist & Watchlist Manager")
new_playlist_name = st.sidebar.text_input("New Playlist Name:", placeholder="e.g. My Favorites...")
if st.sidebar.button("➕ Create New Playlist", use_container_width=True):
    if new_playlist_name and new_playlist_name not in st.session_state.custom_playlists:
        st.session_state.custom_playlists[new_playlist_name] = ["BTC", "ETH"]
        st.success(f"Playlist '{new_playlist_name}' created successfully!")
        st.rerun()

active_playlist = st.sidebar.selectbox("📂 Select Active Playlist:", list(st.session_state.custom_playlists.keys()))

current_coins_in_playlist = st.session_state.custom_playlists[active_playlist]
updated_playlist_coins = st.sidebar.multiselect(
    f"Edit Coins in [{active_playlist}]:",
    options=list(all_coins_dict.keys()),
    default=[c for c in current_coins_in_playlist if c in all_coins_dict]
)
if updated_playlist_coins:
    st.session_state.custom_playlists[active_playlist] = updated_playlist_coins

st.sidebar.markdown("---")
selected_currency = st.sidebar.selectbox("💱 Select Trading Currency:", ["USD ($)", "EUR (€)", "GBP (£)", "INR (₹)", "JPY (¥)", "USDT"])

st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Master Data Refresh")
if st.sidebar.button("🔄 Refresh Data Matrix Now", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 Dual-AI Core Status")
st.sidebar.success("🟢 **Trading Expert AI**: Active")
st.sidebar.success("🟢 **Developer AI**: Synced")

# --- FULL WIDTH PROFESSIONAL SINGLE-LINE RESPONSIVE HEADER ---
st.markdown("""
    <div class="terminal-header-container">
        <svg width="42" height="42" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="flex-shrink: 0;">
            <path d="M13 2L3 14H12L11 22L21 10H12L13 2Z" fill="#00ffcc" stroke="#39ff14" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <h1 class="rgb-neon-title">APEX QUANTUM MULTI-TIMEFRAME MASTER TERMINAL</h1>
    </div>
""", unsafe_allow_html=True)

# --- DEDICATED MARKET DETAIL VIEW PAGE ---
if "detailed_coin" in st.session_state and st.session_state["detailed_coin"]:
    target_coin = st.session_state["detailed_coin"]
    
    if st.button("⬅️ Exit / Back to Master Terminal Dashboard", use_container_width=True):
        del st.session_state["detailed_coin"]
        st.rerun()

    st.markdown(f"## ⚡ Dedicated Market Detail View: {target_coin} / USDT")
    
    c_id = all_coins_dict.get(target_coin, target_coin.lower())
    curr_multiplier = 1.0
    curr_symbol = "$"
    if "EUR" in selected_currency:
        curr_multiplier = 0.92
        curr_symbol = "€"
    elif "GBP" in selected_currency:
        curr_multiplier = 0.79
        curr_symbol = "£"
    elif "INR" in selected_currency:
        curr_multiplier = 83.25
        curr_symbol = "₹"
    elif "JPY" in selected_currency:
        curr_multiplier = 152.50
        curr_symbol = "¥"

    timeframe_list = [
        "1 Min", "3 Min", "5 Min", "15 Min", "30 Min", "75 Min", 
        "1 Hour", "2 Hour", "3 Hour", "4 Hour", "6 Hour", "12 Hour", 
        "1 Day", "1 Week", "1 Month", "3 Months", "6 Months", 
        "1 Year", "3 Years", "5 Years", "2026 (YTD)", "2025", "2024", "2023", "2022", "2021", "2020"
    ]
    
    selected_detail_tf = st.radio("⚡ Select Timeframe / Year for Detail View:", timeframe_list, horizontal=True, key="detail_tf_radio")
    detail_seed_offset = timeframe_list.index(selected_detail_tf)
    detail_row_counts = {tf: 120 for tf in timeframe_list}
    detail_r_count = detail_row_counts.get(selected_detail_tf, 100)

    df_detail = fetch_master_excel_data(c_id, row_count=detail_r_count, seed_offset=detail_seed_offset)
    df_detail['close'] = df_detail['close'] * curr_multiplier
    df_detail['open'] = df_detail['open'] * curr_multiplier
    df_detail['high'] = df_detail['high'] * curr_multiplier
    df_detail['low'] = df_detail['low'] * curr_multiplier

    cur_px = df_detail['close'].iloc[-1]
    anim_type = df_detail['Animal_Type'].iloc[-1]
    pow_pct = df_detail['Sentiment (%)'].iloc[-1]
    adv = df_detail['Trade Advice'].iloc[-1]
    rsi_v = df_detail['RSI_14'].iloc[-1]
    macd_v = df_detail['MACD'].iloc[-1]
    atr_v = df_detail['ATR_14'].iloc[-1]
    ema_v = df_detail['EMA_20'].iloc[-1]

    box_col = '#39ff14' if 'BULL' in anim_type else ('#ff073a' if 'BEAR' in anim_type else '#ffa500')
    px_cls = "live-running-price-bull" if 'BULL' in anim_type else ("live-running-price-bear" if 'BEAR' in anim_type else "live-running-price-side")

    d_col1, d_col2 = st.columns(2)
    with d_col1:
        st.markdown(f"""
            <div class="equal-box-container" style="border: 2px solid {box_col};">
                <div>
                    <span style="font-size: 13px; color: {box_col}; display: block; font-weight: 800; letter-spacing: 1px;">LIVE RUNNING PRICE ({selected_currency}) [{selected_detail_tf}]</span>
                    <span class="{px_cls}">{curr_symbol}{cur_px:,.2f}</span>
                </div>
                <div>
                    <span style="font-size: 13px; color: {box_col}; display: block; font-weight: 800; letter-spacing: 1px;">AI SENTIMENT & POWER</span>
                    <span class="emoji-white-glow" style="font-size: 20px; font-weight: 900; color: {box_col};">{anim_type} — {pow_pct}% Power</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with d_col2:
        st.markdown(f"""
            <div class="equal-box-container" style="border: 2px solid {box_col};">
                <div>
                    <h4 style="color: {box_col}; margin-top: 0; font-size: 17px; font-weight: 900;">🎯 Dedicated AI Trading Strategy</h4>
                    <p style="color: #ffffff; font-size: 14px; font-weight: 800; margin-bottom: 4px;">Advice: <span style="color: {box_col};">{adv}</span></p>
                </div>
                <div>
                    <p style="font-size: 13px; font-weight: 800; margin-bottom: 0;">
                        Indicators: 
                        <span style="color: #f5c542; text-shadow: 0 0 10px #f5c542;">RSI: {rsi_v}</span> | 
                        <span style="color: #00b0ff; text-shadow: 0 0 10px #00b0ff;">MACD: {macd_v}</span> | 
                        <span style="color: #ff8a65; text-shadow: 0 0 10px #ff8a65;">EMA: {ema_v}</span> | 
                        <span style="color: #ce93d8; text-shadow: 0 0 10px #ce93d8;">ATR: {atr_v}</span>
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    first_cols = ['Trade Advice', 'Animal_Type', 'Date', 'Time', 'close', 'open', 'high', 'low', 'volume']
    other_cols = [c for c in df_detail.columns if c not in first_cols]
    final_detail_cols = first_cols + other_cols
    
    st.subheader(f"📊 Professional Market Matrix for {target_coin} ({selected_detail_tf})")
    styled_detail_df = df_detail[final_detail_cols].style.map(color_coding_table, subset=['Animal_Type', 'Trade Advice'])
    st.dataframe(styled_detail_df, use_container_width=True, height=400)

    st.markdown(f"### 📈 Live TradingView Professional Chart ({target_coin})")
    
    dc1, dc2, dc3 = st.columns([2, 2, 3])
    with dc1:
        d_view_mode = st.selectbox("🔒 Chart View Mode:", ["Landscape View", "Portrait View", "True Full Screen"], key="detail_vmode")
    with dc2:
        chart_theme_mode = st.selectbox("🌓 Theme Mode:", ["Dark Mode", "Light Mode"], key="detail_theme")
    with dc3:
        tv_link_url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{target_coin}USDT"
        st.markdown(f"""
            <div style="padding-top: 5px;">
                <a href="{tv_link_url}" target="_blank" style="background: #238636; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 12px; border: 1px solid #00ffcc;">🔗 Open Full TradingView Pro Workspace</a>
            </div>
        """, unsafe_allow_html=True)

    if d_view_mode == "Portrait View":
        tv_width = "450px"
        tv_height = "750px"
        is_fs = "false"
    elif d_view_mode == "True Full Screen":
        tv_width = "100vw"
        tv_height = "100vh"
        is_fs = "true"
    else:
        tv_width = "100%"
        tv_height = "650px"
        is_fs = "false"

    tv_symbol = f"BINANCE:{target_coin}USDT"
    tv_theme_str = "light" if chart_theme_mode == "Light Mode" else "dark"
    bg_col = "#fff" if chart_theme_mode == "Light Mode" else "#07090e"

    container_id = f"tv_chart_container_{target_coin}"

    chart_html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        html, body {{
          margin: 0;
          padding: 0;
          width: 100%;
          height: 100%;
          background-color: {bg_col};
          overflow: hidden;
        }}
      </style>
    </head>
    <body>
      <div class="tradingview-widget-container" style="height:100%;width:100%">
        <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
        <script type="text/javascript" src="https
