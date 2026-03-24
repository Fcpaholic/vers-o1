"""
Bet card UI components for Streamlit.
Renders minimal cards (default) with expandable detail.
"""
import streamlit as st


SPORT_EMOJI = {"football": "⚽", "basketball": "🏀"}
LEAGUE_SHORT = {
    "PL": "Premier League", "PD": "La Liga", "BL1": "Bundesliga",
    "SA": "Serie A", "FL1": "Ligue 1", "DED": "Eredivisie",
    "PPL": "Liga Portugal", "BSA": "Belgian Pro League",
    "ELC": "Championship", "NBA": "NBA",
}


def _edge_color(edge_pct: float) -> str:
    if edge_pct >= 10:
        return "#00c853"   # green
    elif edge_pct >= 6:
        return "#ff9800"   # orange
    else:
        return "#64b5f6"   # blue


def _confidence_label(conf: float, dq_flag: bool) -> str:
    label = f"{conf:.1f}%"
    if dq_flag:
        label += " *"
    return label


def render_bet_card(bet: dict, index: int = 0):
    """Render a minimal bet card with an expandable detail section."""
    sport_emoji = SPORT_EMOJI.get(bet["sport"], "🎯")
    league_name = LEAGUE_SHORT.get(bet["league"], bet["league"])
    edge_color = _edge_color(bet["edge_pct"])
    dq_flag = bet.get("data_quality_flag", 0)
    conf_label = _confidence_label(bet["confidence_pct"], bool(dq_flag))
    high_value = bet["stake_units"] >= 2.0

    # --- Minimal card ---
    card_key = f"card_{index}_{bet.get('id', index)}"

    badge = "🔥 HIGH VALUE" if high_value else "✅ VALUE"

    st.markdown(f"""
    <div style="
        background: #1e1e2e;
        border: 1px solid {'#00c853' if high_value else '#3a3a5c'};
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 8px;
    ">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:0.85em; color:#888;">{sport_emoji} {league_name} &nbsp;|&nbsp; {bet['match_date']}</span>
            <span style="font-size:0.8em; color:{'#00c853' if high_value else '#64b5f6'}; font-weight:600;">{badge}</span>
        </div>
        <div style="font-size:1.05em; font-weight:700; margin:6px 0;">
            {bet['home_team']} vs {bet['away_team']}
        </div>
        <div style="display:flex; gap:20px; flex-wrap:wrap; font-size:0.92em;">
            <span><b>{bet['market']}</b> — {bet['selection']}</span>
            <span>Odds: <b>{bet['bookmaker_odds']:.2f}</b></span>
            <span>Fair: <b>{bet['fair_value_odds']:.2f}</b></span>
            <span>Edge: <b style="color:{edge_color}">+{bet['edge_pct']:.1f}%</b></span>
            <span>Conf: <b>{conf_label}</b></span>
            <span>Stake: <b>{bet['stake_units']:.0f}u (€{bet['stake_eur']:.0f})</b></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- Expandable detail ---
    with st.expander("Details", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Bookmaker Odds", f"{bet['bookmaker_odds']:.2f}")
            st.metric("Edge", f"+{bet['edge_pct']:.1f}%")
        with col2:
            st.metric("Fair Value Odds", f"{bet['fair_value_odds']:.2f}")
            st.metric("Confidence", conf_label)
        with col3:
            implied = round(100 / bet['bookmaker_odds'], 1)
            fair_prob = round(100 / bet['fair_value_odds'], 1)
            st.metric("Book Implied Prob", f"{implied:.1f}%")
            st.metric("Model Prob", f"{fair_prob:.1f}%")

        st.markdown(f"**Stake:** {bet['stake_units']:.0f}u = **€{bet['stake_eur']:.0f}**")

        if bet.get("model_factors"):
            st.info(f"📊 {bet['model_factors']}")

        if dq_flag:
            st.warning("\\* Confidence reduced — limited historical data for one or both teams. Bet may still have merit; review manually.")

        if bet.get("status") == "PENDING":
            cols = st.columns([1, 1, 2])
            with cols[0]:
                if st.button("✅ Mark Win", key=f"win_{card_key}"):
                    st.session_state[f"settle_{bet['id']}"] = "WIN"
                    st.rerun()
            with cols[1]:
                if st.button("❌ Mark Loss", key=f"loss_{card_key}"):
                    st.session_state[f"settle_{bet['id']}"] = "LOSS"
                    st.rerun()


def render_settled_row(bet: dict):
    """Compact row for settled bets history."""
    result_color = {"WIN": "#00c853", "LOSS": "#f44336", "VOID": "#888"}.get(bet.get("result", ""), "#888")
    pnl = bet.get("profit_loss_eur", 0) or 0
    pnl_str = f"+€{pnl:.0f}" if pnl >= 0 else f"-€{abs(pnl):.0f}"
    dq = " *" if bet.get("data_quality_flag") else ""

    st.markdown(f"""
    <div style="display:flex; gap:16px; align-items:center; padding:8px 0; border-bottom:1px solid #2a2a3e; font-size:0.88em;">
        <span style="min-width:80px; color:#aaa;">{bet['match_date']}</span>
        <span style="min-width:180px;">{bet['home_team']} vs {bet['away_team']}</span>
        <span style="min-width:80px; color:#ccc;">{bet['selection']}</span>
        <span style="min-width:50px;">{bet['bookmaker_odds']:.2f}</span>
        <span style="min-width:60px; color:#64b5f6;">+{bet['edge_pct']:.1f}%</span>
        <span style="min-width:60px;">{bet['confidence_pct']:.0f}%{dq}</span>
        <span style="min-width:40px;">{bet['stake_units']:.0f}u</span>
        <span style="min-width:60px; color:{result_color}; font-weight:600;">{bet.get('result', '-')}</span>
        <span style="color:{result_color};">{pnl_str}</span>
    </div>
    """, unsafe_allow_html=True)
