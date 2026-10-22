import json
import re
import sqlite3
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

# =====================================================================
# 1. CONFIG
# =====================================================================
st.set_page_config(
    page_title="APEX Quantum Terminal",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded",
)

BINANCE_SPOT = "https://api.binance.com/api/v3"
BINANCE_FUT = "https://fapi.binance.com"
COINGECKO = "https://api.coingecko.com/api/v3"
FX_URL = "https://api.frankfurter.app/latest"
HEADERS = {"User-Agent": "apex-terminal/2.0"}
TIMEOUT = 6
START_CASH = 10_000.0
DB_PATH = "apex_terminal.db"

UP, DOWN = "#26a69a", "#ef5350"

TIMEFRAMES = {
    "1 Min": "1m", "5 Min": "5m", "15 Min": "15m", "30 Min": "30m",
    "1 Hour": "1h", "4 Hour": "4h", "1 Day": "1d", "1 Week": "1w",
}
TV_INTERVALS = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "1h": "60", "4h": "240", "1d": "D", "1w": "W"}
CURRENCIES = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "JPY": "¥", "USDT": "₮"}
FALLBACK_FX = {"USD": 1.0, "EUR": 0.92, "GBP": 0.79, "INR": 83.5, "JPY": 152.5, "USDT": 1.0}

DEFAULT_PLAYLISTS = {
    "Default Watchlist": ["BTC", "ETH", "SOL", "BNB"],
    "Altcoins Pro": ["ADA", "AVAX", "LINK", "SUI", "DOT"],
    "DeFi & Layer1": ["NEAR", "ATOM", "APT", "UNI", "INJ"],
}
DEFAULT_SYMBOLS = sorted({s for v in DEFAULT_PLAYLISTS.values() for s in v} | {"PEPE", "RENDER", "ICP", "TRX"})

INDEX_TICKERS = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN", "INDIA VIX": "^INDIAVIX"}
STOCK_TICKERS = {
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "INFY": "INFY.NS", "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS", "SBIN": "SBIN.NS", "BHARTIARTL": "BHARTIARTL.NS",
    "ITC": "ITC.NS", "TATAMOTORS": "TATAMOTORS.NS", "LT": "LT.NS",
}

LABELS = {
    "English":  {"matrix": "Market Sentiment Matrix", "price": "Live Price", "signal": "Signal"},
    "Hinglish": {"matrix": "Market Sentiment Matrix (Bazaar Mood)", "price": "Live Price", "signal": "Signal"},
    "Hindi":    {"matrix": "बाज़ार भावना मैट्रिक्स", "price": "लाइव कीमत", "signal": "सिग्नल"},
}

# Dark terminal styling
st.markdown("""
<style>
.stApp { background-color: #0b0e11; }
[data-testid="stSidebar"] { background-color: #11151a; border-right: 1px solid #22272e; }
.apex-title { font-family: 'Trebuchet MS', sans-serif; font-weight: 800; font-size: 28px; color: #00ffcc;
              text-shadow: 0 0 8px rgba(0,255,204,0.35); margin-bottom: 4px; }
.apex-sub { color: #8b949e; font-size: 13px; margin-bottom: 12px; }
.badge-live { background:#0f3d2e; color:#26a69a; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
.badge-demo { background:#3d2a0f; color:#ffb300; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. DATABASE (paper trades persist across restarts)
# =====================================================================
@st.cache_resource
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, symbol TEXT, side TEXT, qty REAL, price REAL, pnl REAL
        )
    """)
    conn.commit()
    return conn


def load_trades():
    return pd.read_sql_query("SELECT * FROM trades ORDER BY id", get_db())


def compute_portfolio(trades):
    """Average-cost method. Returns (cash, positions, realized_pnl)."""
    cash, realized = START_CASH, 0.0
    pos = {}
    for t in trades.itertuples():
        cur = pos.get(t.symbol, {"qty": 0.0, "avg": 0.0})
        if t.side == "BUY":
            cash -= t.qty * t.price
            new_qty = cur["qty"] + t.qty
            cur["avg"] = (cur["qty"] * cur["avg"] + t.qty * t.price) / new_qty
            cur["qty"] = new_qty
            pos[t.symbol] = cur
        else:
            sell_q = min(t.qty, cur["qty"])
            realized += (t.price - cur["avg"]) * sell_q
            cash += sell_q * t.price
            cur["qty"] -= sell_q
            if cur["qty"] <= 1e-12:
                pos.pop(t.symbol, None)
            else:
                pos[t.symbol] = cur
    return cash, pos, realized


