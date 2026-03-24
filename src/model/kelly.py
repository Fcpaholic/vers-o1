"""
Kelly Criterion stake calculator.
Rules:
  - Fractional Kelly (25%)
  - Max 2u for high-value bets (edge >= HIGH_VALUE_THRESHOLD)
  - 1u for standard value bets
  - Never exceed 2u
  - 1u = €10
"""
from config import (
    KELLY_FRACTION, MAX_STAKE_UNITS, STANDARD_STAKE_UNITS,
    HIGH_VALUE_THRESHOLD, UNIT_VALUE_EUR
)


def kelly_fraction_stake(prob: float, decimal_odds: float) -> float:
    """
    Fractional Kelly stake as a fraction of bankroll.
    f* = (b*p - q) / b  where b = decimal_odds - 1
    Returns raw Kelly fraction (can be negative if no edge).
    """
    if decimal_odds <= 1.0 or prob <= 0:
        return 0.0
    b = decimal_odds - 1.0
    q = 1.0 - prob
    raw_kelly = (b * prob - q) / b
    return raw_kelly * KELLY_FRACTION


def recommended_stake(edge_pct: float) -> tuple[float, float]:
    """
    Map edge percentage to stake units and euros.
    Returns (units, euros).
    """
    if edge_pct >= HIGH_VALUE_THRESHOLD:
        units = MAX_STAKE_UNITS       # 2u
    else:
        units = STANDARD_STAKE_UNITS  # 1u
    return units, units * UNIT_VALUE_EUR


def fair_value_odds(prob: float) -> float:
    """Convert probability to fair decimal odds (no margin)."""
    if prob <= 0:
        return 9999.0
    return round(1 / prob, 3)


def implied_prob(decimal_odds: float) -> float:
    """Convert decimal odds to implied probability."""
    if decimal_odds <= 0:
        return 0.0
    return round(1 / decimal_odds, 5)


def remove_margin(odds_dict: dict) -> dict:
    """
    Remove bookmaker margin from a set of odds to get true probabilities.
    odds_dict: {"home": 2.0, "draw": 3.5, "away": 3.8}
    Returns dict of devigged probabilities.
    """
    probs = {k: implied_prob(v) for k, v in odds_dict.items() if v and v > 0}
    total = sum(probs.values())
    if total == 0:
        return probs
    return {k: round(v / total, 5) for k, v in probs.items()}
