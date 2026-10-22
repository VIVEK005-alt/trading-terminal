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
HEADERS = {"User-Agent": "apex-terminal/4.0"}
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

LANG_TITLES = {
    "English": "Market Sentiment Matrix",
    "Hinglish": "Market Mood Matrix (Bazaar Mood)",
    "Hindi": "बाज़ार भावना मैट्रिक्स",
}

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
.apex-price {{ font-size: 30px; font-weight: 900; text-shadow: 0 0 8px rgba(38,166,154,0.5); }}
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
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button, .stLinkButton > a {{
    background:{PANEL}; color:{ACCENT} !important; border:1px solid {ACCENT}; border-radius:8px; font-weight:700; }}
.stButton > button:hover, .stFormSubmitButton > button:hover, .stLinkButton > a:hover {{ background:{ACCENT}; color:{BG} !important; }}
[data-testid="stMetric"] {{ background:{PANEL}; border:1px solid #1b2330; border-radius:10px; padding:10px 14px; }}
[data-testid="stMetricValue"] {{ color:{ACCENT} !important; }}
[data-testid="stMetricLabel"] {{ color:{MUTED} !important; }}
[data-testid="stAlert"] {{ background:{PANEL} !important; border:1px solid #1b2330; }}
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. DATABASE (watchlists, alerts, trades, settings — all persisted)
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
# 3. INDICATORS (computed from real OHLCV)
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
    vols = np.bincount(idx, weights=df["volume"].values, minlength=bins)
    return mids, vols


# =====================================================================
# 4. DATA FETCHERS (real APIs only, cached)
# =====================================================================
def _binance_klines(base, tf_key, limit):
    r = requests.get(f"{BINANCE_SPOT}/klines",
                     params={"symbol": f"{base}USDT", "interval": TIMEFRAMES[tf_key][0], "limit": limit},
                     headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    df = pd.DataFrame(r.json()).iloc[:, :6]
    df.columns = ["time", "open", "high", "low", "close", "volume"]
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    return df


def _yahoo_klines(yf_symbol, tf_key, limit):
    _, yf_iv, period, rule = TIMEFRAMES[tf_key]
    h = yf.Ticker(yf_symbol).history(period=period, interval=yf_iv, auto_adjust=False)
    if h is None or h.empty:
        return None
    h = h.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].astype(float)
    idx = h.index
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    h.index = idx
    if rule:
        h = h.resample(rule).agg({"open": "first", "high": "max", "low": "min",
                                  "close": "last", "volume": "sum"}).dropna()
    h.index.name = "time"
    return h.reset_index().tail(limit).reset_index(drop=True)


@st.cache_data(ttl=60, show_spinner=False)
def get_klines(base, tf_key, limit=300):
    """Returns (df_with_indicators, source_label). Binance first, Yahoo fallback."""
    try:
        df = _binance_klines(base, tf_key, limit)
        if df is not None and len(df):
            return add_indicators(df), "LIVE · Binance"
    except Exception:
        pass
    if HAS_YF:
        try:
            df = _yahoo_klines(f"{base}-USD", tf_key, limit)
            if df is not None and len(df):
                return add_indicators(df), "LIVE · Yahoo"
        except Exception:
            pass
    return None, "NO DATA"


@st.cache_data(ttl=15, show_spinner=False)
def get_snapshot(base):
    try:
        r = requests.get(f"{BINANCE_SPOT}/ticker/24hr", params={"symbol": f"{base}USDT"},
                         headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200:
            d = r.json()
            return {"price": float(d["lastPrice"]), "chg": float(d["priceChangePercent"]), "src": "Binance"}
    except Exception:
        pass
    if HAS_YF:
        try:
            fi = yf.Ticker(f"{base}-USD").fast_info
            p, prev = float(fi["last_price"]), float(fi["previous_close"])
            if np.isfinite(p) and np.isfinite(prev) and prev > 0:
                return {"price": p, "chg": (p / prev - 1) * 100, "src": "Yahoo"}
        except Exception:
            pass
    return None


@st.cache_data(ttl=300, show_spinner=False)
def get_universe():
    cols = ["Rank", "Symbol", "Name", "Price (USD)", "Market Cap", "Volume 24h", "24h %"]
    try:
        r = requests.get(f"{COINGECKO}/coins/markets",
                         params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": 150,
                                 "page": 1, "sparkline": "false", "price_change_percentage": "24h"},
                         headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        d = pd.DataFrame(r.json()).drop_duplicates("symbol")
        return pd.DataFrame({
            "Rank": d["market_cap_rank"], "Symbol": d["symbol"].str.upper(), "Name": d["name"],
            "Price (USD)": d["current_price"], "Market Cap": d["market_cap"],
            "Volume 24h": d["total_volume"], "24h %": d["price_change_percentage_24h"],
        }).reset_index(drop=True)
    except Exception:
        return pd.DataFrame(columns=cols)


@st.cache_data(ttl=3600, show_spinner=False)
def get_fx():
    try:
        r = requests.get(FX_URL, params={"from": "USD", "to": "EUR,GBP,INR,JPY"},
                         headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return {"USD": 1.0, "USDT": 1.0, **r.json()["rates"]}
    except Exception:
        return FALLBACK_FX


@st.cache_data(ttl=60, show_spinner=False)
def get_derivatives(base):
    pair = f"{base}USDT"

    def g(url, **params):
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()

    try:
        oi = g(f"{BINANCE_FUT}/fapi/v1/openInterest", symbol=pair)
        pi = g(f"{BINANCE_FUT}/fapi/v1/premiumIndex", symbol=pair)
        ls = g(f"{BINANCE_FUT}/futures/data/globalLongShortAccountRatio", symbol=pair, period="1h", limit=24)
        oh = g(f"{BINANCE_FUT}/futures/data/openInterestHist", symbol=pair, period="1h", limit=24)
    except Exception:
        return None
    oh_df = pd.DataFrame(oh)
    oh_df["time"] = pd.to_datetime(oh_df["timestamp"], unit="ms")
    oh_df["oi_usd"] = oh_df["sumOpenInterestValue"].astype(float)
    return {"oi_coins": float(oi["openInterest"]),
            "funding": float(pi["lastFundingRate"]) * 100,
            "ls": pd.DataFrame(ls), "oih": oh_df}


@st.cache_data(ttl=300, show_spinner=False)
def get_stock(yf_symbol):
    """Daily OHLCV + indicators for NSE/BSE/indices via Yahoo Finance."""
    if not HAS_YF:
        return None
    try:
        h = yf.Ticker(yf_symbol).history(period="1y", interval="1d", auto_adjust=False)
        if h is None or h.empty:
            return None
        h = h.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].astype(float)
        idx = h.index
        if getattr(idx, "tz", None) is not None:
            idx = idx.tz_localize(None)
        h.index = idx
        h.index.name = "time"
        return add_indicators(h.reset_index())
    except Exception:
        return None


# =====================================================================
# 5. HELPERS & CHART BUILDER
# =====================================================================
def parse_base(q):
    s = str(q).upper().replace(" ", "").split("/")[0]
    for suf in ("USDT", "USDC", "USD"):
        if s.endswith(suf) and len(s) > len(suf):
            s = s[: -len(suf)]
            break
    return re.sub(r"[^A-Z0-9]", "", s) or "BTC"


def fmt_money(usd, rate, sym):
    if usd is None or not np.isfinite(usd):
        return "N/A"
    v = usd * rate
    return f"{sym}{v:,.6f}" if abs(v) < 1 else f"{sym}{v:,.2f}"


def color_signal(v):
    s = str(v)
    if "BUY" in s or "BULL" in s or "UP" in s:
        return f"color:{UP};font-weight:700"
    if "SELL" in s or "BEAR" in s or "DOWN" in s:
        return f"color:{DOWN};font-weight:700"
    if "NEUTRAL" in s or "HOLD" in s:
        return f"color:{WARN};font-weight:700"
    return ""


def color_pct(v):
    try:
        return f"color:{UP};font-weight:600" if float(v) >= 0 else f"color:{DOWN};font-weight:600"
    except (TypeError, ValueError):
        return ""


def source_badge(src):
    if src.startswith("LIVE"):
        return f'<span class="badge badge-live">● {src}</span>'
    return f'<span class="badge badge-warn">● {src}</span>'


def build_chart(df, title, overlays, panels, show_vp=False, height=None):
    n = 1 + len(panels)
    heights = [0.6] + [0.4 / len(panels)] * len(panels) if panels else [1.0]
    cols = 2 if show_vp else 1
    kw = {"column_widths": [0.88, 0.12]} if show_vp else {}
    fig = make_subplots(rows=n, cols=cols, shared_xaxes=True, vertical_spacing=0.03,
                        row_heights=heights, horizontal_spacing=0.01, **kw)

    fig.add_trace(go.Candlestick(
        x=df["time"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name=title, increasing_line_color=UP, decreasing_line_color=DOWN,
        increasing_fillcolor=UP, decreasing_fillcolor=DOWN), row=1, col=1)

    ema_cfg = {"EMA 9": ("EMA9", "#f5c542"), "EMA 21": ("EMA21", "#00b0ff"),
               "EMA 50": ("EMA50", "#ff8a65"), "EMA 200": ("EMA200", "#ce93d8")}
    for name, (col, color) in ema_cfg.items():
        if name in overlays:
            fig.add_trace(go.Scatter(x=df["time"], y=df[col], name=name,
                                     line=dict(color=color, width=1.3)), row=1, col=1)

    if "Bollinger" in overlays:
        fig.add_trace(go.Scatter(x=df["time"], y=df["BB_UP"], name="BB Upper",
                                 line=dict(color="#607d8b", width=1, dash="dot")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["BB_LO"], name="BB Lower",
                                 line=dict(color="#607d8b", width=1, dash="dot"),
                                 fill="tonexty", fillcolor="rgba(96,125,139,0.08)"), row=1, col=1)
    if "SuperTrend" in overlays:
        up_line = df["ST_LINE"].where(df["ST_DIR"] == 1)
        dn_line = df["ST_LINE"].where(df["ST_DIR"] == -1)
        fig.add_trace(go.Scatter(x=df["time"], y=up_line, name="SuperTrend ▲",
                                 line=dict(color=UP, width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["time"], y=dn_line, name="SuperTrend ▼",
                                 line=dict(color=DOWN, width=2)), row=1, col=1)
    if "VWAP" in overlays:
        fig.add_trace(go.Scatter(x=df["time"], y=df["VWAP"], name="VWAP",
                                 line=dict(color="#e040fb", width=1.2, dash="dash")), row=1, col=1)

    for r, p in enumerate(panels, start=2):
        if p == "Volume":
            colors = np.where(df["close"] >= df["open"], UP, DOWN).tolist()
            fig.add_trace(go.Bar(x=df["time"], y=df["volume"], marker_color=colors, name="Volume"), row=r, col=1)
        elif p == "RSI":
            fig.add_trace(go.Scatter(x=df["time"], y=df["RSI"], name="RSI 14",
                                     line=dict(color="#ab47bc", width=1.3)), row=r, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color=DOWN, row=r, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color=UP, row=r, col=1)
            fig.update_yaxes(range=[0, 100], row=r, col=1)
        elif p == "MACD":
            hist_colors = np.where(df["MACD_HIST"] >= 0, UP, DOWN).tolist()
            fig.add_trace(go.Bar(x=df["time"], y=df["MACD_HIST"], marker_color=hist_colors, name="Hist"), row=r, col=1)
            fig.add_trace(go.Scatter(x=df["time"], y=df["MACD"], name="MACD",
                                     line=dict(color="#00b0ff", width=1.2)), row=r, col=1)
            fig.add_trace(go.Scatter(x=df["time"], y=df["MACD_SIG"], name="Signal",
                                     line=dict(color="#ff8a65", width=1.2)), row=r, col=1)
        elif p == "ADX":
            fig.add_trace(go.Scatter(x=df["time"], y=df["ADX"], name="ADX",
                                     line=dict(color=ACCENT, width=1.5)), row=r, col=1)
            fig.add_trace(go.Scatter(x=df["time"], y=df["DIP"], name="+DI",
                                     line=dict(color=UP, width=1)), row=r, col=1)
            fig.add_trace(go.Scatter(x=df["time"], y=df["DIM"], name="-DI",
                                     line=dict(color=DOWN, width=1)), row=r, col=1)
            fig.add_hline(y=25, line_dash="dot", line_color=MUTED, row=r, col=1)

    if show_vp:
        mids, vols = volume_profile(df)
        bar_w = (mids[1] - mids[0]) if len(mids) > 1 else 1
        fig.add_trace(go.Bar(x=vols, y=mids, orientation="h", width=bar_w,
                             marker_color="rgba(0,255,204,0.28)", name="Volume Profile"), row=1, col=2)
        fig.update_yaxes(matches="y", row=1, col=2, showticklabels=False, showgrid=False)
        fig.update_xaxes(showticklabels=False, showgrid=False, row=1, col=2)

    fig.update_layout(
        template="plotly_dark", height=height or (600 + 160 * len(panels)),
        paper_bgcolor=BG, plot_bgcolor=BG, xaxis_rangeslider_visible=False,
        hovermode="x unified", dragmode="pan", margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=1.03, x=0),
    )
    fig.update_xaxes(showspikes=True, spikemode="across", spikecolor=MUTED, spikethickness=1, gridcolor=GRID)
    fig.update_yaxes(showspikes=True, spikecolor=MUTED, spikethickness=1, gridcolor=GRID)
    return fig


def tv_widget(symbol, interval, theme, height, uid, studies=None):
    cfg = {
        "autosize": True, "symbol": symbol, "interval": interval, "timezone": "Asia/Kolkata",
        "theme": theme, "style": "1", "locale": "en", "enable_publishing": False,
        "allow_symbol_change": True, "details": True, "hotlist": True,
        "withdateranges": True, "container_id": uid,
        "studies": studies or [],
    }
    return f"""
    <div id="{uid}" style="height:{height}px;width:100%"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>new TradingView.widget({json.dumps(cfg)});</script>
    """


def flash(msg):
    st.session_state["flash"] = msg


def show_flash():
    msg = st.session_state.pop("flash", None)
    if msg:
        st.success(msg)


# =====================================================================
# 6. PAPER TRADING & TAX MATH
# =====================================================================
def compute_portfolio(trades):
    cash, realized, pos = START_CASH, 0.0, {}
    for _, t in trades.iterrows():
        p = pos.get(t["symbol"], {"qty": 0.0, "avg": 0.0})
        if t["side"] == "BUY":
            new_q = p["qty"] + t["qty"]
            p["avg"] = (p["qty"] * p["avg"] + t["qty"] * t["price"]) / new_q
            p["qty"] = new_q
            cash -= t["qty"] * t["price"]
            pos[t["symbol"]] = p
        else:
            sell = min(t["qty"], p["qty"])
            if sell <= 0:
                continue
            realized += (t["price"] - p["avg"]) * sell
            cash += sell * t["price"]
            p["qty"] -= sell
            if p["qty"] <= 1e-12:
                pos.pop(t["symbol"], None)
            else:
                pos[t["symbol"]] = p
    return cash, pos, realized


def fy_label(ts):
    d = pd.to_datetime(ts)
    y = d.year if d.month >= 4 else d.year - 1
    return f"FY {y}-{str(y + 1)[-2:]}"


# =====================================================================
# 7. SIDEBAR (all state persisted in SQLite)
# =====================================================================
get_conn()
universe = get_universe()
universe_syms = universe["Symbol"].tolist() if not universe.empty else sorted(
    {s for v in DEFAULT_PLAYLISTS.values() for s in v})
fx = get_fx()

with st.sidebar:
    st.markdown("## ⚡ APEX CONTROL")

    if st.button("🔄 Refresh all live data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    def persisted_select(label, options, key):
        saved = get_setting(key, options[0])
        idx = options.index(saved) if saved in options else 0

        def _save():
            set_setting(key, st.session_state[f"w_{key}"])

        return st.selectbox(label, options, index=idx, key=f"w_{key}", on_change=_save)

    lang = persisted_select("🌐 Language", list(LANG_TITLES), "language")
    currency = persisted_select("💱 Display currency", list(CURRENCIES), "currency")
    rate, sym = fx.get(currency, 1.0), CURRENCIES[currency]

    st.markdown("---")
    st.subheader("📁 Playlists")
    playlists = load_playlists()
    with st.form("new_playlist", clear_on_submit=True):
        new_name = st.text_input("New playlist name", placeholder="e.g. My Favorites")
        if st.form_submit_button("➕ Create playlist", use_container_width=True):
            name = new_name.strip()[:40]
            if name and name not in playlists:
                create_playlist(name)
                set_setting("active_playlist", name)
                st.rerun()

    names = list(playlists.keys())
    saved_active = get_setting("active_playlist", names[0] if names else "")
    active_pl = st.selectbox("Active playlist", names,
                             index=names.index(saved_active) if saved_active in names else 0,
                             key="active_pl_select")
    set_setting("active_playlist", active_pl)

    coins_now = playlists.get(active_pl, [])

    def _save_coins(pl=active_pl):
        save_playlist_coins(pl, st.session_state[f"coins_{pl}"])

    options = sorted(set(universe_syms) | set(coins_now))
    st.multiselect("Coins in playlist", options, default=coins_now,
                   key=f"coins_{active_pl}", on_change=_save_coins)

    add_sym = st.text_input("Any other symbol", key="add_sym", placeholder="e.g. PEPE")
    if st.button("➕ Add to playlist", use_container_width=True):
        s = parse_base(add_sym) if add_sym.strip() else ""
        if s and s not in coins_now:
            save_playlist_coins(active_pl, coins_now + [s])
            st.session_state.pop(f"coins_{active_pl}", None)
            st.rerun()

    if st.button("🗑️ Delete this playlist", use_container_width=True) and len(names) > 1:
        delete_playlist(active_pl)
        st.rerun()

    st.markdown("---")
    st.subheader("🔔 Price alerts")
    with st.form("alert_form", clear_on_submit=True):
        a_sym = st.text_input("Symbol", value="BTC")
        a_cond = st.selectbox("Condition", ["Above", "Below"])
        a_px = st.number_input("Target price (USD)", min_value=0.0, value=0.0, format="%.6f")
        if st.form_submit_button("Add alert", use_container_width=True) and a_px > 0 and a_sym.strip():
            db_write("INSERT INTO alerts (symbol, cond, price, created_at) VALUES (?, ?, ?, ?)",
                     (parse_base(a_sym), a_cond, a_px, now_iso()))
            st.rerun()

    alerts = load_alerts()
    fired = st.session_state.setdefault("fired_alerts", set())
    for _, al in alerts.iterrows():
        snap = get_snapshot(al["symbol"])
        if snap is None:
            status = "⚠️ no price"
        else:
            hit = snap["price"] >= al["price"] if al["cond"] == "Above" else snap["price"] <= al["price"]
            status = "✅ TRIGGERED" if hit else f"⏳ now {snap['price']:,.4f}"
            if hit and al["id"] not in fired:
                fired.add(al["id"])
                st.toast(f"🔔 {al['symbol']} {al['cond']} {al['price']} ho gaya", icon="🔔")
        c1, c2 = st.columns([4, 1])
        c1.caption(f"{al['symbol']} {al['cond']} {al['price']} → {status}")
        if c2.button("✖", key=f"del_alert_{al['id']}"):
            db_write("DELETE FROM alerts WHERE id = ?", (int(al["id"]),))
            st.rerun()

# =====================================================================
# 8. MAIN HEADER + GLOBAL SEARCH
# =====================================================================
st.session_state.setdefault("global_q", "BTC/USDT")
if "pending_q" in st.session_state:
    st.session_state["global_q"] = st.session_state.pop("pending_q")

st.markdown('<div class="apex-title">⚡ APEX QUANTUM MULTI-TIMEFRAME TERMINAL</div>', unsafe_allow_html=True)
st.markdown('<div class="apex-sub">Live market data • Rule-based signals • Paper trading • Not financial advice</div>',
            unsafe_allow_html=True)

query = st.text_input("🔍 Global search (pair / symbol)", key="global_q", help="Example: ETH/USDT, SOL, DOGE")
base = parse_base(query)


@st.fragment(run_every=20)
def live_bar(coin, rate_, sym_):
    snap = get_snapshot(coin)
    if snap is None:
        st.warning(f"{coin}: live price abhi nahi mil raha.")
        return
    color = UP if snap["chg"] >= 0 else DOWN
    st.markdown(f"""
        <div class="apex-live">
            <div><span style="color:{MUTED};font-size:12px">{coin}/USDT · {snap['src']} · auto-refresh 20s</span><br>
                 <span class="apex-price" style="color:{color}">{fmt_money(snap['price'], rate_, sym_)}</span></div>
            <div><span style="color:{MUTED};font-size:12px">24h change</span><br>
                 <span style="color:{color};font-size:20px;font-weight:700">{snap['chg']:+.2f}%</span></div>
        </div>""", unsafe_allow_html=True)


live_bar(base, rate, sym)

tabs = st.tabs([
    "📊 Master Matrix", "📈 Pro Chart", "🔀 Multi-Timeframe", "📺 TradingView",
    "🐋 Derivatives", "🎮 Paper Trading", "💰 Tax & PnL", "🪙 Token Screener",
    "🇮🇳 NSE / BSE", "🎬 Media",
])

# ---------- TAB 1: MASTER MATRIX ----------
with tabs[0]:
    st.subheader(f"{LANG_TITLES[lang]} — {active_pl}")
    tf_key = st.radio("Timeframe", list(TIMEFRAMES), index=4, horizontal=True, key="mm_tf")
    coins = playlists.get(active_pl, [])
    if not coins:
        st.info("Sidebar me is playlist me coins add karo.")
    else:
        cols = st.columns(min(4, len(coins)))
        rows = []
        for i, coin in enumerate(coins):
            df, src = get_klines(coin, tf_key, 300)
            if df is None:
                rows.append({"Coin": coin, "Price": "N/A", "Chg % (lookback)": None, "RSI": None,
                             "ADX": None, "SuperTrend": "—", "Close in range %": None,
                             "Signal": "NEUTRAL 🟡", "Source": src})
                continue
            last = df.iloc[-1]
            ref = df["close"].iloc[-25] if len(df) > 25 else df["close"].iloc[0]
            chg = (last["close"] / ref - 1) * 100
            with cols[i % len(cols)]:
                st.metric(coin, fmt_money(last["close"], rate, sym), f"{chg:+.2f}%")
                st.markdown(source_badge(src), unsafe_allow_html=True)
            rows.append({
                "Coin": coin, "Price": fmt_money(last["close"], rate, sym),
                "Chg % (lookback)": round(chg, 2), "RSI": round(last["RSI"], 1),
                "ADX": round(last["ADX"], 1), "SuperTrend": "UP 🟢" if last["ST_DIR"] == 1 else "DOWN 🔴",
                "Close in range %": last["CLOSE_IN_RANGE"], "Signal": last["SIGNAL"], "Source": src,
            })

        sig = [r["Signal"] for r in rows]
        b, s_, n_ = sum("BUY" in x for x in sig), sum("SELL" in x for x in sig), sum("NEUTRAL" in x for x in sig)
        m1, m2, m3 = st.columns(3)
        m1.metric("🟢 BUY signals", b)
        m2.metric("🔴 SELL signals", s_)
        m3.metric("🟡 NEUTRAL", n_)

        st.dataframe(
            pd.DataFrame(rows).style.map(color_signal, subset=["Signal", "SuperTrend"])
            .map(color_pct, subset=["Chg % (lookback)"]),
            use_container_width=True, hide_index=True,
        )
    st.caption("Signals = EMA + MACD + RSI + SuperTrend + ADX rules. 'Close in range %' = candle close high-low range me kahan hai.")

# ---------- TAB 2: PRO CHART ----------
with tabs[1]:
    st.subheader(f"📈 {base}/USDT — Pro Chart Studio")
    c1, c2, c3, c4 = st.columns([2, 2, 3, 3])
    tf = c1.selectbox("Timeframe", list(TIMEFRAMES), index=4, key="pc_tf")
    bars = c2.slider("Candles", 100, 500, 250, key="pc_bars")
    overlays = c3.multiselect("Overlays",
                              ["EMA 9", "EMA 21", "EMA 50", "EMA 200", "Bollinger", "SuperTrend", "VWAP"],
                              default=["EMA 21", "EMA 50", "Bollinger", "SuperTrend"], key="pc_ov")
    panels = c4.multiselect("Indicator panels", ["Volume", "RSI", "MACD", "ADX"],
                            default=["Volume", "RSI", "MACD"], key="pc_pn")
    show_vp = st.toggle("Show Volume Profile (right side)", value=True, key="pc_vp")

    df, src = get_klines(base, tf, bars)
    if df is None:
        st.error(f"{base} ka data nahi mila (Binance aur Yahoo dono par). Symbol check karo.")
    else:
        st.markdown(source_badge(src) +
                    f' &nbsp; <a href="https://www.tradingview.com/chart/?symbol=BINANCE:{base}USDT" '
                    f'target="_blank" style="color:{ACCENT}">Open in TradingView ↗</a>',
                    unsafe_allow_html=True)
        fig = build_chart(df, f"{base}/USDT", overlays, panels, show_vp=show_vp)
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displaylogo": False})

        last = df.iloc[-1]
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Last close", fmt_money(last["close"], rate, sym))
        m2.metric("RSI (14)", f"{last['RSI']:.1f}")
        m3.metric("ADX (14)", f"{last['ADX']:.1f}", "Trending" if last["ADX"] > 25 else "Weak trend", delta_color="off")
        m4.metric("ATR (14)", f"{last['ATR']:.4f}")
        m5.metric("SuperTrend", "UP 🟢" if last["ST_DIR"] == 1 else "DOWN 🔴")
        st.markdown(f"**Signal:** {last['SIGNAL']} · **Close in range:** {last['CLOSE_IN_RANGE']:.1f}%")

        with st.expander("📐 Fibonacci retracement (last 100 candles)"):
            hi, lo = df["high"].tail(100).max(), df["low"].tail(100).min()
            levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
            st.dataframe(pd.DataFrame({
                "Level": [f"{x:.3f}" for x in levels],
                "Price": [f"{hi - (hi - lo) * x:,.4f}" for x in levels],
            }), use_container_width=True, hide_index=True)

# ---------- TAB 3: MULTI-TIMEFRAME ----------
with tabs[2]:
    st.subheader(f"🔀 Multi-Timeframe Alignment — {base}/USDT")
    mtf_keys = ["15 Min", "1 Hour", "4 Hour", "1 Day"]
    summary, charts_cols = [], st.columns(2)
    for i, k in enumerate(mtf_keys):
        d, src = get_klines(base, k, 200)
        if d is None:
            summary.append({"Timeframe": k, "Trend": "NO DATA", "Bull checks": "0/4"})
            continue
        last = d.iloc[-1]
        checks = {
            "SuperTrend": last["ST_DIR"] == 1,
            "Close > EMA50": last["close"] > last["EMA50"],
            "MACD > Signal": last["MACD"] > last["MACD_SIG"],
            "+DI > -DI": last["DIP"] > last["DIM"],
        }
        bull = sum(int(v) for v in checks.values())
        summary.append({"Timeframe": k, "Bull checks": f"{bull}/4",
                        "Trend": "BULLISH 🐂" if bull >= 3 else ("BEARISH 🐻" if bull <= 1 else "NEUTRAL 🤖"),
                        "RSI": round(last["RSI"], 1), "ADX": round(last["ADX"], 1), "Source": src})
        with charts_cols[i % 2]:
            fig = build_chart(d.tail(150), k, ["EMA 21", "EMA 50", "SuperTrend"], [], height=340)
            fig.update_layout(title=dict(text=k, font=dict(color=ACCENT)))
            st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})

    st.dataframe(pd.DataFrame(summary).style.map(color_signal, subset=["Trend"]),
                 use_container_width=True, hide_index=True)
    total = sum(int(s["Bull checks"].split("/")[0]) for s in summary)
    maxp = 4 * len(summary)
    pct = total / maxp * 100 if maxp else 0
    verdict = "STRONG BULLISH 🐂" if pct >= 75 else ("BULLISH 🐂" if pct >= 55 else
              ("BEARISH 🐻" if pct <= 30 else "MIXED 🤖"))
    st.markdown(f'<div class="apex-card"><b style="color:{ACCENT}">Overall alignment:</b> '
                f'{total}/{maxp} bullish checks ({pct:.0f}%) → {verdict}</div>',
                unsafe_allow_html=True)

# ---------- TAB 4: TRADINGVIEW ----------
with tabs[3]:
    st.subheader(f"📺 Official TradingView Widget — BINANCE:{base}USDT")
    st.caption("Ye TradingView ka official embed hai. Custom Python indicators yahan inject nahi ho sakte; "
               "custom studies TradingView ke toolbar se add karo.")
    t1, t2 = st.columns(2)
    tv_iv = t1.selectbox("Interval", list(TV_INTERVALS), index=6, key="tv_iv")
    tv_theme = t2.selectbox("Theme", ["dark", "light"], key="tv_theme")
    tv_studies = ["RSI@tv-basicstudies", "MACD@tv-basicstudies", "BB@tv-basicstudies"]
    components.html(tv_widget(f"BINANCE:{base}USDT", TV_INTERVALS[tv_iv], tv_theme, 620, "tv_main", tv_studies),
                    height=640)

    st.markdown("#### 🔀 Multi-timeframe (TradingView)")
    m1, m2, m3 = st.columns(3)
    for col, (lbl, iv) in zip([m1, m2, m3], [("15 Min", "15"), ("1 Hour", "60"), ("4 Hour", "240")]):
        with col:
            st.caption(lbl)
            components.html(tv_widget(f"BINANCE:{base}USDT", iv, tv_theme, 380, f"tv_mtf_{iv}"), height=390)

# ---------- TAB 5: DERIVATIVES ----------
with tabs[4]:
    st.subheader(f"🐋 Derivatives — {base}USDT Futures (Binance)")
    d = get_derivatives(base)
    snap = get_snapshot(base)
    if not d or snap is None:
        st.warning("Futures data load nahi hua. Binance Futures aapke network/region me block ho sakta hai.")
    else:
        last_ls = d["ls"].iloc[-1]
        longs, shorts = float(last_ls["longAccount"]), float(last_ls["shortAccount"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Open Interest", fmt_money(d["oi_coins"] * snap["price"], rate, sym))
        c2.metric("Funding (8h)", f"{d['funding']:+.4f}%",
                  "Longs pay shorts" if d["funding"] > 0 else "Shorts pay longs", delta_color="off")
        c3.metric("Long / Short ratio", f"{float(last_ls['longShortRatio']):.2f}")
        c4.metric("Longs %", f"{longs * 100:.1f}%", f"Shorts {shorts * 100:.1f}%", delta_color="off")

        oih = d["oih"]
        fig = go.Figure(go.Scatter(x=oih["time"], y=oih["oi_usd"] * rate, mode="lines",
                                   line=dict(color=ACCENT, width=2), name="OI"))
        fig.update_layout(template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG, height=320,
                          title=dict(text=f"Open Interest — last 24h ({currency})", font=dict(color=ACCENT)),
                          margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Positive funding = longs, shorts ko pay karte hain (long crowding). Data: Binance public API.")

# ---------- TAB 6: PAPER TRADING ----------
with tabs[5]:
    st.subheader("🎮 Paper Trading (virtual paisa, real prices)")
    show_flash()
    trades = load_trades()
    cash, positions, realized = compute_portfolio(trades)

    mv, unreal = 0.0, 0.0
    for s, p in positions.items():
        sn = get_snapshot(s)
        lp = sn["price"] if sn else p["avg"]
        mv += p["qty"] * lp
        unreal += (lp - p["avg"]) * p["qty"]
    equity = cash + mv

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cash", fmt_money(cash, rate, sym))
    m2.metric("Equity", fmt_money(equity, rate, sym), f"{(equity / START_CASH - 1) * 100:+.2f}% vs start")
    m3.metric("Realized PnL", fmt_money(realized, rate, sym))
    m4.metric("Unrealized PnL", fmt_money(unreal, rate, sym))

    price_now = snap["price"] if snap else None
    st.markdown(f"**{base}/USDT live price:** {fmt_money(price_now, rate, sym) if price_now else 'N/A'}")

    with st.form("order_form"):
        f1, f2 = st.columns(2)
        side = f1.radio("Side", ["BUY", "SELL"], horizontal=True)
        qty = f2.number_input(f"Quantity of {base}", min_value=0.0, value=0.1, format="%.6f")
        submitted = st.form_submit_button("🚀 Execute at market", use_container_width=True)

    if submitted:
        held = positions.get(base, {"qty": 0.0, "avg": 0.0})
        if price_now is None:
            st.error("Live price nahi mila. Order nahi hua.")
        elif qty <= 0:
            st.error("Quantity 0 se zyada honi chahiye.")
        elif side == "BUY" and qty * price_now > cash:
            st.error(f"Virtual cash kam hai. Max BUY qty: {cash / price_now:.6f} {base}")
        elif side == "SELL" and qty > held["qty"] + 1e-12:
            st.error(f"Itne {base} holdings me nahi hain (held: {held['qty']:.6f}).")
        else:
            pnl = (price_now - held["avg"]) * qty if side == "SELL" else 0.0
            add_trade(base, side, qty, price_now, pnl)
            flash(f"{side} {qty} {base} @ ${price_now:,.4f} executed.")
            st.rerun()

    st.markdown("#### 📦 Open positions")
    if positions:
        prow = []
        for s, p in positions.items():
            sn = get_snapshot(s)
            lp = sn["price"] if sn else p["avg"]
            prow.append({"Symbol": s, "Qty": round(p["qty"], 6),
                         "Avg cost (USD)": round(p["avg"], 6), "Last (USD)": round(lp, 6),
                         "Market value": fmt_money(p["qty"] * lp, rate, sym),
                         "Unrealized PnL": round((lp - p["avg"]) * p["qty"] * rate, 2)})
        st.dataframe(pd.DataFrame(prow).style.map(color_pct, subset=["Unrealized PnL"]),
                     use_container_width=True, hide_index=True)
    else:
        st.info("Koi open position nahi hai.")

    st.markdown("#### 🧾 Trade history")
    if not trades.empty:
        st.dataframe(trades.tail(100).iloc[::-1], use_container_width=True, hide_index=True)
    if st.button("🗑️ Reset paper account", use_container_width=True):
        db_write("DELETE FROM trades")
        st.rerun()

# ---------- TAB 7: TAX & PNL ----------
with tabs[6]:
    st.subheader("💰 Paper Trade Tax & PnL Ledger (India style)")
    trades = load_trades()
    if trades.empty:
        st.info("Abhi koi trade nahi hai. Paper Trading tab me trade karo.")
    else:
        sells = trades[trades["side"] == "SELL"].copy()
        sells["FY"] = sells["ts"].apply(fy_label)
        fy = (sells.assign(gain=sells["pnl"].clip(lower=0), loss=sells["pnl"].clip(upper=0))
              .groupby("FY")[["gain", "loss"]].sum().reset_index())
        fy_disp = pd.DataFrame({
            "Financial year": fy["FY"],
            f"Gains ({currency})": fy["gain"] * rate,
            f"Losses ({currency}, no set-off)": fy["loss"] * rate,
            f"Tax @30% + 4% cess ({currency})": fy["gain"] * 0.30 * 1.04 * rate,
        })
        total_gain = fy["gain"].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Total realized PnL", fmt_money(sells["pnl"].sum(), rate, sym))
        m2.metric("Total trades", len(trades))
        m3.metric("Est. tax (30% + cess)", fmt_money(total_gain * 0.30 * 1.04, rate, sym))

        st.markdown("#### Financial-year summary")
        st.dataframe(fy_disp, use_container_width=True, hide_index=True)
        st.warning(
            "⚠️ Ye sirf paper trading ka learning ledger hai, real tax calculation nahi. India me Virtual Digital "
            "Assets (crypto) ke gains par flat 30% tax (Sec 115BBH) + cess lagta hai, crypto losses ko kisi aur income "
            "se set-off nahi kiya ja sakta, aur 1% TDS (Sec 194S) bhi hota hai. Exact filing ke liye CA se milo."
        )
        ledger = trades[["ts", "symbol", "side", "qty", "price", "pnl"]].copy()
        ledger.columns = ["Timestamp (UTC)", "Symbol", "Side", "Qty", "Price (USD)", "PnL (USD)"]
        st.dataframe(ledger, use_container_width=True, hide_index=True)
        st.download_button("📥 Download ledger (CSV)", ledger.to_csv(index=False).encode("utf-8"),
                           file_name="apex_paper_ledger.csv", mime="text/csv", use_container_width=True)

# ---------- TAB 8: TOKEN SCREENER ----------
with tabs[7]:
    st.subheader("🪙 Crypto Token Screener (Top 150 by market cap — live CoinGecko)")
    if universe.empty:
        st.warning("CoinGecko se data nahi aaya (rate limit ho sakta hai). Sidebar se Refresh dabao.")
    else:
        search = st.text_input("🔍 Filter by symbol or name", key="tok_search", placeholder="e.g. PEPE, SOL, Layer")
        view = universe.copy()
        if search:
            mask = view["Symbol"].str.contains(search.upper(), regex=False) | \
                   view["Name"].str.contains(search, case=False, regex=False)
            view = view[mask]
        view["Price (USD)"] = view["Price (USD)"] * rate
        view = view.rename(columns={"Price (USD)": f"Price ({currency})"})
        st.dataframe(
            view.style.format({f"Price ({currency})": "{:,.6g}", "Market Cap": "{:,.0f}",
                               "Volume 24h": "{:,.0f}", "24h %": "{:+.2f}%"}, na_rep="—")
            .map(color_pct, subset=["24h %"]),
            use_container_width=True, hide_index=True, height=520,
        )
        pick_opts = view["Symbol"].tolist() or ["BTC"]
        pick = st.selectbox("Pro Chart me kholne ke liye coin chuno", pick_opts, key="tok_pick")
        if st.button("📈 Open in Pro Chart", use_container_width=True):
            st.session_state["pending_q"] = f"{pick}/USDT"
            st.rerun()
        st.caption("Data: CoinGecko. Price conversion approx hai (Frankfurter/ECB rates).")

# ---------- TAB 9: NSE / BSE ----------
with tabs[8]:
    st.subheader("🇮🇳 NSE / BSE Terminal (INR) — Yahoo Finance data")
    if not HAS_YF:
        st.warning("Indian stocks ke liye requirements.txt me yfinance hona chahiye.")
    else:
        icols = st.columns(4)
        for col, (name, tk) in zip(icols, INDEX_TICKERS.items()):
            ix = get_stock(tk)
            if ix is not None and len(ix) > 1:
                lp, pv = ix["close"].iloc[-1], ix["close"].iloc[-2]
                col.metric(name, f"₹{lp:,.2f}", f"{(lp / pv - 1) * 100:+.2f}%")
            else:
                col.metric(name, "N/A")

        saved_nse = json.loads(get_setting("nse_watch", json.dumps(NSE_DEFAULT)))

        def _save_nse():
            set_setting("nse_watch", json.dumps(st.session_state["nse_ms"]))

        nse_opts = sorted(set(NSE_DEFAULT) | set(saved_nse))
        st.multiselect("NSE/BSE watchlist (saved)", nse_opts, default=saved_nse,
                       key="nse_ms", on_change=_save_nse)

        a1, a2, a3 = st.columns([2, 1, 1])
        new_sym = a1.text_input("Add symbol (e.g. IRCTC, ZOMATO)", key="nse_add").strip().upper()
        exch = a2.selectbox("Exchange", [".NS (NSE)", ".BO (BSE)"], key="nse_ex")
        if a3.button("➕ Add", use_container_width=True) and new_sym:
            full = new_sym + exch.split()[0]
            if full not in saved_nse:
                set_setting("nse_watch", json.dumps(saved_nse + [full]))
                st.rerun()

        rows = []
        with st.spinner("Stock data load ho raha hai..."):
            for full in json.loads(get_setting("nse_watch", json.dumps(NSE_DEFAULT))):
                d = get_stock(full)
                if d is None or len(d) < 2:
                    continue
                last, prev = d.iloc[-1], d.iloc[-2]
                rows.append({
                    "Symbol": full, "LTP (₹)": round(last["close"], 2),
                    "Chg %": round((last["close"] / prev["close"] - 1) * 100, 2),
                    "RSI (14)": round(last["RSI"], 1), "ADX (14)": round(last["ADX"], 1),
                    "SuperTrend": "UP 🟢" if last["ST_DIR"] == 1 else "DOWN 🔴",
                    "Signal": last["SIGNAL"],
                })
        if rows:
            st.dataframe(pd.DataFrame(rows).style.map(color_pct, subset=["Chg %"])
                         .map(color_signal, subset=["SuperTrend", "Signal"]),
                         use_container_width=True, hide_index=True)
        else:
            st.info("Data nahi mila. NSE ka exact symbol check karo.")
        st.caption("Yahoo Finance daily data par signals hain (~15 min delay). Official NSE/BSE API public nahi hai.")

# ---------- TAB 10: MEDIA ----------
with tabs[9]:
    st.subheader("🎬 YouTube Stream")
    url = st.text_input("YouTube video / Shorts / playlist link",
                        value="https://www.youtube.com/watch?v=jNQXAC9IVRw")
    muted = st.toggle("🔇 Mute", value=False)
    vid = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})", url)
    plist = re.search(r"[?&]list=([A-Za-z0-9_-]+)", url)
    if vid:
        src_url = f"https://www.youtube.com/embed/{vid.group(1)}?autoplay=1&mute={int(muted)}"
    elif plist:
        src_url = f"https://www.youtube.com/embed/videoseries?list={plist.group(1)}&autoplay=1&mute={int(muted)}"
    else:
        src_url = None
    if src_url:
        components.html(
            f'<iframe width="100%" height="500" src="{src_url}" frameborder="0" '
            f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
            f'allowfullscreen></iframe>', height=520)
        st.link_button("Open on YouTube ↗", url)
    else:
        st.error("Valid YouTube link paste karo.")