# =====================================================================
# 3. INDICATORS (all computed for real, no random numbers)
# =====================================================================
def rsi_series(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def supertrend(df, period=10, mult=3.0):
    hl2 = (df["high"] + df["low"]) / 2
    atr = df["ATR"].values
    upper = (hl2 + mult * df["ATR"]).values
    lower = (hl2 - mult * df["ATR"]).values
    close = df["close"].values
    n = len(df)
    fu, fl = upper.copy(), lower.copy()
    for i in range(1, n):
        fu[i] = upper[i] if (upper[i] < fu[i - 1] or close[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lower[i] if (lower[i] > fl[i - 1] or close[i - 1] < fl[i - 1]) else fl[i - 1]
    trend = np.ones(n)
    st_val = np.full(n, np.nan)
    for i in range(1, n):
        if np.isnan(st_val[i - 1]) or st_val[i - 1] == fu[i - 1]:
            trend[i] = -1 if close[i] <= fu[i] else 1
        else:
            trend[i] = 1 if close[i] >= fl[i] else -1
        st_val[i] = fl[i] if trend[i] == 1 else fu[i]
    df["SUPERTREND"] = st_val
    df["ST_DIR"] = trend.astype(int)
    return df


def add_indicators(df):
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]

    for span in (9, 21, 50, 200):
        df[f"EMA{span}"] = c.ewm(span=span, adjust=False).mean()

    mid, sd = c.rolling(20).mean(), c.rolling(20).std()
    df["BB_UP"], df["BB_LO"] = mid + 2 * sd, mid - 2 * sd

    df["RSI"] = rsi_series(c, 14)

    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    sig = macd.ewm(span=9, adjust=False).mean()
    df["MACD"], df["MACD_SIG"], df["MACD_HIST"] = macd, sig, macd - sig

    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1 / 14, adjust=False).mean()

    df = supertrend(df)

    tp = (h + l + c) / 3
    df["VWAP"] = (tp * v).cumsum() / v.cumsum().replace(0, np.nan)

    # Buy pressure = where the candle closed within its range (0% = low, 100% = high)
    rng = (h - l).replace(0, np.nan)
    df["BUY_PCT"] = ((c - l) / rng * 100).fillna(50).round(1)

    buy = (c > df["EMA21"]) & (df["EMA9"] > df["EMA21"]) & (df["MACD"] > df["MACD_SIG"]) \
          & (df["RSI"] < 70) & (df["ST_DIR"] == 1)
    sell = (c < df["EMA21"]) & (df["EMA9"] < df["EMA21"]) & (df["MACD"] < df["MACD_SIG"]) \
           & (df["RSI"] > 30) & (df["ST_DIR"] == -1)
    df["SIGNAL"] = np.select([buy, sell], ["STRONG BUY 🟢", "STRONG SELL 🔴"], "NEUTRAL 🟡")
    return df


# =====================================================================
# 4. DATA FETCHERS (cached, with graceful fallbacks)
# =====================================================================
def demo_klines(base, limit):
    seed = sum(ord(ch) for ch in base)
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, limit)))
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.006, limit))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.006, limit))
    vol = rng.uniform(1e3, 1e4, limit)
    t = pd.date_range(end=pd.Timestamp.now().floor("h"), periods=limit, freq="h")
    df = pd.DataFrame({"time": t, "open": open_, "high": high, "low": low, "close": close, "volume": vol})
    return add_indicators(df)


@st.cache_data(ttl=60, show_spinner=False)
def get_klines(base, interval, limit=300):
    """Returns (df, source_label). source_label is 'LIVE', 'DEMO' or None (not listed)."""
    try:
        r = requests.get(f"{BINANCE_SPOT}/klines",
                         params={"symbol": f"{base}USDT", "interval": interval, "limit": limit},
                         headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException:
        return demo_klines(base, limit), "DEMO"
    if r.status_code != 200:
        return None, "NOT LISTED"
    cols = ["open_time", "open", "high", "low", "close", "volume", "close_time",
            "quote_vol", "trades", "tb_base", "tb_quote", "ignore"]
    df = pd.DataFrame(r.json(), columns=cols)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df["time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df[["time", "open", "high", "low", "close", "volume"]].reset_index(drop=True)
    return add_indicators(df), "LIVE"


@st.cache_data(ttl=10, show_spinner=False)
def get_ticker(base):
    try:
        r = requests.get(f"{BINANCE_SPOT}/ticker/24hr", params={"symbol": f"{base}USDT"},
                         headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        d = r.json()
        return {"price": float(d["lastPrice"]), "chg": float(d["priceChangePercent"]),
                "high": float(d["highPrice"]), "low": float(d["lowPrice"]),
                "vol": float(d["quoteVolume"])}
    except requests.RequestException:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_fx():
    try:
        r = requests.get(FX_URL, params={"from": "USD", "to": "EUR,GBP,INR,JPY"}, timeout=TIMEOUT)
        rates = r.json()["rates"]
        rates["USD"], rates["USDT"] = 1.0, 1.0
        return rates
    except Exception:
        return FALLBACK_FX


@st.cache_data(ttl=300, show_spinner=False)
def get_universe():
    cols = ["Rank", "Symbol", "Name", "Price (USD)", "Market Cap", "Volume 24h", "24h %"]
    try:
        r = requests.get(f"{COINGECKO}/coins/markets",
                         params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": 150,
                                 "page": 1, "sparkline": "false", "price_change_percentage": "24h"},
                         headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        df = pd.DataFrame(r.json())
        df["symbol"] = df["symbol"].str.upper()
        df = df[["market_cap_rank", "symbol", "name", "current_price", "market_cap",
                 "total_volume", "price_change_percentage_24h"]]
        df.columns = cols
        return df
    except Exception:
        return pd.DataFrame(columns=cols)


@st.cache_data(ttl=60, show_spinner=False)
def get_derivatives(base):
    pair = f"{base}USDT"
    try:
        oi = requests.get(f"{BINANCE_FUT}/fapi/v1/openInterest", params={"symbol": pair}, headers=HEADERS, timeout=TIMEOUT)
        pi = requests.get(f"{BINANCE_FUT}/fapi/v1/premiumIndex", params={"symbol": pair}, headers=HEADERS, timeout=TIMEOUT)
        ls = requests.get(f"{BINANCE_FUT}/futures/data/globalLongShortAccountRatio",
                          params={"symbol": pair, "period": "1h", "limit": 24}, headers=HEADERS, timeout=TIMEOUT)
        oih = requests.get(f"{BINANCE_FUT}/futures/data/openInterestHist",
                           params={"symbol": pair, "period": "1h", "limit": 24}, headers=HEADERS, timeout=TIMEOUT)
        if any(x.status_code != 200 for x in (oi, pi, ls, oih)):
            return None
        oih_df = pd.DataFrame(oih.json())
        oih_df["time"] = pd.to_datetime(oih_df["timestamp"].astype(float), unit="ms")
        oih_df["oi_usd"] = oih_df["sumOpenInterestValue"].astype(float)
        return {
            "oi_coins": float(oi.json()["openInterest"]),
            "funding": float(pi.json()["lastFundingRate"]) * 100,
            "ls": pd.DataFrame(ls.json()),
            "oih": oih_df,
        }
    except requests.RequestException:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def get_yf_quote(ticker):
    if not HAS_YF:
        return None
    try:
        h = yf.Ticker(ticker).history(period="1y", interval="1d")
        if h.empty:
            return None
        c = h["Close"].astype(float)
        last = c.iloc[-1]
        prev = c.iloc[-2] if len(c) > 1 else last
        rsi = float(rsi_series(c).iloc[-1])
        ma50 = float(c.rolling(50).mean().iloc[-1])
        if last > ma50 and rsi > 50:
            trend = "BULLISH 🐂"
        elif last < ma50 and rsi < 50:
            trend = "BEARISH 🐻"
        else:
            trend = "NEUTRAL 🤖"
        return {"price": float(last), "chg": float((last / prev - 1) * 100), "rsi": rsi, "trend": trend}
    except Exception:
        return None


# =====================================================================
# 5. HELPERS
# =====================================================================
def fmt_money(usd, rate, sym):
    v = usd * rate
    return f"{sym}{v:,.6f}" if abs(v) < 1 else f"{sym}{v:,.2f}"


def color_signal(v):
    s = str(v)
    if "BUY" in s or "BULL" in s:
        return "color:#26a69a;font-weight:700"
    if "SELL" in s or "BEAR" in s:
        return "color:#ef5350;font-weight:700"
    if "NEUTRAL" in s or "HOLD" in s:
        return "color:#ffb300;font-weight:700"
    return ""


def color_pct(v):
    try:
        return "color:#26a69a;font-weight:600" if float(v) >= 0 else "color:#ef5350;font-weight:600"
    except (TypeError, ValueError):
        return ""


def source_badge(src):
    if src == "LIVE":
        return '<span class="badge-live">● LIVE Binance</span>'
    if src == "DEMO":
        return '<span class="badge-demo">● DEMO data (internet/API issue)</span>'
    return '<span class="badge-demo">● Not listed on Binance</span>'


def build_chart(df, title, overlays, panels):
    n = 1 + len(panels)
    heights = [0.6] + [0.4 / len(panels)] * len(panels) if panels else [1.0]
    fig = make_subplots(rows=n, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=heights)

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
        fig.add_trace(go.Scatter(x=df["time"], y=df["SUPERTREND"], name="SuperTrend",
                                 line=dict(color="#00ffcc", width=1.5)), row=1, col=1)
    if "VWAP" in overlays:
        fig.add_trace(go.Scatter(x=df["time"], y=df["VWAP"], name="VWAP",
                                 line=dict(color="#e040fb", width=1.2, dash="dash")), row=1, col=1)

    row = 2
    for p in panels:
        if p == "Volume":
            colors = np.where(df["close"] >= df["open"], UP, DOWN).tolist()
            fig.add_trace(go.Bar(x=df["time"], y=df["volume"], marker_color=colors, name="Volume"), row=row, col=1)
        elif p == "RSI":
            fig.add_trace(go.Scatter(x=df["time"], y=df["RSI"], name="RSI 14",
                                     line=dict(color="#ab47bc", width=1.3)), row=row, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color=DOWN, row=row, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color=UP, row=row, col=1)
            fig.update_yaxes(range=[0, 100], row=row, col=1)
        elif p == "MACD":
            hist_colors = np.where(df["MACD_HIST"] >= 0, UP, DOWN).tolist()
            fig.add_trace(go.Bar(x=df["time"], y=df["MACD_HIST"], marker_color=hist_colors, name="Hist"), row=row, col=1)
            fig.add_trace(go.Scatter(x=df["time"], y=df["MACD"], name="MACD", line=dict(color="#00b0ff", width=1.2)), row=row, col=1)
            fig.add_trace(go.Scatter(x=df["time"], y=df["MACD_SIG"], name="Signal", line=dict(color="#ff8a65", width=1.2)), row=row, col=1)
        row += 1

    fig.update_layout(
        template="plotly_dark", height=620 + 170 * len(panels),
        paper_bgcolor="#0b0e11", plot_bgcolor="#0b0e11",
        xaxis_rangeslider_visible=False, hovermode="x unified",
        margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=1.02, x=0),
    )
    fig.update_xaxes(showspikes=True, spikemode="across", spikesnap="cursor", spikethickness=1, spikecolor="#888")
    fig.update_yaxes(showspikes=True, spikethickness=1, spikecolor="#888", gridcolor="#1e2530")
    return fig


# =====================================================================
# 6. SIDEBAR
# =====================================================================
if "playlists" not in st.session_state:
    st.session_state.playlists = {k: list(v) for k, v in DEFAULT_PLAYLISTS.items()}
if "alerts" not in st.session_state:
    st.session_state.alerts = []
playlists = st.session_state.playlists

universe = get_universe()
universe_syms = universe["Symbol"].tolist() if not universe.empty else DEFAULT_SYMBOLS

with st.sidebar:
    st.markdown("## ⚡ APEX CONTROL")
    lang_name = st.selectbox("🌐 Language", list(LABELS.keys()))
    L = LABELS[lang_name]
    currency = st.selectbox("💱 Display Currency", list(CURRENCIES.keys()))

    st.markdown("---")
    st.subheader("📁 Playlists")
    new_name = st.text_input("New playlist name", key="new_pl", placeholder="e.g. My Favorites")
    if st.button("➕ Create playlist", use_container_width=True):
        name = new_name.strip()
        if name and name not in playlists:
            playlists[name] = ["BTC", "ETH"]
            st.rerun()
    active_pl = st.selectbox("Active playlist", list(playlists.keys()))
    all_opts = sorted(set(universe_syms) | set(playlists[active_pl]))
    playlists[active_pl] = st.multiselect("Coins in playlist", all_opts, default=playlists[active_pl])

    st.markdown("---")
    st.subheader("🔔 Price Alerts")
    a_sym = st.text_input("Symbol", value="BTC", key="alert_sym").strip().upper()
    a_cond = st.selectbox("Condition", ["Above", "Below"])
    a_price = st.number_input("Target price (USD)", min_value=0.0, value=0.0, format="%.6f")
    if st.button("Add alert", use_container_width=True) and a_price > 0 and a_sym:
        st.session_state.alerts.append({"sym": a_sym, "cond": a_cond, "price": a_price})
        st.rerun()
    for i, al in enumerate(st.session_state.alerts):
        tk = get_ticker(al["sym"])
        if tk is None:
            status = "⚠️ no price"
        else:
            hit = tk["price"] >= al["price"] if al["cond"] == "Above" else tk["price"] <= al["price"]
            status = "✅ TRIGGERED" if hit else f"⏳ now ${tk['price']:,.4f}"
        st.caption(f"{al['sym']} {al['cond']} {al['price']} → {status}")
    if st.session_state.alerts and st.button("Clear alerts", use_container_width=True):
        st.session_state.alerts = []
        st.rerun()

fx = get_fx()
rate = fx.get(currency, 1.0)
sym = CURRENCIES[currency]

# =====================================================================
# 7. GLOBAL SEARCH + TABS
# =====================================================================
st.markdown('<div class="apex-title">⚡ APEX QUANTUM MULTI-TIMEFRAME TERMINAL</div>', unsafe_allow_html=True)
st.markdown('<div class="apex-sub">Real market data • Rule-based signals • Paper trading • Not financial advice</div>',
            unsafe_allow_html=True)

query = st.text_input("🔍 Global search (symbol / pair)", value="BTC/USDT", help="Example: ETH/USDT, SOL, DOGE")
base = query.upper().strip().split("/")[0]
if base.endswith("USDT") and len(base) > 4:
    base = base[:-4]
base = base or "BTC"

tabs = st.tabs([
    "📊 Master Matrix", "📈 Pro Chart", "📺 TradingView Widget", "🐋 Derivatives",
    "🎮 Paper Trading", "💰 Tax & PnL", "🪙 Token Screener", "🇮🇳 Indian Stocks", "🎬 Media",
])

# ---------- TAB 1: MASTER MATRIX ----------
with tabs[0]:
    st.subheader(f"{L['matrix']} — {active_pl}")
    tf_label = st.radio("Timeframe", list(TIMEFRAMES.keys()), index=4, horizontal=True)
    interval = TIMEFRAMES[tf_label]

    coins = playlists[active_pl]
    if not coins:
        st.info("Sidebar se is playlist me coins add karo.")
    else:
        cols = st.columns(min(4, len(coins)))
        rows = []
        for i, coin in enumerate(coins):
            df, src = get_klines(coin, interval, 300)
            col = cols[i % len(cols)]
            if df is None:
                col.warning(f"{coin}: Binance par listed nahi")
                continue
            last = df.iloc[-1]
            chg = (last["close"] / df["close"].iloc[-25] - 1) * 100 if len(df) > 25 else 0.0
            col.metric(coin, fmt_money(last["close"], rate, sym), f"{chg:+.2f}%")
            col.markdown(f"**{last['SIGNAL']}**  ·  Buy pressure {last['BUY_PCT']:.1f}%  ·  RSI {last['RSI']:.1f}")
            col.markdown(source_badge(src), unsafe_allow_html=True)
            rows.append({
                "Coin": coin, L["price"]: fmt_money(last["close"], rate, sym),
                "24-bar %": round(chg, 2), "RSI": round(last["RSI"], 1),
                "MACD": round(last["MACD"], 4), "SuperTrend": "UP 🟢" if last["ST_DIR"] == 1 else "DOWN 🔴",
                L["signal"]: last["SIGNAL"], "Buy %": last["BUY_PCT"],
            })
        if rows:
            st.dataframe(pd.DataFrame(rows).style.map(color_signal, subset=[L["signal"], "SuperTrend"]),
                         use_container_width=True, height=min(480, 60 + 36 * len(rows)))
    st.caption("Signals rule-based hain (EMA + MACD + RSI + SuperTrend). Ye financial advice nahi hai.")

# ---------- TAB 2: PRO CHART ----------
with tabs[1]:
    st.subheader(f"📈 {base}/USDT — Pro Chart Studio")
    c1, c2, c3, c4 = st.columns([2, 2, 3, 3])
    tf = c1.selectbox("Timeframe", list(TIMEFRAMES.keys()), index=4, key="pc_tf")
    bars = c2.slider("Candles", 100, 500, 250, key="pc_bars")
    overlays = c3.multiselect("Overlays", ["EMA 9", "EMA 21", "EMA 50", "EMA 200", "Bollinger", "SuperTrend", "VWAP"],
                              default=["EMA 21", "EMA 50", "Bollinger", "SuperTrend"], key="pc_ov")
    panels = c4.multiselect("Indicator panels", ["Volume", "RSI", "MACD"], default=["Volume", "RSI", "MACD"], key="pc_pn")

    df, src = get_klines(base, TIMEFRAMES[tf], bars)
    if df is None:
        st.error(f"{base} Binance par listed nahi hai. TradingView widget tab try karo ya koi aur coin chuno.")
    else:
        st.markdown(source_badge(src), unsafe_allow_html=True)
        fig = build_chart(df, f"{base}/USDT", overlays, panels)
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True, "displaylogo": False})

        last = df.iloc[-1]
        ticker = get_ticker(base)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Last price", fmt_money(last["close"], rate, sym), f"{ticker['chg']:+.2f}% (24h)" if ticker else None)
        m2.metric("RSI (14)", f"{last['RSI']:.1f}")
        m3.metric("MACD hist", f"{last['MACD_HIST']:.4f}")
        m4.metric("ATR (14)", f"{last['ATR']:.4f}")
        m5.metric("SuperTrend", "UP 🟢" if last["ST_DIR"] == 1 else "DOWN 🔴")

        st.markdown(f"**Signal:** {last['SIGNAL']}  ·  **Buy pressure:** {last['BUY_PCT']:.1f}%")

        with st.expander("📐 Fibonacci retracement (last 100 candles)"):
            hi, lo = df["high"].tail(100).max(), df["low"].tail(100).min()
            levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
            fib_df = pd.DataFrame({"Level": [f"{x:.3f}" for x in levels],
                                   "Price": [f"{hi - (hi - lo) * x:,.4f}" for x in levels]})
            st.dataframe(fib_df, use_container_width=True, hide_index=True)

