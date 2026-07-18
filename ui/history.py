import streamlit as st


def render_historical_confidence(
    historical: dict,
) -> None:
    st.markdown(
        '<div class="neon-panel">',
        unsafe_allow_html=True,
    )

    st.markdown("### Historical Confidence")

    h1, h2, h3, h4, h5 = st.columns(5)

    h1.metric(
        "Accuracy",
        f"{historical.get('accuracy'):.2%}",
    )

    h2.metric(
        "Precision",
        f"{historical.get('precision'):.2%}",
    )

    h3.metric(
        "Recall",
        f"{historical.get('recall'):.2%}",
    )

    h4.metric(
        "F1",
        f"{historical.get('f1'):.2%}",
    )

    h5.metric(
        "AUC",
        f"{historical.get('auc'):.2%}",
    )

    st.caption(
        f"Model version {historical.get('model_version')} · "
        f"Calibration: {historical.get('calibration_method')} · "
        f"Validation rows: {historical.get('validation_rows')}"
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )
