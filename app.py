import json
import re
import sqlite3
import threading
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components
from plotly.subplots import make_subplots

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

st.set_page_config(
    page_title="APEX Quantum Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================================
# 1. CONSTANTS & THEME
# =====================================================================
BG, PANEL, SIDE, GRID = "#05070b", "#0d1117", "#0a0d13", "#161b22"
ACCENT, UP, DOWN, WARN, MUTED = "#00ffcc", "#26a69a", "#ef5350", "#ffb300", "#8b949e"

BINANCE_SPOT = "https://api.binance.com/api/v3"
BINANCE_FUT = "https://fapi.binance.com"
COINGECKO = "https://api.coingecko.com/api/v3"
FX_URL = "https://api.frankfurter.app/latest"
HEADERS = {"User-Agent": "apex-terminal/3.0"}
TIMEOUT = 8
START_CASH = 10_000.0
DB_PATH = "apex_terminal.db"

# label -> (binance interval, yahoo interval, yahoo period, resample rule)
TIMEFRAMES = {
    "1 Min": ("1m", "1m", "5d", None),
    "5 Min": ("5m", "5m", "30d", None),
    "15 Min": ("15m", "15m", "30d", None),
    "30 Min": ("30m", "30m", "60d", None),
    "1 Hour": ("1h", "1h", "180d", None),
    "4 Hour": ("4h", "1h", "360d", "4h"),
    "1 Day": ("1d", "1d", "2y", None),
    "1 Week": ("1w", "1wk", "5y", None),
}
TV_INTERVALS = {"1 Min": "1", "5 Min": "5", "15 Min": "15", "30 Min": "30",
                "1 Hour": "60", "4 Hour": "240", "1 Day": "D", "1 Week": "W"}
CURRENCIES = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "JPY": "¥", "USDT": "₮"}
FALLBACK_FX = {"USD": 1.0, "USDT": 1.0, "EUR": 0.92, "GBP": 0.79, "INR": 83.5, "JPY": 152.5}
LANGS = {"English": "Market Sentiment Matrix", "Hinglish": "Market Mood Matrix (Bazaar Mood)",
         "Hindi": "बाज़ार भावना मैट्रिक्स"}

DEFAULT_PLAYLISTS = {
    "Default Watchlist": ["BTC", "ETH", "SOL", "BNB"],
    "Altcoins Pro": ["ADA", "AVAX", "LINK", "SUI", "DOT"],
    "DeFi & Layer1": ["NEAR", "ATOM", "APT", "UNI", "INJ"],
}
NSE_DEFAULT = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
               "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "TATAMOTORS.NS", "LT.NS"]
INDEX_TICKERS = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN", "INDIA VIX": "^INDIAVIX"}

st.markdown(f"""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
    background-color: {BG} !important; color: #d6fff5 !important;
}}
[data-testid="stSidebar"] {{ background-color: {SIDE} !important; border-right: 1px solid #1b2330; }}
h1, h2, h3, h4, h5, label, p {{ color: #d6fff5 !important; }}
.apex-title {{ font-weight: 800; font-size: 28px; color: {ACCENT};
              text-shadow: 0 0 10px rgba(0,255,204,0.35); margin-bottom: 2px; }}
.apex-sub {{ color: {MUTED}; font-size: 13px; margin-bottom: 10px; }}
.apex-live {{ background: {PANEL}; border: 1px solid {ACCENT}; border-radius: 12px; padding: 12px 18px;
             box-shadow: 0 0 18px rgba(0,255,204,0.18); display:flex; gap:28px; align-items:center; flex-wrap:wrap; }}
.apex-price {{ font-size: 30px; font-weight: 900; color: {UP}; text-shadow: 0 0 8px rgba(38,166,154,0.5); }}
.apex-card {{ background: {PANEL}; border: 1px solid #1b2330; border-radius: 10px; padding: 12px 16px; margin: 8px 0; }}
.badge {{ padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 700; }}
.badge-live {{ background:#0f3d2e; color:{UP}; }}
.badge-warn {{ background:#3d2a0f; color:{WARN}; }}
.stTabs [data-baseweb="tab-list"] {{ background:{PANEL}; border:1px solid #1b2330; border-radius:10px; gap:4px; flex-wrap:wrap; padding:6px; }}
.stTabs [data-baseweb="tab"] {{ color:#7ee7d2; font-weight:600; }}
.stTabs [aria-selected="true"] {{ color:{BG} !important; background:{ACCENT} !important; border-radius:6px; }}
.stTabs [data-baseweb="tab-highlight"] {{ display:none !important; }}
input, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] > div {{
    background:{PANEL} !important; color:#d6fff5 !important; border-color:#1b2330 !important; }}
[data-baseweb="popover"] li, [data-baseweb="menu"] {{ background:{PANEL} !important; color:#d6fff5 !important; }}
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
    background:{PANEL}; color:{ACCENT}; border:1px solid {ACCENT}; border-radius:8px; font-weight:700; }}
.stButton > button:hover, .stFormSubmitButton > button:hover {{ background:{ACCENT}; color:{BG}; }}
[data-testid="stMetric"] {{ background:{PANEL}; border:1px solid #1b2330; border-radius:10px; padding:10px 14px; }}
[data-testid="stMetricValue"] {{ color:{ACCENT} !important; }}
[data-testid="stMetricLabel"] {{ color:{MUTED} !important; }}
[data-testid="stAlert"] {{ background:{PANEL} !important; border:1px solid #1b2330; }}
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. DATABASE (single source of truth: watchlists, alerts, trades, settings)
# =====================================================================
SCHEMA = """
CREATE TABLE IF NOT EXISTS playlists (name TEXT PRIMARY KEY, created_at TEXT);
CREATE TABLE IF NOT EXISTS playlist_coins (playlist TEXT, symbol TEXT, pos INTEGER,
                                           PRIMARY KEY (playlist, symbol));
CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT,
                                   cond TEXT, price REAL, created_at TEXT);
CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, symbol TEXT,
                                   side TEXT, qty REAL, price REAL, pnl REAL);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
