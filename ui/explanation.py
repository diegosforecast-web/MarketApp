import streamlit as st


def render_explanation(
    explanation: dict,
) -> None:
    st.markdown(
        '<div class="neon-panel">',
        unsafe_allow_html=True,
    )

    st.markdown("### AI Explanation")

    st.info(
        explanation.get(
            "summary",
            "No explanation available.",
        )
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )
