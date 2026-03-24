"""
API fetchers for all data sources:
  - The Odds API       → live odds
  - football-data.org  → results, standings
  - API-Football       → deep stats
  - balldontlie.io     → NBA results
"""
import time
import requests
from config import (
    ODDS_API_KEY, ODDS_API_BASE, ODDS_REGIONS,
    FOOTBALL_DATA_API_KEY, FD_BASE,
    API_FOOTBALL_KEY, APIF_BASE,
    BDL_BASE,
    ODDS_SPORT_FOOTBALL, ODDS_SPORT_BASKETBALL,
    ODDS_MARKETS_FOOTBALL, ODDS_MARKETS_BASKETBALL,
)


def _get(url: str, headers: dict = None, params: dict = None, retries: int = 3) -> dict | list | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=15)
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == retries - 1:
                print(f"[fetcher] ERROR {url}: {e}")
                return None
            time.sleep(1)
    return None


# ---------------------------------------------------------------------------
# The Odds API
# ---------------------------------------------------------------------------

def fetch_football_odds(sport_key: str) -> list[dict]:
    """Fetch odds for a football competition. sport_key e.g. 'soccer_epl'"""
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": ODDS_REGIONS,
        "markets": ODDS_MARKETS_FOOTBALL,
        "oddsFormat": "decimal",
    }
    data = _get(f"{ODDS_API_BASE}/sports/{sport_key}/odds", params=params)
    return data if isinstance(data, list) else []


def fetch_basketball_odds() -> list[dict]:
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": ODDS_REGIONS,
        "markets": ODDS_MARKETS_BASKETBALL,
        "oddsFormat": "decimal",
    }
    data = _get(f"{ODDS_API_BASE}/sports/{ODDS_SPORT_BASKETBALL}/odds", params=params)
    return data if isinstance(data, list) else []


def fetch_available_sports() -> list[dict]:
    data = _get(f"{ODDS_API_BASE}/sports", params={"apiKey": ODDS_API_KEY})
    return data if isinstance(data, list) else []


def get_best_odds(event: dict, market: str = "h2h") -> dict:
    """
    Extract best available odds and Pinnacle reference from an Odds API event.
    Returns dict with keys: home, draw, away (decimal odds) for best book + pinnacle.
    """
    result = {
        "best": {"home": None, "draw": None, "away": None},
        "pinnacle": {"home": None, "draw": None, "away": None},
        "home_team": event.get("home_team"),
        "away_team": event.get("away_team"),
        "commence_time": event.get("commence_time"),
    }
    for bookmaker in event.get("bookmakers", []):
        for mkt in bookmaker.get("markets", []):
            if mkt["key"] != market:
                continue
            outcomes = {o["name"]: o["price"] for o in mkt.get("outcomes", [])}
            home_price = outcomes.get(event.get("home_team"))
            away_price = outcomes.get(event.get("away_team"))
            draw_price = outcomes.get("Draw")

            is_pinnacle = bookmaker["key"] == "pinnacle"

            for side, price in [("home", home_price), ("away", away_price), ("draw", draw_price)]:
                if price is None:
                    continue
                if is_pinnacle:
                    result["pinnacle"][side] = price
                if result["best"][side] is None or price > result["best"][side]:
                    result["best"][side] = price
    return result


# ---------------------------------------------------------------------------
# football-data.org
# ---------------------------------------------------------------------------

def _fd_headers():
    return {"X-Auth-Token": FOOTBALL_DATA_API_KEY}


def fetch_fd_matches(competition_code: str, season: str = None) -> list[dict]:
    """Fetch finished matches for a competition."""
    params = {"status": "FINISHED"}
    if season:
        params["season"] = season
    data = _get(
        f"{FD_BASE}/competitions/{competition_code}/matches",
        headers=_fd_headers(),
        params=params
    )
    if data and "matches" in data:
        return data["matches"]
    return []