# ---------- TAB 3: TRADINGVIEW WIDGET ----------
with tabs[2]:
    st.subheader(f"📺 Official TradingView Widget — BINANCE:{base}USDT")
    tc1, tc2 = st.columns(2)
    tv_iv = tc1.selectbox("Interval", list(TV_INTERVALS.keys()), index=6, key="tv_iv")
    tv_theme = tc2.selectbox("Theme", ["dark", "light"], key="tv_theme")
    config = {
        "autosize": True, "symbol": f"BINANCE:{base}USDT", "interval": TV_INTERVALS[tv_iv],
        "timezone": "Asia/Kolkata", "theme": tv_theme, "style": "1", "locale": "en",
        "toolbar_bg": "#0b0e11" if tv_theme == "dark" else "#ffffff",
        "enable_publishing": False, "allow_symbol_change": True, "hide_side_toolbar": False,
        "withdateranges": True, "details": True, "hotlist": True,
        "studies": ["RSI@tv-basicstudies", "MACD@tv-basicstudies", "BB@tv-basicstudies"],
        "container_id": "tv_chart",
    }
    html = f"""
    <div id="tv_chart" style="height:100%;width:100%"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>new TradingView.widget({json.dumps(config)});</script>
    """
    components.html(html, height=720)

# ---------- TAB 4: DERIVATIVES ----------
with tabs[3]:
    st.subheader(f"🐋 Derivatives — {base}USDT Futures (Binance)")
    d = get_derivatives(base)
    if not d:
        st.warning("Futures data load nahi hua. Binance Futures aapke network/region me block ho sakta hai.")
    else:
        t = get_ticker(base)
        price = t["price"] if t else 0.0
        last_ls = d["ls"].iloc[-1]
        longs, shorts = float(last_ls["longAccount"]), float(last_ls["shortAccount"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Open Interest", fmt_money(d["oi_coins"] * price, rate, sym))
        c2.metric("Funding Rate (8h)", f"{d['funding']:+.4f}%")
        c3.metric("Long / Short Ratio", f"{float(last_ls['longShortRatio']):.2f}")
        c4.metric("Longs %", f"{longs * 100:.1f}%", f"Shorts {shorts * 100:.1f}%", delta_color="off")

        oih = d["oih"]
        fig = go.Figure(go.Scatter(x=oih["time"], y=oih["oi_usd"] * rate, mode="lines",
                                   line=dict(color="#00ffcc", width=2), name="OI"))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0b0e11", plot_bgcolor="#0b0e11",
                          height=320, title=f"Open Interest — last 24h ({currency})", margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Funding positive = longs shorts ko pay karte hain (bullish crowding). Data Binance public API se.")

# ---------- TAB 5: PAPER TRADING ----------
with tabs[4]:
    st.subheader("🎮 Paper Trading (virtual paisa, real prices)")
    conn = get_db()
    trades = load_trades()
    cash, positions, realized = compute_portfolio(trades)

    mv, unreal = 0.0, 0.0
    for s, p in positions.items():
        tk = get_ticker(s)
        last_px = tk["price"] if tk else p["avg"]
        mv += p["qty"] * last_px
        unreal += (last_px - p["avg"]) * p["qty"]
    equity = cash + mv

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cash", fmt_money(cash, rate, sym))
    m2.metric("Equity", fmt_money(equity, rate, sym), f"{(equity / START_CASH - 1) * 100:+.2f}% vs start")
    m3.metric("Realized PnL", fmt_money(realized, rate, sym))
    m4.metric("Unrealized PnL", fmt_money(unreal, rate, sym))

    ticker = get_ticker(base)
    price = ticker["price"] if ticker else None
    st.markdown(f"**{base}/USDT live price:** {fmt_money(price, rate, sym) if price else 'N/A'}")

    with st.form("order_form", clear_on_submit=False):
        f1, f2 = st.columns(2)
        side = f1.radio("Side", ["BUY", "SELL"], horizontal=True)
        qty = f2.number_input(f"Quantity of {base}", min_value=0.0, value=0.1, format="%.6f")
        submitted = st.form_submit_button("🚀 Execute at market", use_container_width=True)

    if submitted:
        held = positions.get(base, {"qty": 0.0, "avg": 0.0})
        if price is None:
            st.error("Live price nahi mila. Order nahi hua.")
        elif qty <= 0:
            st.error("Quantity 0 se zyada honi chahiye.")
        elif side == "BUY" and qty * price > cash:
            st.error("Virtual cash kam hai.")
        elif side == "SELL" and qty > held["qty"] + 1e-12:
            st.error(f"Itne {base} holdings me nahi hain (held: {held['qty']:.6f}).")
        else:
            pnl = (price - held["avg"]) * qty if side == "SELL" else 0.0
            conn.execute("INSERT INTO trades (ts, symbol, side, qty, price, pnl) VALUES (?,?,?,?,?,?)",
                         (datetime.now(timezone.utc).isoformat(timespec="seconds"), base, side, qty, price, pnl))
            conn.commit()
            st.success(f"{side} {qty} {base} @ ${price:,.4f} executed.")
            st.rerun()

    st.markdown("#### 📦 Open Positions")
    if positions:
        prow = []
        for s, p in positions.items():
            tk = get_ticker(s)
            lp = tk["price"] if tk else p["avg"]
            prow.append({"Symbol": s, "Qty": round(p["qty"], 6), "Avg cost": fmt_money(p["avg"], rate, sym),
                         "Last": fmt_money(lp, rate, sym), "Market value": fmt_money(p["qty"] * lp, rate, sym),
                         "Unrealized PnL": round((lp - p["avg"]) * p["qty"] * rate, 2)})
        st.dataframe(pd.DataFrame(prow).style.map(lambda v: color_pct(v), subset=["Unrealized PnL"]),
                     use_container_width=True, hide_index=True)
    else:
        st.info("Koi open position nahi hai.")

    st.markdown("#### 🧾 Trade History")
    if not trades.empty:
        st.dataframe(trades.tail(50).iloc[::-1], use_container_width=True, hide_index=True)
    if st.button("🗑️ Reset paper account", use_container_width=True):
        conn.execute("DELETE FROM trades")
        conn.commit()
        st.rerun()

# ---------- TAB 6: TAX & PNL ----------
with tabs[5]:
    st.subheader("💰 Paper Trade Tax & PnL Ledger")
    trades = load_trades()
    if trades.empty:
        st.info("Abhi koi trade nahi hai. Paper Trading tab me trade karo.")
    else:
        trades["date"] = pd.to_datetime(trades["ts"])
        trades["FY"] = trades["date"].apply(
            lambda d: f"FY {d.year}-{str(d.year + 1)[-2:]}" if d.month >= 4 else f"FY {d.year - 1}-{str(d.year)[-2:]}")
        sells = trades[trades["side"] == "SELL"]

        fy_sum = sells.groupby("FY")["pnl"].sum().reset_index().rename(columns={"pnl": "Net PnL (USD)"})
        fy_sum["Net PnL (" + currency + ")"] = fy_sum["Net PnL (USD)"] * rate
        fy_sum["Est. tax @30% (on gains)"] = fy_sum["Net PnL (USD)"].clip(lower=0) * 0.30 * rate

        m1, m2, m3 = st.columns(3)
        m1.metric("Total realized PnL", fmt_money(sells["pnl"].sum(), rate, sym))
        m2.metric("Total trades", len(trades))
        m3.metric("Est. tax (30% on gains)", fmt_money(fy_sum["Net PnL (USD)"].clip(lower=0).sum() * 0.30, rate, sym))

        st.markdown("#### Financial-year summary")
        st.dataframe(fy_sum.style.map(color_pct, subset=["Net PnL (USD)"]), use_container_width=True, hide_index=True)

        st.warning(
            "⚠️ Ye sirf paper trading ka learning ledger hai, real tax calculation nahi. "
            "India me Virtual Digital Assets (crypto) ke gains par flat 30% tax (Sec 115BBH) aur 1% TDS (Sec 194S) lagta hai, "
            "aur crypto losses ko kisi aur income se set-off nahi kiya ja sakta. Exact filing ke liye CA se milo."
        )

        ledger = trades[["ts", "symbol", "side", "qty", "price", "pnl"]].copy()
        ledger["pnl_display"] = ledger["pnl"] * rate
        ledger.columns = ["Timestamp (UTC)", "Symbol", "Side", "Qty", "Price (USD)", "PnL (USD)", f"PnL ({currency})"]
        st.dataframe(ledger, use_container_width=True, hide_index=True)
        st.download_button("📥 Download ledger (CSV)", ledger.to_csv(index=False).encode("utf-8"),
                           file_name="apex_paper_ledger.csv", mime="text/csv", use_container_width=True)

# ---------- TAB 7: TOKEN SCREENER ----------
with tabs[6]:
    st.subheader("🪙 Crypto Token Screener (Top 150 by market cap)")
    if universe.empty:
        st.warning("CoinGecko se data nahi aaya. Thodi der baad Refresh karo.")
    else:
        search = st.text_input("🔍 Filter by symbol or name", key="tok_search", placeholder="e.g. PEPE, SOL, Layer")
        view = universe.copy()
        if search:
            mask = view["Symbol"].str.contains(search.upper()) | view["Name"].str.contains(search, case=False)
            view = view[mask]
        view["Price (USD)"] = view["Price (USD)"] * rate
        view = view.rename(columns={"Price (USD)": f"Price ({currency})"})
        st.dataframe(
            view.style.format({f"Price ({currency})": "{:,.6g}", "Market Cap": "{:,.0f}",
                               "Volume 24h": "{:,.0f}", "24h %": "{:+.2f}%"}, na_rep="—")
                .map(color_pct, subset=["24h %"]),
            use_container_width=True, hide_index=True, height=520,
        )
        st.caption("Data: CoinGecko. Price conversion approx hai (frankfurter/ECB rates).")

# ---------- TAB 8: INDIAN STOCKS ----------
with tabs[7]:
    st.subheader("🇮🇳 NSE / BSE Market Terminal (INR)")
    if not HAS_YF:
        st.warning("Indian stocks ke liye run karo: `pip install yfinance`")
    else:
        cols = st.columns(4)
        for col, (name, tk_sym) in zip(cols, INDEX_TICKERS.items()):
            q = get_yf_quote(tk_sym)
            if q:
                col.metric(name, f"₹{q['price']:,.2f}", f"{q['chg']:+.2f}%")
            else:
                col.metric(name, "N/A")

        extra = st.text_input("➕ Add any NSE symbol (e.g. IRCTC, ZOMATO)", key="nse_add").strip().upper()
        stock_map = dict(STOCK_TICKERS)
        if extra:
            stock_map[extra] = f"{extra}.NS"

        rows = []
        with st.spinner("NSE data load ho raha hai..."):
            for name, tk_sym in stock_map.items():
                q = get_yf_quote(tk_sym)
                if q:
                    rows.append({"Symbol": name, "LTP (₹)": round(q["price"], 2), "Change %": round(q["chg"], 2),
                                 "RSI (14)": round(q["rsi"], 1), "Trend": q["trend"]})
        if rows:
            idf = pd.DataFrame(rows)
            st.dataframe(idf.style.map(color_pct, subset=["Change %"]).map(color_signal, subset=["Trend"]),
                         use_container_width=True, hide_index=True)
        else:
            st.info("Data nahi mila. Symbol check karo (NSE ka exact symbol likho).")
        st.caption("Data: Yahoo Finance (yfinance), ~15 min delay ho sakta hai. Educational use only.")

# ---------- TAB 9: MEDIA ----------
with tabs[8]:
    st.subheader("🎬 YouTube Stream")
    url = st.text_input("Paste YouTube video / Shorts / playlist link",
                        value="https://www.youtube.com/watch?v=jNQXAC9IVRw")
    muted = st.toggle("🔇 Mute", value=False)
    vid = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})", url)
    plist = re.search(r"[?&]list=([A-Za-z0-9_-]+)", url)
    src = None
    if vid:
        src = f"https://www.youtube.com/embed/{vid.group(1)}?autoplay=1&mute={int(muted)}"
    elif plist:
        src = f"https://www.youtube.com/embed/videoseries?list={plist.group(1)}&autoplay=1&mute={int(muted)}"
    if src:
        components.html(
            f'<iframe width="100%" height="500" src="{src}" frameborder="0" '
            f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
            f'allowfullscreen></iframe>', height=520)
        st.link_button("Open on YouTube ↗", url)
    else:
        st.error("Valid YouTube link paste karo.")
