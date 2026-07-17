import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 50% 3%, rgba(0, 245, 255, 0.20), transparent 26%),
                radial-gradient(circle at 88% 14%, rgba(157, 0, 255, 0.24), transparent 30%),
                radial-gradient(circle at 10% 86%, rgba(0, 245, 255, 0.10), transparent 26%),
                linear-gradient(135deg, #020617 0%, #05021f 48%, #090014 100%);
            color: #e5faff;
        }

        [data-testid="stHeader"] {
            background: rgba(2, 6, 23, 0);
        }

        [data-testid="stToolbar"] {
            right: 1rem;
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(7, 12, 45, 0.98), rgba(3, 7, 28, 0.98));
            border-right: 1px solid rgba(0, 245, 255, 0.55);
            box-shadow: 0 0 40px rgba(0, 245, 255, 0.30);
        }

        [data-testid="stSidebar"] * {
            color: #dffcff;
        }

        .block-container {
            max-width: 1240px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        .dimarket-sidebar-item {
            padding: 15px 16px;
            margin: 10px 0;
            border-radius: 16px;
            border: 1px solid rgba(0, 245, 255, 0.10);
            background: rgba(5, 12, 44, 0.42);
            color: #dffcff;
            font-weight: 700;
            box-shadow: inset 0 0 14px rgba(0, 245, 255, 0.04);
        }

        .dimarket-sidebar-item:hover {
            border-color: rgba(0, 245, 255, 0.60);
            box-shadow: 0 0 18px rgba(0, 245, 255, 0.20);
        }

        .hero {
            border: 1px solid rgba(0, 245, 255, 0.62);
            border-radius: 30px;
            padding: 38px 34px;
            margin-bottom: 26px;
            text-align: center;
            background:
                radial-gradient(circle at 50% 4%, rgba(0, 245, 255, 0.30), transparent 30%),
                linear-gradient(135deg, rgba(4, 12, 46, 0.92), rgba(21, 3, 62, 0.76));
            box-shadow:
                0 0 36px rgba(0, 245, 255, 0.44),
                inset 0 0 24px rgba(157, 0, 255, 0.28);
        }

        .hero-title {
            font-size: 60px;
            font-weight: 900;
            color: #ffffff;
            text-shadow:
                0 0 12px rgba(0, 245, 255, 1),
                0 0 34px rgba(157, 0, 255, 0.95);
            margin-bottom: 6px;
        }

        .hero-subtitle {
            color: #b8f7ff;
            font-size: 16px;
            opacity: 0.92;
        }

        .neon-panel {
            border: 1px solid rgba(0, 245, 255, 0.48);
            border-radius: 24px;
            padding: 24px;
            background: rgba(3, 8, 38, 0.82);
            box-shadow:
                0 0 26px rgba(0, 245, 255, 0.24),
                inset 0 0 18px rgba(0, 245, 255, 0.07);
            margin-bottom: 22px;
        }

        .purple-panel {
            border: 1px solid rgba(157, 0, 255, 0.62);
            box-shadow:
                0 0 28px rgba(157, 0, 255, 0.34),
                inset 0 0 20px rgba(157, 0, 255, 0.08);
        }

        .section-title {
            font-size: 27px;
            font-weight: 900;
            color: #ffffff;
            margin-bottom: 18px;
            text-shadow: 0 0 10px rgba(0, 245, 255, 0.72);
        }

        .metric-card {
            border: 1px solid rgba(0, 245, 255, 0.32);
            border-radius: 20px;
            padding: 18px;
            background: rgba(8, 15, 55, 0.86);
            box-shadow: inset 0 0 16px rgba(0, 245, 255, 0.08);
            min-height: 116px;
        }

        .metric-label {
            color: #94dfff;
            font-size: 13px;
            margin-bottom: 8px;
            font-weight: 700;
        }

        .metric-value {
            color: #ffffff;
            font-size: 30px;
            font-weight: 900;
            text-shadow: 0 0 12px rgba(0, 245, 255, 0.48);
        }

        .metric-delta {
            color: #b8f7ff;
            font-size: 13px;
            margin-top: 4px;
        }

        .badge {
            display: inline-block;
            padding: 12px 22px;
            border-radius: 999px;
            font-weight: 950;
            letter-spacing: 1px;
            font-size: 20px;
            text-align: center;
        }

        .badge-buy {
            background: rgba(34, 197, 94, 0.16);
            border: 1px solid rgba(34, 197, 94, 0.82);
            color: #86efac;
            box-shadow: 0 0 22px rgba(34, 197, 94, 0.50);
        }

        .badge-hold {
            background: rgba(250, 204, 21, 0.16);
            border: 1px solid rgba(250, 204, 21, 0.82);
            color: #fde68a;
            box-shadow: 0 0 22px rgba(250, 204, 21, 0.40);
        }

        .badge-reject {
            background: rgba(248, 113, 113, 0.16);
            border: 1px solid rgba(248, 113, 113, 0.82);
            color: #fecaca;
            box-shadow: 0 0 22px rgba(248, 113, 113, 0.40);
        }

        .reason {
            border-left: 3px solid #00f5ff;
            padding: 11px 13px;
            margin-bottom: 9px;
            background: rgba(0, 245, 255, 0.08);
            border-radius: 11px;
            color: #e5faff;
        }

        .warning {
            border-left: 3px solid #facc15;
            padding: 11px 13px;
            margin-bottom: 9px;
            background: rgba(250, 204, 21, 0.08);
            border-radius: 11px;
            color: #fff7d6;
        }

        .mini-copy {
            color: #9bdfff;
            font-size: 13px;
            opacity: 0.90;
        }

        .stButton > button {
            background: linear-gradient(90deg, #00f5ff, #9d00ff);
            color: white;
            border: none;
            border-radius: 13px;
            padding: 0.68rem 1.35rem;
            font-weight: 900;
            box-shadow: 0 0 24px rgba(0, 245, 255, 0.52);
        }

        .stButton > button:hover {
            border: none;
            filter: brightness(1.18);
            box-shadow: 0 0 32px rgba(157, 0, 255, 0.72);
        }

        .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: rgba(7, 12, 45, 0.95) !important;
            color: #ffffff !important;
            border-radius: 13px !important;
        }

        div[data-testid="stMetricValue"] {
            color: #ffffff;
        }

        div[data-testid="stMetricLabel"] {
            color: #b8f7ff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
