"""
Basketball (NBA) win probability model.
Uses historical point averages (home/away offensive and defensive ratings)
with form weighting to estimate P(home win) and P(away win).
No draws in basketball.
"""
from src.data.db import get_team_stats_by_name
from config import CURRENT_SEASON, MIN_GAMES_FULL_CONFIDENCE, LOW_DATA_PENALTY

NBA_AVG_POINTS = {"home": 114.5, "away": 111.5}
FORM_WEIGHT = 0.15


def _form_multiplier(form_str: str) -> float:
    if not form_str:
        return 1.0
    pts = sum({"W": 1, "L": 0}.get(c, 0) for c in form_str[-5:])
    n = len(form_str[-5:]) or 1
    ratio = pts / n
    return 0.90 + 0.20 * ratio  # 0.90 → 1.10


def _data_quality(games_played: int) -> tuple[float, bool]:
    if games_played >= MIN_GAMES_FULL_CONFIDENCE:
        return 0.0, False
    penalty = LOW_DATA_PENALTY * (1 - games_played / MIN_GAMES_FULL_CONFIDENCE)
    return round(penalty, 4), True


def expected_points(home_team: str, away_team: str, season: str = None) -> dict:
    season = season or CURRENT_SEASON
    avg = NBA_AVG_POINTS

    home_stats = get_team_stats_by_name(home_team, "NBA", season)
    away_stats = get_team_stats_by_name(away_team, "NBA", season)

    home_games = home_stats["games_played"] if home_stats else 0
    away_games = away_stats["games_played"] if away_stats else 0
    min_games = min(home_games, away_games)
    dq_penalty, dq_flag = _data_quality(min_games)

    if home_stats and home_stats["games_played"] > 0:
        home_off = home_stats["home_avg_scored"] / avg["home"]
        home_def = home_stats["home_avg_conceded"] / avg["away"]
        home_form = _form_multiplier(home_stats.get("form_last5", ""))
    else:
        home_off = home_def = home_form = 1.0

    if away_stats and away_stats["games_played"] > 0:
        away_off = away_stats["away_avg_scored"] / avg["away"]
        away_def = away_stats["away_avg_conceded"] / avg["home"]
        away_form = _form_multiplier(away_stats.get("form_last5", ""))
    else:
        away_off = away_def = away_form = 1.0

    raw_home_pts = home_off * away_def * avg["home"]
    raw_away_pts = away_off * home_def * avg["away"]

    exp_home = raw_home_pts * (1 - FORM_WEIGHT) + raw_home_pts * home_form * FORM_WEIGHT
    exp_away = raw_away_pts * (1 - FORM_WEIGHT) + raw_away_pts * away_form * FORM_WEIGHT

    return {
        "exp_home_pts": round(exp_home, 2),
        "exp_away_pts": round(exp_away, 2),
        "home_games": home_games,
        "away_games": away_games,
        "data_quality_flag": dq_flag,
        "confidence_penalty": dq_penalty,
        "home_form": home_stats.get("form_last5", "") if home_stats else "",
        "away_form": away_stats.get("form_last5", "") if away_stats else "",
    }


def win_probs(exp_home_pts: float, exp_away_pts: float) -> dict:
    """
    Convert expected point totals to win probabilities using a logistic function
    based on point differential.
    """
    diff = exp_home_pts - exp_away_pts
    # Logistic: sigma(diff / scale) where scale ≈ 10 points
    import math
    p_home = 1 / (1 + math.exp(-diff / 10.0))
    p_away = 1 - p_home
    return {
        "home": round(p_home, 5),
        "away": round(p_away, 5),
    }


def model_factors_text(home_team: str, away_team: str, ep: dict) -> str:
    parts = []
    diff = ep["exp_home_pts"] - ep["exp_away_pts"]
    if diff > 8:
        parts.append(f"{home_team} strong favourites (+{diff:.1f} pts advantage)")
    elif diff < -8:
        parts.append(f"{away_team} strong favourites ({abs(diff):.1f} pts advantage)")
    if ep.get("home_form", "").endswith("WWW"):
        parts.append(f"{home_team} on a winning streak")
    if ep.get("away_form", "").endswith("LLL"):
        parts.append(f"{away_team} struggling recently")
    parts.append(f"Projected score: {home_team} {ep['exp_home_pts']:.0f} – {ep['exp_away_pts']:.0f} {away_team}")
    return "; ".join(parts)
