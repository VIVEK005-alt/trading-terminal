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
FALLBACK_FX = {"USD": 1.0, "USDT": 1.0, "EUR": 0.92,
