# history_archive/archive_manager.py
import streamlit as st
import datetime

def render_history_archive():
    """
    Yeh module permanent yearly historical archive manage karta hai
    jahan aap apne past trades, notes, aur terminal milestones store kar sakte hain.
    """
    st.markdown("### 🏛️ Permanent Yearly Historical Archive")
    st.markdown("Store and review historical trade logs, yearly performance reports, and milestone archives.")

    current_year = datetime.datetime.now().year
    selected_year = st.selectbox("Select Archive Year:", [current_year, current_year - 1, current_year - 2])

    st.info(f"📁 Displaying archived records for the year **{selected_year}**.")
    
    # Sample archive logs
    archive_data = [
        {"date": f"{selected_year}-03-15", "event": "Q1 Crypto Portfolio Rebalancing & Risk Audit", "status": "Archived Successfully"},
        {"date": f"{selected_year}-06-30", "event": "Mid-Year Technical Strategy Review & EMA Opt", "status": "Archived Successfully"}
    ]

    for record in archive_data:
        st.markdown(f"""
            <div style="background-color: #161B22; padding: 12px; border-radius: 6px; border: 1px solid #30363D; margin-bottom: 10px; color: #C9D1D9;">
                <b>📅 {record['date']}</b> | {record['event']} <br>
                <span style="color: #3FB950; font-size: 12px;">● {record['status']}</span>
            </div>
        """, unsafe_allow_html=True)
