# sandbox_requests/dynamic_user_requests.py
import streamlit as st

def render_user_sandbox():
    """
    Yeh module user-demand sandbox tab hai jahan aap naye custom features,
    indicators ya tools ke liye live request daal sakte hain.
    """
    st.markdown("""
        <style>
        .sandbox-box {
            background-color: #0E1117;
            border: 2px dashed #00FFCC;
            padding: 20px;
            border-radius: 10px;
            color: #FFFFFF;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🧪 Isolated User-Demand Sandbox")
    st.markdown("Request custom strategies, indicators, or feature additions for your trading terminal.")

    with st.form("sandbox_form"):
        feature_title = st.text_input("Feature Title / Name", placeholder="e.g., Volume Profile Indicator")
        feature_desc = st.text_area("Detailed Requirement / Logic", placeholder="Describe how you want the feature to work...")
        submitted = st.form_submit_button("Submit Request 🚀")

        if submitted:
            if feature_title:
                st.success(f"✅ Success! Request '{feature_title}' has been logged into your sandbox queue.")
            else:
                st.warning("⚠️ Please enter at least a feature title.")
