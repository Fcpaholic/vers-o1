"""
Value Bet Tracker — Main Streamlit App
Paper trading: scans for value bets, logs them, tracks P&L against a €10k bankroll.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

from src.data.db import init_db, get_value_bets, get_stats_summary, settle_bet, is_seeded
from src.data.seeder import run_all_seeds
from src.model.value import run_full_scan, get_pending_bets
from src.alerts.telegram import send_value_bet, send_scan_summary, send_test_message, is_configured
from src.ui.bet_card import render_bet_card, render_settled_row
from config import (
    FOOTBALL_LEAGUES, UNIT_VALUE_EUR, APP_TITLE, CURRENT_SEASON,
    STARTING_BANKROLL_EUR, ODDS_API_KEY, ODDS_API_BASE, ODDS_REGIONS,
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Value Bet Tracker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .stApp { background:#0d1117; color:#c9d1d9; }
  [data-testid="stSidebar"] { background:#010409; border-right:1px solid #21262d; }
  [data-testid="stSidebar"] * { color:#c9d1d9 !important; }
  #MainMenu, footer, header { visibility:hidden; }

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
  [data-testid="stMetric"] {
    background:#161b22; border:1px solid #21262d;
    border-radius:8px; padding:16px !important;
  }
  [data-testid="stMetricLabel"] { color:#8b949e !important; font-size:0.8rem !important; }
  [data-testid="stMetricValue"] { color:#c9d1d9 !important; font-size:1.4rem !important; }
  .stButton > button {
    background:#238636; color:#fff; border:none;
    border-radius:6px; font-weight:600; width:100%;
  }
  .stButton > button:hover { background:#2ea043; }
  [data-testid="stExpander"] {
    background:#161b22; border:1px solid #21262d; border-radius:8px;
  }
  hr { border-color:#21262d; }
  [data-testid="stSelectbox"] > div > div { background:#161b22; border-color:#30363d; }
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

# ── Settle bets from session state ───────────────────────────────────────────
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

# ── Stats ─────────────────────────────────────────────────────────────────────
s            = get_stats_summary()
total_bets   = s.get("total_bets", 0) or 0
total_pnl    = s.get("total_pnl", 0) or 0
settled      = s.get("settled", 0) or 0
wins         = s.get("wins", 0) or 0
losses       = s.get("losses", 0) or 0
total_staked = s.get("total_staked", 0) or 0
bankroll     = STARTING_BANKROLL_EUR + total_pnl
roi          = total_pnl / total_staked * 100 if total_staked else 0
win_rate     = wins / settled * 100 if settled else 0

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎯 Value Bet Tracker")
    st.caption("Paper trading · €10,000 starting bankroll")
    st.markdown("---")

    # Bankroll highlight
    bk_color = "#3fb950" if bankroll >= STARTING_BANKROLL_EUR else "#f85149"
    pnl_sign  = "+" if total_pnl >= 0 else ""
    st.html(f"""
    <div style="background:#161b22;border:1px solid #21262d;border-radius:8px;
                padding:16px;margin-bottom:12px;">
      <div style="color:#8b949e;font-size:0.75rem;margin-bottom:4px;">BANKROLL</div>
      <div style="color:{bk_color};font-size:1.6rem;font-weight:700;">€{bankroll:,.0f}</div>
      <div style="color:{bk_color};font-size:0.85rem;margin-top:4px;">
        {pnl_sign}€{total_pnl:.0f} P&L &nbsp;·&nbsp; {pnl_sign}{roi:.1f}% ROI
      </div>
    </div>
    """)

    # Scan button
    if st.button("🔍  Run Full Scan", use_container_width=True):
        with st.spinner("Scanning all markets…"):
            new_bets = run_full_scan(save=True)
        st.session_state["last_scan_bets"] = new_bets
        if is_configured():
            send_scan_summary(new_bets)
            for b in new_bets:
                send_value_bet(b)
        msg = f"✅ {len(new_bets)} value bet(s) logged!" if new_bets else "No value bets found right now."
        st.session_state["scan_msg"] = (msg, bool(new_bets))
        st.rerun()

    if "scan_msg" in st.session_state:
        msg, ok = st.session_state.pop("scan_msg")
        st.success(msg) if ok else st.info(msg)

    st.markdown("---")

    # Quick stats
    c1, c2 = st.columns(2)
    c1.metric("Bets logged", total_bets)
    c2.metric("Settled", settled)
    if settled:
        c1, c2 = st.columns(2)
        c1.metric("Wins", wins)
        c2.metric("Losses", losses)
        st.metric("Win rate", f"{win_rate:.0f}%")

    st.markdown("---")
    st.caption(f"1u = €{UNIT_VALUE_EUR:.0f}  ·  Max 2u/bet")

    if is_configured():
        if st.button("📨  Test Telegram", use_container_width=True):
            ok = send_test_message()
            st.success("Sent!") if ok else st.error("Failed")
    else:
        st.caption("⚠️ Telegram not configured")

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
        st.info("No pending value bets. Click **Run Full Scan** in the sidebar to scan all markets.")
        st.caption(
            "The scanner uses the Poisson model against live bookmaker odds. "
            "When edge ≥ 3% it logs the bet here. You then place it manually at the bookmaker."
        )
    else:
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

        st.markdown(f"**{len(filtered)} bet(s)** · sorted by edge  ·  expand each to settle")
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
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Settled", len(settled_bets))
        c2.metric("P&L", f"€{total_pnl:+.0f}")
        c3.metric("Staked", f"€{total_staked:.0f}")
        c4.metric("ROI", f"{roi:+.1f}%")

        st.markdown("---")
        st.html("""
        <div style="display:grid;grid-template-columns:90px 1fr 100px 60px 70px 60px 50px 70px 70px;
                    gap:8px;padding:6px 12px;font-size:0.75rem;color:#8b949e;border-bottom:1px solid #21262d;">
          <span>DATE</span><span>MATCH</span><span>PICK</span>
          <span>ODDS</span><span>EDGE</span><span>CONF</span>
          <span>STAKE</span><span>RESULT</span><span>P&L</span>
        </div>""")

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

        bk_curve = [STARTING_BANKROLL_EUR + c for c in cum_pnl]
        color     = "#3fb950" if cum_pnl[-1] >= 0 else "#f85149"

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates, y=bk_curve, mode="lines+markers", name="Bankroll",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor="rgba(63,185,80,0.06)" if cum_pnl[-1] >= 0 else "rgba(248,81,73,0.06)",
            marker=dict(size=6),
        ))
        fig.add_hline(y=STARTING_BANKROLL_EUR, line_dash="dot", line_color="#30363d",
                      annotation_text="Starting €10k", annotation_font_color="#8b949e")
        fig.update_layout(
            title="Bankroll over time",
            paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
            font=dict(color="#8b949e"),
            xaxis=dict(gridcolor="#21262d"),
            yaxis=dict(gridcolor="#21262d", tickprefix="€"),
            height=320, margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### By League")
        league_data: dict = {}
        for b in all_settled:
            lg = b["league"]
            d  = league_data.setdefault(lg, {"bets": 0, "wins": 0, "pnl": 0.0})
            d["bets"] += 1
            d["wins"] += int(b["result"] == "WIN")
            d["pnl"]  += b.get("profit_loss_eur", 0) or 0
        rows = [
            {"League": lg, "Bets": d["bets"], "W": d["wins"], "L": d["bets"] - d["wins"],
             "Win %": f"{d['wins']/d['bets']*100:.0f}%", "P&L": f"€{d['pnl']:+.0f}"}
            for lg, d in league_data.items()
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# DIAGNOSTICS
# ══════════════════════════════════════════════════════════════════════════════
with tab_diag:
    st.markdown("### Diagnostics")
    st.caption("Understand why scans return no results. Shows raw API responses.")

    if st.button("▶  Run Diagnostics", use_container_width=False):

        from src.data.fetcher import ODDS_API_FOOTBALL_KEYS
        from src.data.db import get_match_count, get_conn
        from src.model.poisson import expected_goals, outcome_probs
        from config import FOOTBALL_DATA_API_KEY

        # 1. Keys
        st.markdown("#### 1 · API Keys")
        c1, c2 = st.columns(2)
        c1.metric("Odds API", "✅ Set" if ODDS_API_KEY else "❌ Missing")
        c2.metric("Football Data", "✅ Set" if FOOTBALL_DATA_API_KEY else "❌ Missing")

        # 2. DB records
        st.markdown("#### 2 · Matches in database")
        db_rows = [{"League": code, "Matches": get_match_count(code)} for code in FOOTBALL_LEAGUES]
        st.dataframe(pd.DataFrame(db_rows), use_container_width=True, hide_index=True)

        # 3. Raw Odds API test — show actual response/error
        st.markdown("#### 3 · Odds API — raw test call (Premier League)")
        test_url = f"{ODDS_API_BASE}/sports/soccer_epl/odds"
        try:
            r = requests.get(test_url, params={
                "apiKey": ODDS_API_KEY,
                "regions": ODDS_REGIONS,
                "markets": "h2h",
                "oddsFormat": "decimal",
            }, timeout=15)
            st.code(f"HTTP {r.status_code}\n\n{r.text[:2000]}", language="json")
            if r.status_code == 200:
                events = r.json() if isinstance(r.json(), list) else []
                st.success(f"✅ {len(events)} events returned")
            elif r.status_code == 401:
                st.error("❌ 401 Unauthorized — check your ODDS_API_KEY secret")
            elif r.status_code == 422:
                st.error("❌ 422 — sport key may be wrong or subscription doesn't include this league")
            elif r.status_code == 429:
                st.error("❌ 429 — quota exceeded. Check your Odds API usage on the-odds-api.com dashboard")
            else:
                st.warning(f"Unexpected status: {r.status_code}")
        except Exception as e:
            st.error(f"Request failed: {e}")

        # 4. All league event counts
        st.markdown("#### 4 · Events per league")
        from src.data.fetcher import fetch_football_odds, fetch_basketball_odds
        odds_rows = []
        sample_event = None
        for code, odds_key in ODDS_API_FOOTBALL_KEYS.items():
            events = fetch_football_odds(odds_key)
            odds_rows.append({"League": code, "Key": odds_key, "Events": len(events)})
            if events and not sample_event:
                sample_event = (code, events[0])

        nba_events = fetch_basketball_odds()
        odds_rows.append({"League": "NBA", "Key": "basketball_nba", "Events": len(nba_events)})
        if nba_events and not sample_event:
            sample_event = ("NBA", nba_events[0])

        st.dataframe(pd.DataFrame(odds_rows), use_container_width=True, hide_index=True)

        # 5. Sample prediction + edge table
        if sample_event:
            league_code, ev = sample_event
            home = ev.get("home_team", "")
            away = ev.get("away_team", "")

            st.markdown(f"#### 5 · Model for: {home} vs {away} ({league_code})")
            if league_code == "NBA":
                st.info("NBA uses a points model — showing bookmaker odds only.")
            else:
                eg    = expected_goals(home, away, league_code)
                probs = outcome_probs(eg["lambda_h"], eg["lambda_a"])

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("xG Home",  f"{eg['lambda_h']:.2f}")
                c2.metric("xG Away",  f"{eg['lambda_a']:.2f}")
                c3.metric("P(Home)",  f"{probs['home']*100:.1f}%")
                c4.metric("P(Draw)",  f"{probs['draw']*100:.1f}%")
                c5.metric("P(Away)",  f"{probs['away']*100:.1f}%")

                if eg.get("data_quality_flag"):
                    st.warning("⚠️ Low data — model using league averages. Team names may not match DB.")

                bm_rows = []
                for bm in ev.get("bookmakers", [])[:4]:
                    for mkt in bm.get("markets", []):
                        if mkt["key"] == "h2h":
                            for o in mkt["outcomes"]:
                                mp    = probs["home"] if o["name"] == home else (
                                        probs["away"] if o["name"] == away else probs["draw"])
                                fair  = round(1 / mp, 2) if mp > 0 else None
                                edge  = round((mp - 1/o["price"]) * 100, 1)
                                bm_rows.append({
                                    "Book": bm["title"], "Pick": o["name"],
                                    "Book odds": o["price"], "Fair odds": fair,
                                    "Edge %": f"{edge:+.1f}%", "Value?": "✅" if edge > 3 else "—",
                                })
                if bm_rows:
                    st.dataframe(pd.DataFrame(bm_rows), use_container_width=True, hide_index=True)

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
                c1.write(f"**{home}** → {[r['name'] for r in h_match] or '❌ not found'}")
                c2.write(f"**{away}** → {[r['name'] for r in a_match] or '❌ not found'}")
                if not h_match or not a_match:
                    st.error("Name mismatch — model falls back to league averages, producing unreliable edges.")
        else:
            st.warning("No live events — all edge detection is blocked. Fix the Odds API issue above.")

        # 6. Available sports on this API key
        st.markdown("#### 7 · All sports available on your API key")
        from src.data.fetcher import fetch_available_sports
        sports_list = fetch_available_sports()
        if sports_list:
            active = [s for s in sports_list if s.get("active")]
            st.caption(f"{len(active)} active sports")
            keys = [s["key"] for s in active if "soccer" in s["key"] or "basketball" in s["key"]]
            st.code("\n".join(keys) or "None matching soccer/basketball")
        else:
            st.error("Could not fetch sports list — likely auth failure")
