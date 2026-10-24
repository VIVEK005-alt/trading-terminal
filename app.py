# --- TAB 2: ADVANCED CHARTS (TradingView Pro Embedded & Pro Layout) ---
with tab2:
    st.subheader("📊 Pro Interactive TradingView Chart & Multi-Indicator Engine")
    st.markdown("""
        <div class="ai-box">
            <b>🤖 Trading Expert AI Insight:</b> Pro TradingView Advanced Workspace with live order book, technical summary, and multi-symbol selectors active.
        </div>
    """, unsafe_allow_html=True)
    
    # Top Control Bar for Advanced Chart
    ac_col1, ac_col2, ac_col3 = st.columns([2, 2, 3])
    with ac_col1:
        t2_symbol = st.selectbox("Select Trading Asset:", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "SUIUSDT", "DOGEUSDT"], index=0, key="t2_sym_select")
    with ac_col2:
        t2_interval = st.selectbox("Default Interval:", ["1", "5", "15", "60", "D", "W"], index=4, key="t2_interval_select")
    with ac_col3:
        st.markdown(f"""
            <div style="padding-top: 28px;">
                <span style="color: #39ff14; font-weight: bold; font-size: 13px;">🟢 BINANCE FEED LIVE | SYMBOL: {t2_symbol}</span>
            </div>
        """, unsafe_allow_html=True)

    t2_tv_symbol = f"BINANCE:{t2_symbol}"
    
    # Advanced TradingView Pro Chart HTML with full height and embedded technical analysis summary
    t2_chart_html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0;background-color:#07090e;">
      <div class="tradingview-widget-container" style="height:620px;width:100%">
        <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
        {{
          "autosize": true,
          "symbol": "{t2_tv_symbol}",
          "interval": "{t2_interval}",
          "timezone": "Etc/UTC",
          "theme": "dark",
          "style": "1",
          "locale": "en",
          "enable_publishing": false,
          "allow_symbol_change": true,
          "watchlist": ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:SOLUSDT", "BINANCE:BNBUSDT", "BINANCE:XRPUSDT"],
          "details": true,
          "hotlist": true,
          "calendar": true,
          "support_host": "https://www.tradingview.com"
        }}
        </script>
      </div>
    </body>
    </html>
    """
    encoded_t2_html = urllib.parse.quote(t2_chart_html)
    st.markdown(f"""
        <div style="width: 100%; height: 640px; border: 2px solid #00ffcc; border-radius: 14px; overflow: hidden; background: #07090e; box-shadow: 0 0 25px rgba(0,255,204,0.2);">
            <iframe src="data:text/html;charset=utf-8,{encoded_t2_html}" width="100%" height="100%" frameborder="0" allowtransparency="true" scrolling="no" allowfullscreen="true" sandbox="allow-scripts allow-same-origin allow-popups"></iframe>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Bottom Pro Widgets side-by-side (Technical Analysis & Market Quotes summary)
    w_col1, w_col2 = st.columns(2)
    with w_col1:
        st.markdown("### 📊 Technical Analysis Summary")
        ta_html = f"""
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js" async>
        {{
          "interval": "1h",
          "width": "100%",
          "isTransparent": true,
          "symbol": "{t2_tv_symbol}",
          "showIntervalTabs": true,
          "locale": "en",
          "colorTheme": "dark"
        }}
        </script>
        """
        st.components.v1.html(ta_html, height=420)

    with w_col2:
        st.markdown("### 🌐 Market Quotes & Overview")
        quote_html = """
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-market-quotes.js" async>
        {
          "width": "100%",
          "height": "420",
          "symbolsGroups": [
            {
              "name": "Crypto",
              "symbols": [
                {"name": "BINANCE:BTCUSDT", "displayName": "Bitcoin"},
                {"name": "BINANCE:ETHUSDT", "displayName": "Ethereum"},
                {"name": "BINANCE:SOLUSDT", "displayName": "Solana"},
                {"name": "BINANCE:BNBUSDT", "displayName": "BNB"},
                {"name": "BINANCE:XRPUSDT", "displayName": "XRP"}
              ]
            }
          ],
          "showSymbolLogo": true,
          "isTransparent": true,
          "locale": "en",
          "colorTheme": "dark"
        }
        </script>
        """
        st.components.v1.html(quote_html, height=420)
