"""Bet card UI — uses st.html() for reliable rendering (Streamlit >= 1.32)."""
import streamlit as st
import streamlit.components.v1 as components

SPORT_ICON = {"football": "⚽", "basketball": "🏀"}
LEAGUE_NAME = {
    "PL": "Premier League", "PD": "La Liga", "BL1": "Bundesliga",
    "SA": "Serie A", "FL1": "Ligue 1", "DED": "Eredivisie",
    "PPL": "Liga Portugal", "BSA": "Belgian Pro League",
    "ELC": "Championship", "NBA": "NBA",
}


def _html(content: str):
    """Render raw HTML without markdown processing."""
    st.html(content)


def render_bet_card(bet: dict, index: int = 0):
    high    = bet["stake_units"] >= 2.0
    dq      = bool(bet.get("data_quality_flag"))
    league  = LEAGUE_NAME.get(bet["league"], bet["league"])
    icon    = SPORT_ICON.get(bet["sport"], "🎯")
    conf    = f"{bet['confidence_pct']:.0f}%" + (" *" if dq else "")
    edge_c  = "#3fb950" if bet["edge_pct"] >= 10 else ("#d29922" if bet["edge_pct"] >= 6 else "#58a6ff")
    badge   = "🔥 HIGH VALUE · 2u" if high else "✅ VALUE · 1u"
    badge_c = "#d29922" if high else "#3fb950"
    bdr_c   = "#d29922" if high else "#30363d"

    _html(f"""
<div style="background:#161b22;border:1px solid {bdr_c};border-left:3px solid {badge_c};
            border-radius:8px;padding:16px 20px;margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <span style="font-size:0.78rem;color:#8b949e;letter-spacing:0.04em;">
      {icon} {league.upper()} &nbsp;·&nbsp; {bet['match_date']}
    </span>
    <span style="font-size:0.78rem;font-weight:700;color:{badge_c};">{badge}</span>
  </div>
  <div style="font-size:1.1rem;font-weight:700;color:#e6edf3;margin-bottom:14px;">
    {bet['home_team']} <span style="color:#8b949e;font-weight:400;">vs</span> {bet['away_team']}
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:28px;font-size:0.88rem;">
    <div>
      <div style="color:#8b949e;font-size:0.72rem;margin-bottom:3px;">MARKET</div>
      <div style="color:#c9d1d9;font-weight:600;">{bet['market']} — {bet['selection']}</div>
    </div>
    <div>
      <div style="color:#8b949e;font-size:0.72rem;margin-bottom:3px;">ODDS</div>
      <div style="color:#e6edf3;font-weight:700;">{bet['bookmaker_odds']:.2f}</div>
    </div>
    <div>
      <div style="color:#8b949e;font-size:0.72rem;margin-bottom:3px;">FAIR VALUE</div>
      <div style="color:#c9d1d9;">{bet['fair_value_odds']:.2f}</div>
    </div>
    <div>
      <div style="color:#8b949e;font-size:0.72rem;margin-bottom:3px;">EDGE</div>
      <div style="color:{edge_c};font-weight:700;">+{bet['edge_pct']:.1f}%</div>
    </div>
    <div>
      <div style="color:#8b949e;font-size:0.72rem;margin-bottom:3px;">CONFIDENCE</div>
      <div style="color:#c9d1d9;">{conf}</div>
    </div>
    <div>
      <div style="color:#8b949e;font-size:0.72rem;margin-bottom:3px;">STAKE</div>
      <div style="color:#e6edf3;font-weight:700;">€{bet['stake_eur']:.0f}</div>
    </div>
  </div>
</div>
""")

    with st.expander("Detail / Settle", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Book odds",  f"{bet['bookmaker_odds']:.2f}")
        c2.metric("Fair odds",  f"{bet['fair_value_odds']:.2f}")
        c3.metric("Book prob",  f"{100/bet['bookmaker_odds']:.1f}%")
        c4.metric("Model prob", f"{100/bet['fair_value_odds']:.1f}%")

        if bet.get("model_factors"):
            st.markdown(f"> {bet['model_factors']}")
        if dq:
            st.warning("\\* Confidence reduced — limited historical data.")

        if bet.get("status") == "PENDING":
            c1, c2, _ = st.columns([1, 1, 4])
            bid = bet.get("id")
            if c1.button("Win ✅", key=f"w_{index}_{bid}"):
                st.session_state[f"settle_{bid}"] = "WIN"
                st.rerun()
            if c2.button("Loss ❌", key=f"l_{index}_{bid}"):
                st.session_state[f"settle_{bid}"] = "LOSS"
                st.rerun()


def render_settled_row(bet: dict):
    colors  = {"WIN": "#3fb950", "LOSS": "#f85149", "VOID": "#8b949e"}
    result  = bet.get("result", "—")
    color   = colors.get(result, "#8b949e")
    pnl     = bet.get("profit_loss_eur", 0) or 0
    pnl_str = f"+€{pnl:.0f}" if pnl >= 0 else f"-€{abs(pnl):.0f}"
    dq      = " *" if bet.get("data_quality_flag") else ""

    _html(f"""
<div style="display:grid;grid-template-columns:90px 1fr 100px 60px 70px 60px 50px 70px 70px;
            gap:8px;align-items:center;padding:10px 12px;
            border-bottom:1px solid #21262d;font-size:0.85rem;color:#c9d1d9;">
  <span style="color:#8b949e;">{bet['match_date']}</span>
  <span>{bet['home_team']} vs {bet['away_team']}</span>
  <span style="font-weight:600;">{bet['selection']}</span>
  <span>{bet['bookmaker_odds']:.2f}</span>
  <span style="color:#58a6ff;">+{bet['edge_pct']:.1f}%</span>
  <span style="color:#8b949e;">{bet['confidence_pct']:.0f}%{dq}</span>
  <span>{bet['stake_units']:.0f}u</span>
  <span style="color:{color};font-weight:700;">{result}</span>
  <span style="color:{color};">{pnl_str}</span>
</div>
""")
