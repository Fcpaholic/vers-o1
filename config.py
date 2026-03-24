import os

# Load .env if present (local dev)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _secret(key: str, default: str = "") -> str:
    """Read from Streamlit secrets first, fall back to env vars."""
    try:
        import streamlit as st
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)

# --- API Keys (set via Streamlit secrets or .env) ---
ODDS_API_KEY = _secret("ODDS_API_KEY")
FOOTBALL_DATA_API_KEY = _secret("FOOTBALL_DATA_API_KEY")
API_FOOTBALL_KEY = _secret("API_FOOTBALL_KEY")
TELEGRAM_BOT_TOKEN = _secret("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _secret("TELEGRAM_CHAT_ID")

# --- Bankroll ---
STARTING_BANKROLL_EUR = 10_000.0   # Paper trading bankroll

# --- Unit Sizing ---
UNIT_VALUE_EUR = 10.0       # 1u = €10, fixed
MAX_STAKE_UNITS = 2.0       # Never exceed 2u
STANDARD_STAKE_UNITS = 1.0
HIGH_VALUE_THRESHOLD = 0.10  # Edge >= 10% qualifies for 2u

# --- Value Betting Thresholds ---
MIN_EDGE_PCT = 0.03          # Minimum 3% edge to flag a value bet
MIN_CONFIDENCE_PCT = 50.0    # Minimum confidence % to show bet
KELLY_FRACTION = 0.25        # Fractional Kelly (25%)

# --- Data Quality ---
MIN_GAMES_FULL_CONFIDENCE = 8   # Games needed for full confidence
LOW_DATA_PENALTY = 0.15         # Reduce confidence by up to 15% for sparse data

# --- Football Leagues ---
FOOTBALL_LEAGUES = {
    # Top 5
    "PL":  {"name": "Premier League",     "country": "England",  "fd_id": "PL",  "apif_id": 39},
    "PD":  {"name": "La Liga",            "country": "Spain",    "fd_id": "PD",  "apif_id": 140},
    "BL1": {"name": "Bundesliga",         "country": "Germany",  "fd_id": "BL1", "apif_id": 78},
    "SA":  {"name": "Serie A",            "country": "Italy",    "fd_id": "SA",  "apif_id": 135},
    "FL1": {"name": "Ligue 1",            "country": "France",   "fd_id": "FL1", "apif_id": 61},
    # Extended
    "DED": {"name": "Eredivisie",         "country": "Netherlands", "fd_id": "DED", "apif_id": 88},
    "PPL": {"name": "Liga Portugal",      "country": "Portugal", "fd_id": "PPL", "apif_id": 94},
    "BSA": {"name": "Belgian Pro League", "country": "Belgium",  "fd_id": "BSA", "apif_id": 144},
    "ELC": {"name": "Championship",       "country": "England",  "fd_id": "ELC", "apif_id": 40},
}

# --- Basketball ---
BASKETBALL_LEAGUES = {
    "NBA": {"name": "NBA", "balldontlie_id": None},
}

# --- Odds API ---
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
ODDS_SPORT_FOOTBALL = "soccer"
ODDS_SPORT_BASKETBALL = "basketball_nba"
ODDS_REGIONS = "eu"
ODDS_MARKETS_FOOTBALL = "h2h,totals,btts"
ODDS_MARKETS_BASKETBALL = "h2h"
ODDS_BOOKMAKER_SHARP = "pinnacle"  # Reference line for fair value

# --- football-data.org ---
FD_BASE = "https://api.football-data.org/v4"

# --- API-Football ---
APIF_BASE = "https://v3.football.api-sports.io"

# --- balldontlie ---
BDL_BASE = "https://api.balldontlie.io/v1"

# --- Database ---
DB_PATH = "data/betting.db"

# --- Streamlit ---
APP_TITLE = "Value Bet Tracker"
CURRENT_SEASON = "2024"
