# modules/inshorts_news.py
import streamlit as st

def render_inshorts_news():
    """
    Yeh module 60-word ke crisp InShorts style crypto/trading news updates render karta hai.
    """
    st.markdown("""
        <style>
        .news-card {
            background-color: #161B22;
            border-left: 4px solid #00FFCC;
            padding: 12px 15px;
            border-radius: 6px;
            margin-bottom: 12px;
            color: #E6EDF3;
            font-family: sans-serif;
        }
        .news-title {
            color: #00FFCC;
            font-weight: bold;
            font-size: 15px;
            margin-bottom: 5px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 📰 60-Word Crypto & Market InShorts")
    
    news_list = [
        {
            "title": "Bitcoin Sustains Momentum Above Key Resistance",
            "content": "BTC bulls continue to dominate as trading volumes surge across major derivatives exchanges. Analysts eye new local highs if consolidation holds firm through the weekly close."
        },
        {
            "title": "DeFi Protocols Record Influx of Institutional Liquidity",
            "content": "Total Value Locked (TVL) across leading Layer-1 and Layer-2 networks sees a notable uptick, driven by rising institutional interest and optimized staking yields."
        }
    ]

    for item in news_list:
        st.markdown(f"""
            <div class="news-card">
                <div class="news-title">{item['title']}</div>
                <div style="font-size: 13px; color: #8B949E;">{item['content']}</div>
            </div>
        """, unsafe_allow_html=True)
