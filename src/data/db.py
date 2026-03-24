"""
Database layer — SQLite via standard library only.
All schema creation, reads, and writes go through this module.
"""
import sqlite3
import os
from datetime import datetime
from config import DB_PATH


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_conn()
    c = conn.cursor()

    # Teams
    c.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT,
            name        TEXT NOT NULL,
            league      TEXT NOT NULL,
            sport       TEXT NOT NULL DEFAULT 'football',
            UNIQUE(external_id, league)
        )
    """)

    # Historical matches
    c.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id     TEXT UNIQUE,
            sport           TEXT NOT NULL DEFAULT 'football',
            league          TEXT NOT NULL,
            season          TEXT,
            match_date      TEXT NOT NULL,
            home_team_id    INTEGER REFERENCES teams(id),
            away_team_id    INTEGER REFERENCES teams(id),
            home_team_name  TEXT,
            away_team_name  TEXT,
            home_goals      INTEGER,
            away_goals      INTEGER,
            status          TEXT DEFAULT 'FINISHED',
            created_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # Team stats (rolling, per league/season)
    c.execute("""
        CREATE TABLE IF NOT EXISTS team_stats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id         INTEGER REFERENCES teams(id),
            league          TEXT NOT NULL,
            season          TEXT NOT NULL,
            games_played    INTEGER DEFAULT 0,
            goals_scored    REAL DEFAULT 0,
            goals_conceded  REAL DEFAULT 0,
            avg_scored      REAL DEFAULT 0,
            avg_conceded    REAL DEFAULT 0,
            home_avg_scored   REAL DEFAULT 0,
            home_avg_conceded REAL DEFAULT 0,
            away_avg_scored   REAL DEFAULT 0,
            away_avg_conceded REAL DEFAULT 0,
            form_last5      TEXT DEFAULT '',
            updated_at      TEXT DEFAULT (datetime('now')),
            UNIQUE(team_id, league, season)
        )
    """)

    # Value bets log
    c.execute("""
        CREATE TABLE IF NOT EXISTS value_bets (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            sport           TEXT NOT NULL DEFAULT 'football',
            league          TEXT NOT NULL,
            match_date      TEXT NOT NULL,
            home_team        TEXT NOT NULL,
            away_team        TEXT NOT NULL,
            market          TEXT NOT NULL,
            selection       TEXT NOT NULL,
            bookmaker_odds  REAL NOT NULL,
            fair_value_odds REAL NOT NULL,
            edge_pct        REAL NOT NULL,
            confidence_pct  REAL NOT NULL,
            data_quality_flag INTEGER DEFAULT 0,
            stake_units     REAL NOT NULL,
            stake_eur       REAL NOT NULL,
            status          TEXT DEFAULT 'PENDING',
            result          TEXT,
            profit_loss_eur REAL,
            model_factors   TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            settled_at      TEXT
        )
    """)

    # Seeder state — track which leagues/seasons have been seeded
    c.execute("""
        CREATE TABLE IF NOT EXISTS seed_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            league      TEXT NOT NULL,
            season      TEXT NOT NULL,
            sport       TEXT NOT NULL DEFAULT 'football',
            seeded_at   TEXT DEFAULT (datetime('now')),
            record_count INTEGER DEFAULT 0,
            UNIQUE(league, season, sport)
        )
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

def upsert_team(external_id: str, name: str, league: str, sport: str = "football") -> int:
    conn = get_conn()
    conn.execute("""
        INSERT INTO teams (external_id, name, league, sport)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(external_id, league) DO UPDATE SET name=excluded.name
    """, (str(external_id), name, league, sport))
    conn.commit()
    row = conn.execute(
        "SELECT id FROM teams WHERE external_id=? AND league=?", (str(external_id), league)
    ).fetchone()
    conn.close()
    return row["id"]


def get_team_id(name: str, league: str) -> int | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM teams WHERE name=? AND league=?", (name, league)
    ).fetchone()
    conn.close()
    return row["id"] if row else None


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------

def insert_match(external_id, sport, league, season, match_date,
                  home_team_id, away_team_id, home_name, away_name,
                  home_goals, away_goals, status="FINISHED"):
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO matches
            (external_id, sport, league, season, match_date,
             home_team_id, away_team_id, home_team_name, away_team_name,
             home_goals, away_goals, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (str(external_id), sport, league, season, match_date,
          home_team_id, away_team_id, home_name, away_name,
          home_goals, away_goals, status))
    conn.commit()
    conn.close()


