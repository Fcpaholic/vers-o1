"""
Poisson-based football match outcome model.

For each match we estimate:
  - Expected goals home (lambda_h)
  - Expected goals away (lambda_a)

Using attack/defence strength ratings derived from historical averages,
blended with a form weight for recent results.

Then we compute P(home win), P(draw), P(away win) and P(over/under N goals)
via the Poisson distribution.
"""
import math
from functools import lru_cache
from src.data.db import get_team_stats_by_name, get_match_count
from config import CURRENT_SEASON, MIN_GAMES_FULL_CONFIDENCE, LOW_DATA_PENALTY


# League average goals per game (fallback when data is thin)
LEAGUE_AVG_GOALS = {
    "PL":  {"home": 1.53, "away": 1.15},
    "PD":  {"home": 1.56, "away": 1.10},
    "BL1": {"home": 1.65, "away": 1.25},
    "SA":  {"home": 1.44, "away": 1.08},
    "FL1": {"home": 1.42, "away": 1.10},
    "DED": {"home": 1.71, "away": 1.29},
    "PPL": {"home": 1.38, "away": 1.05},
    "BSA": {"home": 1.52, "away": 1.18},
    "ELC": {"home": 1.48, "away": 1.16},
}
DEFAULT_AVG = {"home": 1.50, "away": 1.10}

FORM_WEIGHT = 0.20   # 20% weight given to form adjustment
MAX_GOALS_SIM = 10   # Max goals simulated in Poisson table


