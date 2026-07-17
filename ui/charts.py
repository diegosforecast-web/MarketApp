import pandas as pd
import streamlit as st


def driver_dataframe(
    items: list[dict],
    negative: bool = False,
) -> pd.DataFrame:
    rows = []

    for item in items:
        impact = float(
            item.get(
                "impact",
                0.0,
            )
        )

        rows.append(
            {
                "Driver": item.get(
                    "display_name",
                    item.get("feature"),
                ),
                "Impact": (
                    abs(impact)
                    if negative
                    else impact
                ),
            }
        )

    return pd.DataFrame(rows)


def render_driver_charts(
    explanation: dict,
) -> None:
    positive = explanation.get(
        "top_positive_features",
        [],
    )

    negative = explanation.get(
        "top_negative_features",
        [],
    )

    pos_df = driver_dataframe(
        positive,
        negative=False,
    )

    neg_df = driver_dataframe(
        negative,
        negative=True,
    )

    st.markdown(
        '<div class="neon-panel purple-panel">',
        unsafe_allow_html=True,
    )

    st.markdown("### Driver Impact")

    pos_col, neg_col = st.columns(2)

    with pos_col:
        st.markdown("#### Supportive Drivers")

        if not pos_df.empty:
            st.bar_chart(
                pos_df.set_index("Driver"),
            )

        with st.expander("Driver details"):
            for item in positive:
                st.write(
                    f"**{item.get('display_name')}**"
                )
                st.caption(
                    item.get(
                        "description",
                        "",
                    )
                )

    with neg_col:
        st.markdown("#### Risk Drivers")

        if not neg_df.empty:
            st.bar_chart(
                neg_df.set_index("Driver"),
            )

        with st.expander("Driver details"):
            for item in negative:
                st.write(
                    f"**{item.get('display_name')}**"
                )
                st.caption(
                    item.get(
                        "description",
                        "",
                    )
                )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )
