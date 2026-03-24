"""
Value Bet Tracker — Main Streamlit App (redesigned UI)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.data.db import init_db, get_value_bets, get_stats_summary, settle_bet, is_seeded
from src.data.seeder import run_all_seeds
from src.model.value import run_full_scan, get_pending_bets
from src.alerts.telegram import send_value_bet, send_scan_summary, send_test_message, is_configured
from src.ui.bet_card import render_bet_card, render_settled_row
from config import FOOTBALL_LEAGUES, UNIT_VALUE_EUR, APP_TITLE, CURRENT_SEASON

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Value Bet Tracker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  /* Base */
  .stApp { background:#0d1117; color:#c9d1d9; }
  [data-testid="stSidebar"] { background:#010409; border-right:1px solid #21262d; }
  [data-testid="stSidebar"] * { color:#c9d1d9 !important; }

  /* Hide Streamlit chrome */
  #MainMenu, footer, header { visibility:hidden; }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    gap:0; border-bottom:1px solid #21262d; background:transparent;
  }
  .stTabs [data-baseweb="tab"] {
    background:transparent; border:none; border-bottom:2px solid transparent;
    color:#8b949e; font-size:0.9rem; padding:10px 20px; margin:0;
  }
  .stTabs [aria-selected="true"] {
    background:transparent; border-bottom:2px solid #3fb950 !important;
    color:#c9d1d9 !important;
  }

  /* Metrics */
  [data-testid="stMetric"] {
    background:#161b22; border:1px solid #21262d;
    border-radius:8px; padding:16px !important;
  }
  [data-testid="stMetricLabel"] { color:#8b949e !important; font-size:0.8rem !important; }
  [data-testid="stMetricValue"] { color:#c9d1d9 !important; font-size:1.4rem !important; }

  /* Buttons */
  .stButton > button {
    background:#238636; color:#fff; border:none;
    border-radius:6px; font-weight:600; width:100%;
  }
  .stButton > button:hover { background:#2ea043; }

  /* Expander */
  [data-testid="stExpander"] {
    background:#161b22; border:1px solid #21262d; border-radius:8px;
  }

  /* Dataframe */
  [data-testid="stDataFrame"] { border:1px solid #21262d; border-radius:8px; }

  /* Divider */
  hr { border-color:#21262d; }

  /* Selectbox */
  [data-testid="stSelectbox"] > div > div {
    background:#161b22; border-color:#30363d;
  }

  /* Warning/info/success boxes */
  [data-testid="stAlert"] { border-radius:8px; }
</style>
""", unsafe_allow_html=True)

# ── DB init + first-run seed ──────────────────────────────────────────────────
init_db()

def _needs_seed():
    for code in FOOTBALL_LEAGUES:
        if not is_seeded(code, CURRENT_SEASON, "football"):
            return True
    return not is_seeded("NBA", "2024", "basketball")

if _needs_seed() and "seeding_done" not in st.session_state:
    with st.spinner("Loading historical data for the first time…"):
        run_all_seeds()
    st.session_state["seeding_done"] = True
else:
    st.session_state.setdefault("seeding_done", True)

# ── Settle bets ───────────────────────────────────────────────────────────────
for key, result in list(st.session_state.items()):
    if key.startswith("settle_") and result in ("WIN", "LOSS", "VOID"):
        bet_id = int(key.split("_")[1])
        bets = get_value_bets()
        match = next((b for b in bets if b["id"] == bet_id), None)
        if match:
            pnl = (match["bookmaker_odds"] - 1) * match["stake_eur"] if result == "WIN" else (
                   -match["stake_eur"] if result == "LOSS" else 0.0)
            settle_bet(bet_id, result, pnl)
        del st.session_state[key]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎯 Value Bet Tracker")
    st.markdown("---")

    # Scan button
    if st.button("🔍  Run Full Scan", use_container_width=True):
        with st.spinner("Scanning all markets…"):
            new_bets = run_full_scan(save=True)
        st.session_state["last_scan_bets"] = new_bets
        if is_configured():
            send_scan_summary(new_bets)
            for b in new_bets:
                send_value_bet(b)
        msg = f"✅ {len(new_bets)} value bet(s) found!" if new_bets else "No value bets right now."
        st.session_state["scan_msg"] = (msg, bool(new_bets))
        st.rerun()

    if "scan_msg" in st.session_state:
        msg, ok = st.session_state.pop("scan_msg")
        st.success(msg) if ok else st.info(msg)

    st.markdown("---")

    # Stats
    s = get_stats_summary()
    total   = s.get("total_bets", 0) or 0
    pnl     = s.get("total_pnl", 0) or 0
    settled = s.get("settled", 0) or 0
    wins    = s.get("wins", 0) or 0
    losses  = s.get("losses", 0) or 0
    staked  = s.get("total_staked", 0) or 0

    st.metric("Total bets", total)
    st.metric("P&L", f"€{pnl:+.0f}")
    if settled:
        roi      = pnl / staked * 100 if staked else 0
        win_rate = wins / settled * 100
        st.metric("ROI", f"{roi:+.1f}%")
        st.metric("Win rate", f"{win_rate:.0f}%  ({wins}W / {losses}L)")

    st.markdown("---")
    st.caption(f"1u = €{UNIT_VALUE_EUR:.0f}  ·  Max 2u per bet")

    if is_configured():
        if st.button("📨  Test Telegram", use_container_width=True):
            ok = send_test_message()
            st.success("Sent!") if ok else st.error("Failed — check token/chat ID")
    else:
        st.caption("⚠️ Telegram not set up")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_live, tab_history, tab_analysis, tab_diag = st.tabs([
    "Live Bets", "History", "Analysis", "Diagnostics"
])

# ══════════════════════════════════════════════════════════════════════════════
# LIVE BETS
# ══════════════════════════════════════════════════════════════════════════════
with tab_live:
    pending = get_pending_bets()

    if not pending:
        st.markdown("### Active Value Bets")
        st.info("No pending value bets. Hit **Run Full Scan** in the sidebar.")
    else:
        # Filters row
        c1, c2, c3, _ = st.columns([1, 1, 1, 3])
        sports  = ["All"] + sorted({b["sport"]  for b in pending})
        leagues = ["All"] + sorted({b["league"] for b in pending})
        markets = ["All"] + sorted({b["market"] for b in pending})
        sel_sport  = c1.selectbox("Sport",  sports,  label_visibility="collapsed")
        sel_league = c2.selectbox("League", leagues, label_visibility="collapsed")
        sel_market = c3.selectbox("Market", markets, label_visibility="collapsed")

        filtered = [
            b for b in pending
            if (sel_sport  == "All" or b["sport"]  == sel_sport)
            and (sel_league == "All" or b["league"] == sel_league)
            and (sel_market == "All" or b["market"] == sel_market)
        ]
        filtered.sort(key=lambda b: b["edge_pct"], reverse=True)

        st.markdown(f"**{len(filtered)} bet(s)** · sorted by edge")
        st.markdown("")

        for i, bet in enumerate(filtered):
            render_bet_card(bet, i)

# ══════════════════════════════════════════════════════════════════════════════
# HISTORY
# ══════════════════════════════════════════════════════════════════════════════
with tab_history:
    settled_bets = [b for b in get_value_bets() if b["status"] == "SETTLED"]

    if not settled_bets:
        st.markdown("### Settled Bets")
        st.info("No settled bets yet. Mark bets as Win/Loss from the Live tab.")
    else:
        total_pnl   = sum(b.get("profit_loss_eur", 0) or 0 for b in settled_bets)
        total_staked = sum(b.get("stake_eur", 0) for b in settled_bets)
        roi = total_pnl / total_staked * 100 if total_staked else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Settled bets", len(settled_bets))
        c2.metric("P&L", f"€{total_pnl:+.0f}")
        c3.metric("Total staked", f"€{total_staked:.0f}")
        c4.metric("ROI", f"{roi:+.1f}%")

        st.markdown("---")

        # Header
        st.markdown("""
        <div style="display:grid;grid-template-columns:90px 1fr 100px 60px 70px 60px 50px 70px 70px;
                    gap:8px;padding:6px 12px;font-size:0.75rem;color:#8b949e;border-bottom:1px solid #21262d;">
          <span>DATE</span><span>MATCH</span><span>PICK</span>
          <span>ODDS</span><span>EDGE</span><span>CONF</span>
          <span>STAKE</span><span>RESULT</span><span>P&L</span>
        </div>""", unsafe_allow_html=True)

        for b in settled_bets:
            render_settled_row(b)

# ══════════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab_analysis:
    all_settled = [b for b in get_value_bets()
                   if b["status"] == "SETTLED" and b.get("result") in ("WIN", "LOSS")]

    if len(all_settled) < 2:
        st.markdown("### Performance Analysis")
        st.info("Need at least 2 settled results to show analysis.")
    else:
        pnls    = [b.get("profit_loss_eur", 0) or 0 for b in all_settled]
        dates   = [b.get("settled_at", b["match_date"])[:10] for b in all_settled]
        cum_pnl = []
        total   = 0
        for p in pnls:
            total += p
            cum_pnl.append(total)

        color = "#3fb950" if cum_pnl[-1] >= 0 else "#f85149"

        fig = go.Figure(go.Scatter(
            x=dates, y=cum_pnl, mode="lines+markers",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=f"{'rgba(63,185,80,0.08)' if cum_pnl[-1] >= 0 else 'rgba(248,81,73,0.08)'}",
            marker=dict(size=6),
        ))
        fig.add_hline(y=0, line_dash="dot", line_color="#30363d")
        fig.update_layout(
            title="Cumulative P&L (€)",
            paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
            font=dict(color="#8b949e"),
            xaxis=dict(gridcolor="#21262d", showgrid=True),
            yaxis=dict(gridcolor="#21262d", showgrid=True),
            height=320, margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        # League breakdown
        st.markdown("### By League")
        league_data: dict = {}
        for b in all_settled:
            lg = b["league"]
            d  = league_data.setdefault(lg, {"bets": 0, "wins": 0, "pnl": 0.0})
            d["bets"] += 1
            d["wins"] += int(b["result"] == "WIN")
            d["pnl"]  += b.get("profit_loss_eur", 0) or 0

        rows = [
            {
                "League":   lg,
                "Bets":     d["bets"],
                "W":        d["wins"],
                "L":        d["bets"] - d["wins"],
                "Win %":    f"{d['wins']/d['bets']*100:.0f}%",
                "P&L":      f"€{d['pnl']:+.0f}",
            }
            for lg, d in league_data.items()
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# DIAGNOSTICS
# ══════════════════════════════════════════════════════════════════════════════
with tab_diag:
    st.markdown("### Diagnostics")
    st.caption("Run this to understand why scans return no results.")

    if st.button("▶  Run Diagnostics", use_container_width=False):

        from src.data.fetcher import fetch_football_odds, ODDS_API_FOOTBALL_KEYS
        from src.data.db import get_match_count, get_conn
        from src.model.poisson import expected_goals, outcome_probs
        from config import ODDS_API_KEY, FOOTBALL_DATA_API_KEY

        # 1. Keys
        st.markdown("#### 1 · API Keys")
        c1, c2 = st.columns(2)
        c1.metric("Odds API", "✅ Set" if ODDS_API_KEY else "❌ Missing")
        c2.metric("Football Data", "✅ Set" if FOOTBALL_DATA_API_KEY else "❌ Missing")

        # 2. DB records
        st.markdown("#### 2 · Matches in database")
        db_rows = [
            {"League": code, "Matches": get_match_count(code)}
            for code in FOOTBALL_LEAGUES
        ]
        st.dataframe(pd.DataFrame(db_rows), use_container_width=True, hide_index=True)

        # 3. Odds API live events
        st.markdown("#### 3 · Live events from Odds API")
        odds_rows = []
        sample_event = None
        for code, odds_key in ODDS_API_FOOTBALL_KEYS.items():
            events = fetch_football_odds(odds_key)
            odds_rows.append({"League": code, "Events": len(events)})
            if events and not sample_event:
                sample_event = (code, events[0])
        st.dataframe(pd.DataFrame(odds_rows), use_container_width=True, hide_index=True)

        # 4. Sample prediction
        if sample_event:
            league_code, ev = sample_event
            home = ev.get("home_team", "")
            away = ev.get("away_team", "")

            st.markdown(f"#### 4 · Model prediction — {home} vs {away}")
            eg    = expected_goals(home, away, league_code)
            probs = outcome_probs(eg["lambda_h"], eg["lambda_a"])

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("xG Home",  f"{eg['lambda_h']:.2f}")
            c2.metric("xG Away",  f"{eg['lambda_a']:.2f}")
            c3.metric("P(Home)",  f"{probs['home']*100:.1f}%")
            c4.metric("P(Draw)",  f"{probs['draw']*100:.1f}%")
            c5.metric("P(Away)",  f"{probs['away']*100:.1f}%")

            if eg["data_quality_flag"]:
                st.warning("⚠️ Low data — model using league averages. Team names may not match between Odds API and DB.")

            # Edge table
            st.markdown("#### 5 · Book odds vs model")
            bm_rows = []
            for bm in ev.get("bookmakers", [])[:4]:
                for mkt in bm.get("markets", []):
                    if mkt["key"] == "h2h":
                        for o in mkt["outcomes"]:
                            if o["name"] == home:
                                mp = probs["home"]
                            elif o["name"] == away:
                                mp = probs["away"]
                            else:
                                mp = probs["draw"]
                            fair  = round(1 / mp, 2) if mp > 0 else "-"
                            edge  = round((mp - 1/o["price"]) * 100, 1)
                            bm_rows.append({
                                "Book":      bm["title"],
                                "Pick":      o["name"],
                                "Book odds": o["price"],
                                "Fair odds": fair,
                                "Edge %":    f"{edge:+.1f}%",
                                "Value?":    "✅" if edge > 3 else "—",
                            })
            if bm_rows:
                st.dataframe(pd.DataFrame(bm_rows), use_container_width=True, hide_index=True)

            # Name match
            st.markdown("#### 6 · Team name match in DB")
            conn = get_conn()
            h_match = conn.execute(
                "SELECT name FROM teams WHERE league=? AND name LIKE ?",
                (league_code, f"%{home.split()[0]}%")
            ).fetchall()
            a_match = conn.execute(
                "SELECT name FROM teams WHERE league=? AND name LIKE ?",
                (league_code, f"%{away.split()[0]}%")
            ).fetchall()
            conn.close()
            c1, c2 = st.columns(2)
            c1.write(f"**{home}** → DB: {[r['name'] for r in h_match] or '❌ not found'}")
            c2.write(f"**{away}** → DB: {[r['name'] for r in a_match] or '❌ not found'}")
            if not h_match or not a_match:
                st.error("Team name mismatch — this is why edges aren't found. Model falls back to league averages and the odds look off.")
        else:
            st.warning("No live events returned from Odds API.")
