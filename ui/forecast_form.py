import streamlit as st


def render_forecast_form():
    left, right = st.columns([1.2, 0.9])

    with left:
        st.markdown(
            '<div class="neon-panel">',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="section-title">🚀 Forecast Input</div>',
            unsafe_allow_html=True,
        )

        with st.form("forecast_form"):
            ticker = st.text_input(
                "Choose ticker",
                value="AAPL",
            )

            horizon = st.selectbox(
                "Select forecast days",
                [1, 2, 3, 4, 5],
                index=4,
            )

            submitted = st.form_submit_button(
                "Run Forecast",
            )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            """
            <div class="neon-panel purple-panel">
                <div class="section-title">🪐 AI Forecast</div>
                <div class="mini-copy">
                    Enter a ticker and generate a calibrated recommendation
                    with explainability, historical confidence, and risk drivers.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return ticker, horizon, submitted