def get_matches(league: str, season: str = None, limit: int = 200):
    conn = get_conn()
    if season:
        rows = conn.execute(
            "SELECT * FROM matches WHERE league=? AND season=? ORDER BY match_date DESC LIMIT ?",
            (league, season, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM matches WHERE league=? ORDER BY match_date DESC LIMIT ?",
            (league, limit)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_match_count(league: str) -> int:
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM matches WHERE league=?", (league,)).fetchone()
    conn.close()
    return row["cnt"]


# ---------------------------------------------------------------------------
# Team Stats
# ---------------------------------------------------------------------------

def upsert_team_stats(team_id: int, league: str, season: str, stats: dict):
    conn = get_conn()
    conn.execute("""
        INSERT INTO team_stats
            (team_id, league, season, games_played, goals_scored, goals_conceded,
             avg_scored, avg_conceded, home_avg_scored, home_avg_conceded,
             away_avg_scored, away_avg_conceded, form_last5, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(team_id, league, season) DO UPDATE SET
            games_played=excluded.games_played,
            goals_scored=excluded.goals_scored,
            goals_conceded=excluded.goals_conceded,
            avg_scored=excluded.avg_scored,
            avg_conceded=excluded.avg_conceded,
            home_avg_scored=excluded.home_avg_scored,
            home_avg_conceded=excluded.home_avg_conceded,
            away_avg_scored=excluded.away_avg_scored,
            away_avg_conceded=excluded.away_avg_conceded,
            form_last5=excluded.form_last5,
            updated_at=excluded.updated_at
    """, (
        team_id, league, season,
        stats.get("games_played", 0),
        stats.get("goals_scored", 0),
        stats.get("goals_conceded", 0),
        stats.get("avg_scored", 0),
        stats.get("avg_conceded", 0),
        stats.get("home_avg_scored", 0),
        stats.get("home_avg_conceded", 0),
        stats.get("away_avg_scored", 0),
        stats.get("away_avg_conceded", 0),
        stats.get("form_last5", ""),
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()


def get_team_stats(team_id: int, league: str, season: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM team_stats WHERE team_id=? AND league=? AND season=?",
        (team_id, league, season)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_team_stats_by_name(name: str, league: str, season: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("""
        SELECT ts.* FROM team_stats ts
        JOIN teams t ON ts.team_id = t.id
        WHERE t.name=? AND ts.league=? AND ts.season=?
    """, (name, league, season)).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Value Bets
# ---------------------------------------------------------------------------

def save_value_bet(bet: dict) -> int:
    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO value_bets
            (sport, league, match_date, home_team, away_team, market,
             selection, bookmaker_odds, fair_value_odds, edge_pct,
             confidence_pct, data_quality_flag, stake_units, stake_eur,
             status, model_factors)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        bet["sport"], bet["league"], bet["match_date"],
        bet["home_team"], bet["away_team"], bet["market"],
        bet["selection"], bet["bookmaker_odds"], bet["fair_value_odds"],
        bet["edge_pct"], bet["confidence_pct"], int(bet.get("data_quality_flag", False)),
        bet["stake_units"], bet["stake_eur"],
        bet.get("status", "PENDING"), bet.get("model_factors", "")
    ))
    bet_id = cur.lastrowid
    conn.commit()
    conn.close()
    return bet_id


def get_value_bets(status: str = None, limit: int = 100):
    conn = get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM value_bets WHERE status=? ORDER BY created_at DESC LIMIT ?",
            (status, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM value_bets ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def settle_bet(bet_id: int, result: str, profit_loss_eur: float):
    """result: 'WIN' | 'LOSS' | 'VOID'"""
    conn = get_conn()
    conn.execute("""
        UPDATE value_bets
        SET result=?, profit_loss_eur=?, status='SETTLED', settled_at=?
        WHERE id=?
    """, (result, profit_loss_eur, datetime.utcnow().isoformat(), bet_id))
    conn.commit()
    conn.close()


def get_stats_summary() -> dict:
    conn = get_conn()
    row = conn.execute("""
        SELECT
            COUNT(*) as total_bets,
            SUM(CASE WHEN status='SETTLED' THEN 1 ELSE 0 END) as settled,
            SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN result='LOSS' THEN 1 ELSE 0 END) as losses,
            SUM(COALESCE(profit_loss_eur, 0)) as total_pnl,
            SUM(stake_eur) as total_staked
        FROM value_bets
    """).fetchone()
    conn.close()
    return dict(row) if row else {}


# ---------------------------------------------------------------------------
# Seed Log
# ---------------------------------------------------------------------------

def is_seeded(league: str, season: str, sport: str = "football") -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM seed_log WHERE league=? AND season=? AND sport=?",
        (league, season, sport)
    ).fetchone()
    conn.close()
    return row is not None


def mark_seeded(league: str, season: str, sport: str, record_count: int):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO seed_log (league, season, sport, record_count)
        VALUES (?,?,?,?)
    """, (league, season, sport, record_count))
    conn.commit()
    conn.close()
