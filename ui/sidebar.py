from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = ROOT / "logo.png"


def render_sidebar() -> None:
    with st.sidebar:
        if LOGO_PATH.exists():
            st.image(
                str(LOGO_PATH),
                width=150,
            )

        st.markdown("## DiMarket")
        st.markdown("##### Navigation")

        items = [
            "🏠 Home",
            "🤖 AI Forecast",
            "📜 Prediction History",
            "💳 Pricing Plans",
            "👤 My Account",
            "⚙️ Settings",
            "⏻ Logout",
        ]

        for item in items:
            st.markdown(
                f'<div class="dimarket-sidebar-item">{item}</div>',
                unsafe_allow_html=True,
            )

        st.divider()
        st.caption("DiMarket v1 SaaS dashboard")