"""
_DB_LOCK = threading.Lock()


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.executescript(SCHEMA)
    # Seed defaults only once
    if conn.execute("SELECT COUNT(*) FROM playlists").fetchone()[0] == 0:
        for i, (name, coins) in enumerate(DEFAULT_PLAYLISTS.items()):
            conn.execute("INSERT INTO playlists (name, created_at) VALUES (?, ?)",
                         (name, f"2026-01-0{i + 1}T00:00:00"))
            conn.executemany("INSERT INTO playlist_coins (playlist, symbol, pos) VALUES (?, ?, ?)",
                             [(name, c, p) for p, c in enumerate(coins)])
    conn.commit()
    return conn


def db_write(sql, params=()):
    with _DB_LOCK:
        conn = get_conn()
        conn.execute(sql, params)
        conn.commit()


def db_read(sql, params=()):
    with _DB_LOCK:
        return get_conn().execute(sql, params).fetchall()


def get_setting(key, default):
    rows = db_read("SELECT value FROM settings WHERE key = ?", (key,))
    return rows[0][0] if rows else default


def set_setting(key, value):
    db_write("INSERT INTO settings (key, value) VALUES (?, ?) "
             "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, str(value)))


def load_playlists():
    rows = db_read("""
        SELECT p.name, c.symbol FROM playlists p
        LEFT JOIN playlist_coins c ON c.playlist = p.name
        ORDER BY p.created_at, p.name, c.pos
    """)
    out = {}
    for name, sym in rows:
        out.setdefault(name, [])
        if sym:
            out[name].append(sym)
    return out


def create_playlist(name):
    db_write("INSERT OR IGNORE INTO playlists (name, created_at) VALUES (?, ?)", (name, now_iso()))
    save_playlist_coins(name, ["BTC", "ETH"])


def delete_playlist(name):
    with _DB_LOCK:
        conn = get_conn()
        conn.execute("DELETE FROM playlist_coins WHERE playlist = ?", (name,))
        conn.execute("DELETE FROM playlists WHERE name = ?", (name,))
        conn.commit()


def save_playlist_coins(name, coins):
    unique = list(dict.fromkeys(coins))
    with _DB_LOCK:
        conn = get_conn()
        conn.execute("DELETE FROM playlist_coins WHERE playlist = ?", (name,))
        conn.executemany("INSERT INTO playlist_coins (playlist, symbol, pos) VALUES (?, ?, ?)",
                         [(name, c, i) for i, c in enumerate(unique)])
        conn.commit()


def load_trades():
    with _DB_LOCK:
        return pd.read_sql_query("SELECT * FROM trades ORDER BY id", get_conn())


def add_trade(symbol, side, qty, price, pnl):
    db_write("INSERT INTO trades (ts, symbol, side, qty, price, pnl) VALUES (?, ?, ?, ?, ?, ?)",
             (now_iso(), symbol, side, qty, price, pnl))


def load_alerts():
    with _DB_LOCK:
        return pd.read_sql_query("SELECT * FROM alerts ORDER BY id", get_conn())


# =====================================================================
# 3. INDICATORS (computed from real OHLCV, no random numbers)
# =====================================================================
def true_range(df):
    pc = df["close"].shift()
    return pd.concat([df["high"] - df["low"],
                      (df["high"] - pc).abs(),
                      (df["low"] - pc).abs()], axis=1).max(axis=1)


def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def adx_di(df, tr, n=14):
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * plus.ewm(alpha=1 / n, adjust=False).mean() / atr
    mdi = 100 * minus.ewm(alpha=1 / n, adjust=False).mean() / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean(), pdi, mdi


def supertrend(df, period=10, mult=3.0):
    atr = true_range(df).ewm(alpha=1 / period, adjust=False).mean().values
    hl2 = ((df["high"] + df["low"]) / 2).values
    basic_ub, basic_lb = hl2 + mult * atr, hl2 - mult * atr
    close = df["close"].values
    n = len(df)
    fub, flb = basic_ub.copy(), basic_lb.copy()
    for i in range(1, n):
        fub[i] = basic_ub[i] if (basic_ub[i] < fub[i - 1] or close[i - 1] > fub[i - 1]) else fub[i - 1]
        flb[i] = basic_lb[i] if (basic_lb[i] > flb[i - 1] or close[i - 1] < flb[i - 1]) else flb[i - 1]
    direction = np.ones(n, dtype=int)
    for i in range(1, n):
        if direction[i - 1] == 1:
            direction[i] = -1 if close[i] < flb[i] else 1
        else:
            direction[i] = 1 if close[i] > fub[i] else -1
    df["ST_LINE"] = np.where(direction == 1, flb, fub)
    df["ST_DIR"] = direction
    return df


def add_indicators(df):
    df = df.copy()
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]

    for s in (9, 21, 50, 200):
        df[f"EMA{s}"] = c.ewm(span=s, adjust=False).mean()

    mid, sd = c.rolling(20).mean(), c.rolling(20).std()
    df["BB_UP"], df["BB_LO"] = mid + 2 * sd, mid - 2 * sd

    df["RSI"] = rsi(c)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    df["MACD"] = macd
    df["MACD_SIG"] = macd.ewm(span=9, adjust=False).mean()
    df["MACD_HIST"] = df["MACD"] - df["MACD_SIG"]

    tr = true_range(df)
    df["ATR"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    adx, dip, dim = adx_di(df, tr)
    df["ADX"], df["DIP"], df["DIM"] = adx, dip, dim

    df = supertrend(df)

    typical = (h + l + c) / 3
    df["VWAP"] = (typical * v).cumsum() / v.cumsum().replace(0, np.nan)
    df["CLOSE_IN_RANGE"] = ((c - l) / (h - l).replace(0, np.nan) * 100).fillna(50).round(1)

    buy = (c > df["EMA21"]) & (df["EMA9"] > df["EMA21"]) & (df["MACD"] > df["MACD_SIG"]) \
          & (df["RSI"] < 70) & (df["ST_DIR"] == 1) & (df["ADX"] > 20)
    sell = (c < df["EMA21"]) & (df["EMA9"] < df["EMA21"]) & (df["MACD"] < df["MACD_SIG"]) \
           & (df["RSI"] > 30) & (df["ST_DIR"] == -1) & (df["ADX"] > 20)
    df["SIGNAL"] = np.select([buy, sell], ["BUY 🟢", "SELL 🔴"], "NEUTRAL 🟡")
    return df


def volume_profile(df, bins=40):
    lo, hi = df["low"].min(), df["high"].max()
    edges = np.linspace(lo, hi, bins + 1)
    mids = (edges[:-1] + edges[1:]) / 2
    typical = ((df["high"] + df["low"] + df["close"]) / 3).values
    idx = np.clip(np.digitize(typical, edges) - 1, 0, bins - 1)
    vols = np.bincount(idx,
