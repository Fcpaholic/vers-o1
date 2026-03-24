"""
Value Bet Tracker — Main Streamlit App
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Bootstrap DB on every cold start
from src.data.db import init_db, get_value_bets, get_stats_summary, settle_bet, is_seeded
from src.data.seeder import run_all_seeds
from src.model.value import run_full_scan, get_pending_bets
from src.alerts.telegram import send_value_bet, send_scan_summary, send_test_message, is_configured
from src.ui.bet_card import render_bet_card, render_settled_row
from config import FOOTBALL_LEAGUES, UNIT_VALUE_EUR, APP_TITLE, CURRENT_SEASON

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme CSS
st.markdown("""
<style>
    body, .stApp { background-color: #0f0f1a; color: #e0e0e0; }
    .stMetric { background: #1e1e2e; border-radius: 8px; padding: 12px; }
    .stButton>button { border-radius: 6px; }
    h1, h2, h3 { color: #c9d1d9; }
    .stExpander { background: #1e1e2e; border: 1px solid #3a3a5c; border-radius: 8px; }
    div[data-testid="stSidebarContent"] { background: #13131f; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background: #1e1e2e; border-radius: 6px 6px 0 0; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Init DB + first-run seed check
# ---------------------------------------------------------------------------
init_db()

def _needs_seed() -> bool:
    """Check if any league has not been seeded yet."""
    for code in FOOTBALL_LEAGUES:
        if not is_seeded(code, CURRENT_SEASON, "football"):
            return True
    if not is_seeded("NBA", "2024", "basketball"):
        return True
    return False


if _needs_seed() and "seeding_done" not in st.session_state:
    with st.spinner("🌱 First run — seeding historical data... (this may take a minute)"):
        progress = st.empty()
        def _cb(msg):
            progress.caption(msg)
        run_all_seeds(progress_callback=_cb)
        progress.empty()
    st.session_state["seeding_done"] = True
    st.success("Historical data loaded.")
else:
    st.session_state.setdefault("seeding_done", True)

# ---------------------------------------------------------------------------
# Settle bets from card buttons
# ---------------------------------------------------------------------------
for key, result in list(st.session_state.items()):
    if key.startswith("settle_") and result in ("WIN", "LOSS", "VOID"):
        bet_id = int(key.split("_")[1])
        bets = get_value_bets()
        matching = [b for b in bets if b["id"] == bet_id]
        if matching:
            b = matching[0]
            if result == "WIN":
                pnl = (b["bookmaker_odds"] - 1) * b["stake_eur"]
            elif result == "LOSS":
                pnl = -b["stake_eur"]
            else:
                pnl = 0.0
            settle_bet(bet_id, result, pnl)
        del st.session_state[key]

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🎯 Value Bet Tracker")
    st.markdown("---")

    st.subheader("🔍 Scan")
    if st.button("Run Full Scan", type="primary", use_container_width=True):
        with st.spinner("Scanning markets..."):
            new_bets = run_full_scan(save=True)
        st.session_state["last_scan_bets"] = new_bets
        if is_configured():
            send_scan_summary(new_bets)
            for b in new_bets:
                send_value_bet(b)
        if new_bets:
            st.success(f"Found {len(new_bets)} value bet(s)!")
        else:
            st.info("No value bets right now.")
        st.rerun()

    st.markdown("---")
    st.subheader("📊 Stats")
    summary = get_stats_summary()
    total = summary.get("total_bets", 0)
    pnl = summary.get("total_pnl", 0) or 0
    wins = summary.get("wins", 0) or 0
    losses = summary.get("losses", 0) or 0
    settled = summary.get("settled", 0) or 0
    staked = summary.get("total_staked", 0) or 0

    st.metric("Total Bets", total)
    st.metric("P&L", f"€{pnl:+.0f}")
    if settled > 0:
        roi = (pnl / staked * 100) if staked else 0
        win_rate = wins / settled * 100 if settled else 0
        st.metric("ROI", f"{roi:+.1f}%")
        st.metric("Win Rate", f"{win_rate:.0f}% ({wins}W/{losses}L)")

    st.markdown("---")
    st.subheader("⚙️ Settings")
    st.caption(f"1u = €{UNIT_VALUE_EUR:.0f} | Max stake: 2u (€{2*UNIT_VALUE_EUR:.0f})")

    if is_configured():
        if st.button("Test Telegram", use_container_width=True):
            ok = send_test_message()
            st.success("Sent!") if ok else st.error("Failed — check token/chat ID")
    else:
        st.warning("Telegram not configured.\nAdd BOT_TOKEN + CHAT_ID to secrets.")

    st.markdown("---")
    st.caption("football-data.org · API-Football · balldontlie · The Odds API")

# ---------------------------------------------------------------------------
# Main tabs
# ---------------------------------------------------------------------------
tab_live, tab_history, tab_analysis = st.tabs(["🔴 Live Bets", "📋 History", "📈 Analysis"])

# ---- LIVE BETS ----
with tab_live:
    st.header("Active Value Bets")

    pending = get_pending_bets()

    if not pending:
        st.info("No pending value bets. Run a scan to find opportunities.")
    else:
        # Filters
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            sports = ["All"] + sorted(set(b["sport"] for b in pending))
            sel_sport = st.selectbox("Sport", sports, key="f_sport")
        with col_f2:
            leagues = ["All"] + sorted(set(b["league"] for b in pending))
            sel_league = st.selectbox("League", leagues, key="f_league")
        with col_f3:
            markets = ["All"] + sorted(set(b["market"] for b in pending))
            sel_market = st.selectbox("Market", markets, key="f_market")

        filtered = pending
        if sel_sport != "All":
            filtered = [b for b in filtered if b["sport"] == sel_sport]
        if sel_league != "All":
            filtered = [b for b in filtered if b["league"] == sel_league]
        if sel_market != "All":
            filtered = [b for b in filtered if b["market"] == sel_market]

        filtered.sort(key=lambda b: b["edge_pct"], reverse=True)

        st.caption(f"Showing {len(filtered)} bet(s) — sorted by edge")

        for i, bet in enumerate(filtered):
            render_bet_card(bet, index=i)

# ---- HISTORY ----
with tab_history:
    st.header("Settled Bets")

    all_bets = get_value_bets()
    settled_bets = [b for b in all_bets if b["status"] == "SETTLED"]

    if not settled_bets:
        st.info("No settled bets yet. Mark bets as Win/Loss from the Live tab.")
    else:
        # Header row
        st.markdown("""
        <div style="display:flex; gap:16px; font-size:0.8em; color:#888; padding:4px 0; border-bottom:1px solid #3a3a5c;">
            <span style="min-width:80px;">Date</span>
            <span style="min-width:180px;">Match</span>
            <span style="min-width:80px;">Pick</span>
            <span style="min-width:50px;">Odds</span>
            <span style="min-width:60px;">Edge</span>
            <span style="min-width:60px;">Conf</span>
            <span style="min-width:40px;">Stake</span>
            <span style="min-width:60px;">Result</span>
            <span>P&L</span>
        </div>
        """, unsafe_allow_html=True)

        for b in settled_bets:
            render_settled_row(b)

        total_pnl = sum(b.get("profit_loss_eur", 0) or 0 for b in settled_bets)
        total_staked = sum(b.get("stake_eur", 0) for b in settled_bets)
        roi = (total_pnl / total_staked * 100) if total_staked else 0
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total P&L", f"€{total_pnl:+.0f}")
        col2.metric("Total Staked", f"€{total_staked:.0f}")
        col3.metric("ROI", f"{roi:+.1f}%")

# ---- ANALYSIS ----
with tab_analysis:
    st.header("Performance Analysis")

    all_bets = get_value_bets()
    settled = [b for b in all_bets if b["status"] == "SETTLED" and b.get("result") in ("WIN", "LOSS")]

    if len(settled) < 2:
        st.info("Not enough settled bets to show analysis yet. Need at least 2 settled results.")
    else:
        # Cumulative P&L chart
        dates = [b["settled_at"][:10] if b.get("settled_at") else b["match_date"] for b in settled]
        pnls = [b.get("profit_loss_eur", 0) or 0 for b in settled]
        cum_pnl = []
        running = 0
        for p in pnls:
            running += p
            cum_pnl.append(running)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=cum_pnl,
            mode="lines+markers",
            name="Cumulative P&L",
            line=dict(color="#00c853" if cum_pnl[-1] >= 0 else "#f44336", width=2),
            fill="tozeroy",
            fillcolor="rgba(0,200,83,0.08)" if cum_pnl[-1] >= 0 else "rgba(244,67,54,0.08)",
        ))
        fig.add_hline(y=0, line_dash="dash", line_color="#666")
        fig.update_layout(
            title="Cumulative P&L (€)",
            paper_bgcolor="#0f0f1a",
            plot_bgcolor="#1e1e2e",
            font=dict(color="#ccc"),
            xaxis=dict(gridcolor="#2a2a3e"),
            yaxis=dict(gridcolor="#2a2a3e"),
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Edge vs result scatter
        edges = [b["edge_pct"] for b in settled]
        results_num = [1 if b["result"] == "WIN" else 0 for b in settled]
        colors = ["#00c853" if r == 1 else "#f44336" for r in results_num]

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=edges, y=results_num,
            mode="markers",
            marker=dict(color=colors, size=10, opacity=0.8),
            text=[f"{b['home_team']} vs {b['away_team']}" for b in settled],
        ))
        fig2.update_layout(
            title="Edge % vs Outcome",
            xaxis_title="Edge (%)",
            yaxis=dict(tickvals=[0, 1], ticktext=["Loss", "Win"]),
            paper_bgcolor="#0f0f1a",
            plot_bgcolor="#1e1e2e",
            font=dict(color="#ccc"),
            xaxis=dict(gridcolor="#2a2a3e"),
            height=280,
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Stats by league
        st.subheader("By League")
        league_data = {}
        for b in settled:
            lg = b["league"]
            if lg not in league_data:
                league_data[lg] = {"bets": 0, "wins": 0, "pnl": 0.0}
            league_data[lg]["bets"] += 1
            if b["result"] == "WIN":
                league_data[lg]["wins"] += 1
            league_data[lg]["pnl"] += b.get("profit_loss_eur", 0) or 0

        rows = []
        for lg, d in league_data.items():
            rows.append({
                "League": lg,
                "Bets": d["bets"],
                "Wins": d["wins"],
                "Win%": f"{d['wins']/d['bets']*100:.0f}%",
                "P&L (€)": f"€{d['pnl']:+.0f}",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
