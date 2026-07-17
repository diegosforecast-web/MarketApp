import streamlit as st


def render_header() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">DiMarket</div>
            <div class="hero-subtitle">
                Trustworthy AI forecasting for individual investors
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