def _poisson_pmf(k: int, lam: float) -> float:
    """P(X = k) for Poisson(lambda)."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _form_multiplier(form_str: str) -> float:
    """
    Convert a form string like 'WWDLW' to a small multiplier [0.85, 1.15].
    W=3pts, D=1pt, L=0pts; max 15pts for 5 games.
    """
    if not form_str:
        return 1.0
    pts = sum({"W": 3, "D": 1, "L": 0}.get(c, 1) for c in form_str[-5:])
    max_pts = len(form_str[-5:]) * 3 or 1
    ratio = pts / max_pts  # 0..1
    return 0.85 + 0.30 * ratio   # 0.85 (terrible) → 1.15 (perfect form)


def _data_quality(games_played: int) -> tuple[float, bool]:
    """
    Returns (confidence_penalty_fraction, low_quality_flag).
    If games_played < MIN_GAMES_FULL_CONFIDENCE, apply a linear penalty.
    """
    if games_played >= MIN_GAMES_FULL_CONFIDENCE:
        return 0.0, False
    penalty = LOW_DATA_PENALTY * (1 - games_played / MIN_GAMES_FULL_CONFIDENCE)
    return round(penalty, 4), True


def expected_goals(
    home_team: str,
    away_team: str,
    league: str,
    season: str = None,
) -> dict:
    """
    Compute expected goals for home and away teams.
    Returns a dict with lambda_h, lambda_a, data_quality_flag, confidence_penalty.
    """
    season = season or CURRENT_SEASON
    avg = LEAGUE_AVG_GOALS.get(league, DEFAULT_AVG)

    home_stats = get_team_stats_by_name(home_team, league, season)
    away_stats = get_team_stats_by_name(away_team, league, season)

    home_games = home_stats["games_played"] if home_stats else 0
    away_games = away_stats["games_played"] if away_stats else 0
    min_games = min(home_games, away_games)

    dq_penalty, dq_flag = _data_quality(min_games)

    # Attack & defence strengths (ratio to league average)
    if home_stats and home_stats["games_played"] > 0:
        home_attack = home_stats["home_avg_scored"] / avg["home"] if avg["home"] else 1.0
        home_defence = home_stats["home_avg_conceded"] / avg["away"] if avg["away"] else 1.0
        home_form = _form_multiplier(home_stats.get("form_last5", ""))
    else:
        home_attack = 1.0
        home_defence = 1.0
        home_form = 1.0

    if away_stats and away_stats["games_played"] > 0:
        away_attack = away_stats["away_avg_scored"] / avg["away"] if avg["away"] else 1.0
        away_defence = away_stats["away_avg_conceded"] / avg["home"] if avg["home"] else 1.0
        away_form = _form_multiplier(away_stats.get("form_last5", ""))
    else:
        away_attack = 1.0
        away_defence = 1.0
        away_form = 1.0

    # Base lambdas from strength ratings
    raw_lambda_h = home_attack * away_defence * avg["home"]
    raw_lambda_a = away_attack * home_defence * avg["away"]

    # Blend with form (FORM_WEIGHT)
    lambda_h = raw_lambda_h * (1 - FORM_WEIGHT) + raw_lambda_h * home_form * FORM_WEIGHT
    lambda_a = raw_lambda_a * (1 - FORM_WEIGHT) + raw_lambda_a * away_form * FORM_WEIGHT

    # Clamp to reasonable range
    lambda_h = max(0.3, min(lambda_h, 5.0))
    lambda_a = max(0.3, min(lambda_a, 5.0))

    return {
        "lambda_h": round(lambda_h, 4),
        "lambda_a": round(lambda_a, 4),
        "home_games": home_games,
        "away_games": away_games,
        "data_quality_flag": dq_flag,
        "confidence_penalty": dq_penalty,
        "home_form": home_stats.get("form_last5", "") if home_stats else "",
        "away_form": away_stats.get("form_last5", "") if away_stats else "",
        "home_avg_scored": home_stats.get("avg_scored", 0) if home_stats else 0,
        "away_avg_scored": away_stats.get("avg_scored", 0) if away_stats else 0,
    }


def outcome_probs(lambda_h: float, lambda_a: float) -> dict:
    """
    Compute P(home win), P(draw), P(away win) via Poisson joint distribution.
    """
    p_home = 0.0
    p_draw = 0.0
    p_away = 0.0

    for h in range(MAX_GOALS_SIM + 1):
        ph = _poisson_pmf(h, lambda_h)
        for a in range(MAX_GOALS_SIM + 1):
            pa = _poisson_pmf(a, lambda_a)
            p = ph * pa
            if h > a:
                p_home += p
            elif h == a:
                p_draw += p
            else:
                p_away += p

    total = p_home + p_draw + p_away
    if total == 0:
        return {"home": 1/3, "draw": 1/3, "away": 1/3}

    return {
        "home": round(p_home / total, 5),
        "draw": round(p_draw / total, 5),
        "away": round(p_away / total, 5),
    }


def over_under_probs(lambda_h: float, lambda_a: float, line: float = 2.5) -> dict:
    """P(total goals > line) and P(total goals < line)."""
    p_over = 0.0
    p_under = 0.0
    for h in range(MAX_GOALS_SIM + 1):
        for a in range(MAX_GOALS_SIM + 1):
            p = _poisson_pmf(h, lambda_h) * _poisson_pmf(a, lambda_a)
            if h + a > line:
                p_over += p
            else:
                p_under += p
    return {"over": round(p_over, 5), "under": round(p_under, 5)}


def btts_prob(lambda_h: float, lambda_a: float) -> dict:
    """P(both teams to score = yes/no)."""
    p_home_scores = 1 - _poisson_pmf(0, lambda_h)
    p_away_scores = 1 - _poisson_pmf(0, lambda_a)
    p_yes = p_home_scores * p_away_scores
    return {"yes": round(p_yes, 5), "no": round(1 - p_yes, 5)}


def model_factors_text(home_team: str, away_team: str, eg: dict) -> str:
    """Generate a short human-readable explanation of key model factors."""
    parts = []
    if eg["lambda_h"] > 1.8:
        parts.append(f"{home_team} strong at home ({eg['lambda_h']:.1f} xG)")
    if eg["lambda_a"] > 1.5:
        parts.append(f"{away_team} potent away ({eg['lambda_a']:.1f} xG)")
    if eg["lambda_h"] < 0.9:
        parts.append(f"{home_team} weak attack ({eg['lambda_h']:.1f} xG)")
    if eg["lambda_a"] < 0.7:
        parts.append(f"{away_team} weak away ({eg['lambda_a']:.1f} xG)")
    if eg.get("home_form", "").endswith(("WWW", "WWWW", "WWWWW")):
        parts.append(f"{home_team} in excellent form")
    if eg.get("away_form", "").endswith(("LLL", "LLLL", "LLLLL")):
        parts.append(f"{away_team} poor recent form")
    total_xg = eg["lambda_h"] + eg["lambda_a"]
    if total_xg > 3.2:
        parts.append(f"High-scoring game expected ({total_xg:.1f} total xG)")
    elif total_xg < 2.0:
        parts.append(f"Low-scoring game expected ({total_xg:.1f} total xG)")
    return "; ".join(parts) if parts else "Standard match — no standout factors"