def fetch_fd_standings(competition_code: str, season: str = None) -> list[dict]:
    params = {}
    if season:
        params["season"] = season
    data = _get(
        f"{FD_BASE}/competitions/{competition_code}/standings",
        headers=_fd_headers(),
        params=params
    )
    if data and "standings" in data:
        return data["standings"]
    return []


def fetch_fd_upcoming(competition_code: str) -> list[dict]:
    """Fetch scheduled upcoming matches."""
    data = _get(
        f"{FD_BASE}/competitions/{competition_code}/matches",
        headers=_fd_headers(),
        params={"status": "SCHEDULED"}
    )
    if data and "matches" in data:
        return data["matches"]
    return []


# ---------------------------------------------------------------------------
# API-Football (RapidAPI)
# ---------------------------------------------------------------------------

def _apif_headers():
    return {
        "x-rapidapi-key": API_FOOTBALL_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io",
    }


def fetch_apif_fixtures(league_id: int, season: str) -> list[dict]:
    data = _get(
        f"{APIF_BASE}/fixtures",
        headers=_apif_headers(),
        params={"league": league_id, "season": season, "status": "FT"}
    )
    if data and "response" in data:
        return data["response"]
    return []


def fetch_apif_team_stats(league_id: int, season: str, team_id: int) -> dict | None:
    data = _get(
        f"{APIF_BASE}/teams/statistics",
        headers=_apif_headers(),
        params={"league": league_id, "season": season, "team": team_id}
    )
    if data and "response" in data:
        return data["response"]
    return None


def fetch_apif_upcoming(league_id: int) -> list[dict]:
    data = _get(
        f"{APIF_BASE}/fixtures",
        headers=_apif_headers(),
        params={"league": league_id, "next": 10}
    )
    if data and "response" in data:
        return data["response"]
    return []


# ---------------------------------------------------------------------------
# balldontlie (NBA) — no API key needed
# ---------------------------------------------------------------------------

def fetch_nba_games(season: int = 2024, per_page: int = 100) -> list[dict]:
    """Fetch NBA game results. Season = start year (e.g. 2024 = 2024-25)."""
    all_games = []
    page = 1
    while True:
        data = _get(
            f"{BDL_BASE}/games",
            params={"seasons[]": season, "per_page": per_page, "page": page}
        )
        if not data or "data" not in data:
            break
        games = data["data"]
        if not games:
            break
        all_games.extend(games)
        meta = data.get("meta", {})
        if page >= meta.get("total_pages", 1):
            break
        page += 1
        time.sleep(0.2)
    return all_games


def fetch_nba_upcoming() -> list[dict]:
    """Fetch upcoming NBA games (next 7 days)."""
    from datetime import datetime, timedelta
    today = datetime.utcnow().date()
    end = today + timedelta(days=7)
    data = _get(
        f"{BDL_BASE}/games",
        params={
            "start_date": str(today),
            "end_date": str(end),
            "per_page": 100,
        }
    )
    if data and "data" in data:
        return data["data"]
    return []


def fetch_nba_team_stats(season: int = 2024) -> list[dict]:
    """Fetch season averages for all NBA teams."""
    data = _get(f"{BDL_BASE}/teams", params={"per_page": 30})
    if not data or "data" not in data:
        return []
    return data["data"]


# ---------------------------------------------------------------------------
# Odds API — football sport keys mapping
# ---------------------------------------------------------------------------

ODDS_API_FOOTBALL_KEYS = {
    "PL":  "soccer_epl",
    "PD":  "soccer_spain_la_liga",
    "BL1": "soccer_germany_bundesliga",
    "SA":  "soccer_italy_serie_a",
    "FL1": "soccer_france_ligue_one",
    "DED": "soccer_netherlands_eredivisie",
    "PPL": "soccer_portugal_primeira_liga",
    "BSA": "soccer_belgium_first_div",
    "ELC": "soccer_england_championship",
}
