import streamlit as st


def fmt_money(value) -> str:
    if value is None:
        return "—"

    return f"${float(value):,.2f}"


def fmt_pct(value) -> str:
    if value is None:
        return "—"

    return f"{float(value):.2f}%"


def recommendation_badge(
    recommendation: str,
) -> str:
    rec = recommendation.upper()

    if rec == "BUY":
        css_class = "badge badge-buy"
    elif rec == "HOLD":
        css_class = "badge badge-hold"
    else:
        css_class = "badge badge-reject"

    return f'<span class="{css_class}">{rec}</span>'


def render_metric_card(
    label: str,
    value: str,
    delta: str = "",
) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-delta">{delta}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_forecast_metrics(
    data: dict,
) -> None:
    recommendation = data.get(
        "recommendation",
        "N/A",
    )

    st.markdown(
        '<div class="neon-panel purple-panel">',
        unsafe_allow_html=True,
    )

    header_left, header_right = st.columns(
        [3, 1],
    )

    with header_left:
        st.markdown(
            f'<div class="section-title">{data.get("ticker")} Forecast</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"Model: {data.get('model')} · Horizon: {data.get('horizon')} trading days"
        )

    with header_right:
        st.markdown(
            recommendation_badge(
                recommendation,
            ),
            unsafe_allow_html=True,
        )

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        render_metric_card(
            "Current Price",
            fmt_money(
                data.get("current_price"),
            ),
        )

    with m2:
        render_metric_card(
            "Forecast Price",
            fmt_money(
                data.get("forecast_price"),
            ),
        )

    with m3:
        render_metric_card(
            "Expected Move",
            fmt_pct(
                data.get("expected_move_pct"),
            ),
        )

    with m4:
        render_metric_card(
            "AI Confidence",
            f'{data.get("confidence")}%',
            data.get(
                "confidence_level",
                "",
            ),
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    reason_col, warning_col = st.columns(2)

    with reason_col:
        st.markdown(
            '<div class="neon-panel">',
            unsafe_allow_html=True,
        )
        st.markdown("### Reasons")

        reasons = data.get(
            "reasons",
            [],
        )

        if reasons:
            for reason in reasons:
                st.markdown(
                    f'<div class="reason">{reason}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.write("No supporting reasons returned.")

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

    with warning_col:
        st.markdown(
            '<div class="neon-panel">',
            unsafe_allow_html=True,
        )
        st.markdown("### Warnings")

        warnings = data.get(
            "warnings",
            [],
        )

        if warnings:
            for warning in warnings:
                st.markdown(
                    f'<div class="warning">{warning}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.write("No warnings returned.")

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )
