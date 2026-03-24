"""
Value bet detection engine.
Combines model probabilities, bookmaker odds, Kelly staking, and confidence scoring
to produce a list of value bet recommendations.
"""
from datetime import datetime
from src.model.poisson import expected_goals, outcome_probs, over_under_probs, btts_prob, model_factors_text as football_factors
from src.model.basketball import expected_points, win_probs, model_factors_text as nba_factors
from src.model.kelly import fair_value_odds, recommended_stake, implied_prob
from src.data.fetcher import (
    fetch_football_odds, fetch_basketball_odds,
    get_best_odds, ODDS_API_FOOTBALL_KEYS
)
from src.data.db import save_value_bet, get_value_bets
from config import (
    MIN_EDGE_PCT, MIN_CONFIDENCE_PCT, CURRENT_SEASON,
    FOOTBALL_LEAGUES
)


BASE_CONFIDENCE = 75.0  # Base model confidence before adjustments


def _edge(model_prob: float, book_odds: float) -> float:
    """Edge = model_prob - implied_prob(book_odds)."""
    if not book_odds or book_odds <= 1.0:
        return 0.0
    return model_prob - implied_prob(book_odds)


def _confidence(base: float, dq_penalty: float) -> tuple[float, bool]:
    """
    Apply data quality penalty to confidence.
    Returns (confidence_pct, data_quality_flag).
    """
    conf = base * (1 - dq_penalty)
    return round(max(0.0, min(conf, 99.0)), 1), dq_penalty > 0


# ---------------------------------------------------------------------------
# Football value bets
# ---------------------------------------------------------------------------

def scan_football_league(league_code: str, save: bool = True) -> list[dict]:
    """
    Scan a football league for value bets using current odds.
    Returns list of value bet dicts.
    """
    odds_key = ODDS_API_FOOTBALL_KEYS.get(league_code)
    if not odds_key:
        return []

    events = fetch_football_odds(odds_key)
    found = []

    for event in events:
        home = event.get("home_team", "")
        away = event.get("away_team", "")
        commence = event.get("commence_time", "")
        if not home or not away:
            continue

        # Get model expected goals
        eg = expected_goals(home, away, league_code, CURRENT_SEASON)
        lh, la = eg["lambda_h"], eg["lambda_a"]
        dq_penalty = eg["confidence_penalty"]

        # Outcome probs
        probs = outcome_probs(lh, la)
        ou_25 = over_under_probs(lh, la, 2.5)
        btts = btts_prob(lh, la)

        factors = football_factors(home, away, eg)
        best = get_best_odds(event, "h2h")
        ou_odds = get_best_odds(event, "totals")

        # Check 1X2 markets
        for side, model_prob, book_key in [
            ("Home", probs["home"], "home"),
            ("Draw", probs["draw"], "draw"),
            ("Away", probs["away"], "away"),
        ]:
            book_odd = best["best"].get(book_key)
            if not book_odd:
                continue
            edge = _edge(model_prob, book_odd)
            if edge < MIN_EDGE_PCT:
                continue

            conf, dq_flag = _confidence(BASE_CONFIDENCE, dq_penalty)
            if conf < MIN_CONFIDENCE_PCT:
                continue

            fv = fair_value_odds(model_prob)
            edge_pct = round(edge * 100, 2)
            units, eur = recommended_stake(edge)

            bet = {
                "sport": "football",
                "league": league_code,
                "match_date": commence[:10] if commence else "",
                "home_team": home,
                "away_team": away,
                "market": "1X2",
                "selection": side,
                "bookmaker_odds": book_odd,
                "fair_value_odds": fv,
                "edge_pct": edge_pct,
                "confidence_pct": conf,
                "data_quality_flag": dq_flag,
                "stake_units": units,
                "stake_eur": eur,
                "model_factors": factors,
                "status": "PENDING",
            }
            found.append(bet)
            if save:
                save_value_bet(bet)

        # Check Over 2.5
        over_book = ou_odds["best"].get("home") or ou_odds["best"].get("Over 2.5")
        if over_book and _edge(ou_25["over"], over_book) >= MIN_EDGE_PCT:
            edge = _edge(ou_25["over"], over_book)
            conf, dq_flag = _confidence(BASE_CONFIDENCE, dq_penalty)
            if conf >= MIN_CONFIDENCE_PCT:
                fv = fair_value_odds(ou_25["over"])
                units, eur = recommended_stake(edge)
                bet = {
                    "sport": "football",
                    "league": league_code,
                    "match_date": commence[:10] if commence else "",
                    "home_team": home,
                    "away_team": away,
                    "market": "Over/Under",
                    "selection": "Over 2.5",
                    "bookmaker_odds": over_book,
                    "fair_value_odds": fv,
                    "edge_pct": round(edge * 100, 2),
                    "confidence_pct": conf,
                    "data_quality_flag": dq_flag,
                    "stake_units": units,
                    "stake_eur": eur,
                    "model_factors": factors,
                    "status": "PENDING",
                }
                found.append(bet)
                if save:
                    save_value_bet(bet)

    return found


def scan_all_football(save: bool = True) -> list[dict]:
    all_bets = []
    for code in FOOTBALL_LEAGUES:
        bets = scan_football_league(code, save=save)
        all_bets.extend(bets)
    return all_bets


# ---------------------------------------------------------------------------
# Basketball value bets
# ---------------------------------------------------------------------------

def scan_basketball(save: bool = True) -> list[dict]:
    events = fetch_basketball_odds()
    found = []

    for event in events:
        home = event.get("home_team", "")
        away = event.get("away_team", "")
        commence = event.get("commence_time", "")
        if not home or not away:
            continue

        ep = expected_points(home, away, CURRENT_SEASON)
        wp = win_probs(ep["exp_home_pts"], ep["exp_away_pts"])
        dq_penalty = ep["confidence_penalty"]
        factors = nba_factors(home, away, ep)

        best = get_best_odds(event, "h2h")

        for side, model_prob, book_key in [
            (home, wp["home"], "home"),
            (away, wp["away"], "away"),
        ]:
            book_odd = best["best"].get(book_key)
            if not book_odd:
                continue
            edge = _edge(model_prob, book_odd)
            if edge < MIN_EDGE_PCT:
                continue

            conf, dq_flag = _confidence(BASE_CONFIDENCE, dq_penalty)
            if conf < MIN_CONFIDENCE_PCT:
                continue

            fv = fair_value_odds(model_prob)
            units, eur = recommended_stake(edge)

            bet = {
                "sport": "basketball",
                "league": "NBA",
                "match_date": commence[:10] if commence else "",
                "home_team": home,
                "away_team": away,
                "market": "Moneyline",
                "selection": side,
                "bookmaker_odds": book_odd,
                "fair_value_odds": fv,
                "edge_pct": round(edge * 100, 2),
                "confidence_pct": conf,
                "data_quality_flag": dq_flag,
                "stake_units": units,
                "stake_eur": eur,
                "model_factors": factors,
                "status": "PENDING",
            }
            found.append(bet)
            if save:
                save_value_bet(bet)

    return found


# ---------------------------------------------------------------------------
# Full scan
# ---------------------------------------------------------------------------

def run_full_scan(save: bool = True) -> list[dict]:
    """Scan all sports and return all value bets found."""
    bets = []
    bets.extend(scan_all_football(save=save))
    bets.extend(scan_basketball(save=save))
    # Sort by edge descending
    bets.sort(key=lambda b: b["edge_pct"], reverse=True)
    return bets


def get_pending_bets() -> list[dict]:
    return get_value_bets(status="PENDING")


def get_all_bets() -> list[dict]:
    return get_value_bets()
