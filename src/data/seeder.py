"""
Historical data seeder.
On first run (per league/season), pulls historical match data and computes team stats.
Subsequent runs skip already-seeded league/season combos.
"""
from datetime import datetime
from src.data.db import (
    upsert_team, insert_match, upsert_team_stats,
    is_seeded, mark_seeded, get_matches
)
from src.data.fetcher import fetch_fd_matches, fetch_nba_games
from config import FOOTBALL_LEAGUES, CURRENT_SEASON


# ---------------------------------------------------------------------------
# Football seeding (via football-data.org)
# ---------------------------------------------------------------------------

def seed_football_league(league_code: str, season: str = None) -> int:
    """
    Seed historical match data for a football league/season.
    Returns number of records inserted.
    """
    season = season or CURRENT_SEASON
    if is_seeded(league_code, season, "football"):
        return 0

    matches = fetch_fd_matches(league_code, season)
    if not matches:
        return 0

    count = 0
    for m in matches:
        if m.get("status") != "FINISHED":
            continue
        score = m.get("score", {}).get("fullTime", {})
        home_goals = score.get("home")
        away_goals = score.get("away")
        if home_goals is None or away_goals is None:
            continue

        home = m["homeTeam"]
        away = m["awayTeam"]
        home_id = upsert_team(str(home["id"]), home["name"], league_code, "football")
        away_id = upsert_team(str(away["id"]), away["name"], league_code, "football")

        insert_match(
            external_id=m["id"],
            sport="football",
            league=league_code,
            season=season,
            match_date=m.get("utcDate", "")[:10],
            home_team_id=home_id,
            away_team_id=away_id,
            home_name=home["name"],
            away_name=away["name"],
            home_goals=int(home_goals),
            away_goals=int(away_goals),
            status="FINISHED"
        )
        count += 1

    if count > 0:
        _compute_football_stats(league_code, season)
        mark_seeded(league_code, season, "football", count)

    return count


def _compute_football_stats(league_code: str, season: str):
    """Compute per-team averages from stored matches and upsert to team_stats."""
    matches = get_matches(league_code, season, limit=1000)

    # Build per-team records
    teams: dict[str, dict] = {}

    for m in matches:
        home = m["home_team_name"]
        away = m["away_team_name"]
        hg = m["home_goals"]
        ag = m["away_goals"]
        home_id = m["home_team_id"]
        away_id = m["away_team_id"]

        for team_name, team_id, scored, conceded, is_home in [
            (home, home_id, hg, ag, True),
            (away, away_id, ag, hg, False),
        ]:
            if team_name not in teams:
                teams[team_name] = {
                    "team_id": team_id,
                    "games": 0,
                    "scored": 0, "conceded": 0,
                    "home_scored": 0, "home_conceded": 0, "home_games": 0,
                    "away_scored": 0, "away_conceded": 0, "away_games": 0,
                    "results": [],  # 'W','D','L'
                }
            t = teams[team_name]
            t["games"] += 1
            t["scored"] += scored
            t["conceded"] += conceded
            if is_home:
                t["home_scored"] += scored
                t["home_conceded"] += conceded
                t["home_games"] += 1
            else:
                t["away_scored"] += scored
                t["away_conceded"] += conceded
                t["away_games"] += 1

            if scored > conceded:
                t["results"].append("W")
            elif scored == conceded:
                t["results"].append("D")
            else:
                t["results"].append("L")

    for team_name, t in teams.items():
        g = t["games"] or 1
        hg = t["home_games"] or 1
        ag = t["away_games"] or 1
        form = "".join(t["results"][-5:])

        upsert_team_stats(t["team_id"], league_code, season, {
            "games_played": t["games"],
            "goals_scored": t["scored"],
            "goals_conceded": t["conceded"],
            "avg_scored": round(t["scored"] / g, 3),
            "avg_conceded": round(t["conceded"] / g, 3),
            "home_avg_scored": round(t["home_scored"] / hg, 3),
            "home_avg_conceded": round(t["home_conceded"] / hg, 3),
            "away_avg_scored": round(t["away_scored"] / ag, 3),
            "away_avg_conceded": round(t["away_conceded"] / ag, 3),
            "form_last5": form,
        })


# ---------------------------------------------------------------------------
# NBA seeding (via balldontlie)
# ---------------------------------------------------------------------------

def seed_nba(season: int = 2024) -> int:
    season_str = str(season)
    if is_seeded("NBA", season_str, "basketball"):
        return 0

    games = fetch_nba_games(season=season)
    if not games:
        return 0

    count = 0
    for g in games:
        if g.get("status") != "Final":
            continue
        home = g.get("home_team", {})
        visitor = g.get("visitor_team", {})
        home_score = g.get("home_team_score")
        away_score = g.get("visitor_team_score")
        if home_score is None or away_score is None:
            continue

        home_id = upsert_team(
            str(home["id"]), home.get("full_name", home.get("name", "")),
            "NBA", "basketball"
        )
        away_id = upsert_team(
            str(visitor["id"]), visitor.get("full_name", visitor.get("name", "")),
            "NBA", "basketball"
        )

        match_date = g.get("date", "")[:10]
        insert_match(
            external_id=g["id"],
            sport="basketball",
            league="NBA",
            season=season_str,
            match_date=match_date,
            home_team_id=home_id,
            away_team_id=away_id,
            home_name=home.get("full_name", ""),
            away_name=visitor.get("full_name", ""),
            home_goals=int(home_score),
            away_goals=int(away_score),
            status="FINISHED"
        )
        count += 1

    if count > 0:
        _compute_nba_stats(season_str)
        mark_seeded("NBA", season_str, "basketball", count)

    return count


def _compute_nba_stats(season: str):
    matches = get_matches("NBA", season, limit=2000)
    teams: dict[str, dict] = {}

    for m in matches:
        for team_name, team_id, scored, conceded, is_home in [
            (m["home_team_name"], m["home_team_id"], m["home_goals"], m["away_goals"], True),
            (m["away_team_name"], m["away_team_id"], m["away_goals"], m["home_goals"], False),
        ]:
            if team_name not in teams:
                teams[team_name] = {
                    "team_id": team_id,
                    "games": 0, "scored": 0, "conceded": 0,
                    "home_scored": 0, "home_conceded": 0, "home_games": 0,
                    "away_scored": 0, "away_conceded": 0, "away_games": 0,
                    "results": [],
                }
            t = teams[team_name]
            t["games"] += 1
            t["scored"] += scored
            t["conceded"] += conceded
            if is_home:
                t["home_scored"] += scored
                t["home_conceded"] += conceded
                t["home_games"] += 1
            else:
                t["away_scored"] += scored
                t["away_conceded"] += conceded
                t["away_games"] += 1
            t["results"].append("W" if scored > conceded else "L")

    for team_name, t in teams.items():
        g = t["games"] or 1
        hg = t["home_games"] or 1
        ag = t["away_games"] or 1
        upsert_team_stats(t["team_id"], "NBA", season, {
            "games_played": t["games"],
            "goals_scored": t["scored"],
            "goals_conceded": t["conceded"],
            "avg_scored": round(t["scored"] / g, 2),
            "avg_conceded": round(t["conceded"] / g, 2),
            "home_avg_scored": round(t["home_scored"] / hg, 2),
            "home_avg_conceded": round(t["home_conceded"] / hg, 2),
            "away_avg_scored": round(t["away_scored"] / ag, 2),
            "away_avg_conceded": round(t["away_conceded"] / ag, 2),
            "form_last5": "".join(t["results"][-5:]),
        })


# ---------------------------------------------------------------------------
# Run all seeds
# ---------------------------------------------------------------------------

def run_all_seeds(progress_callback=None):
    """
    Seed all football leagues (current season) + NBA.
    progress_callback(message: str) called for UI updates.
    """
    results = {}

    for code in FOOTBALL_LEAGUES:
        msg = f"Seeding {FOOTBALL_LEAGUES[code]['name']}..."
        if progress_callback:
            progress_callback(msg)
        n = seed_football_league(code, CURRENT_SEASON)
        results[code] = n

    msg = "Seeding NBA..."
    if progress_callback:
        progress_callback(msg)
    n = seed_nba(2024)
    results["NBA"] = n

    return results
