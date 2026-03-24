"""
Telegram alert module.
Sends value bet notifications via a Telegram bot.
Uses the requests library directly (no async needed for simple sends).
"""
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def _send_message(text: str, parse_mode: str = "HTML") -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[telegram] Send failed: {e}")
        return False


def format_bet_message(bet: dict) -> str:
    sport_emoji = "⚽" if bet["sport"] == "football" else "🏀"
    dq_note = " *" if bet.get("data_quality_flag") else ""
    stake_note = "🔥 HIGH VALUE" if bet["stake_units"] == 2.0 else "✅ VALUE BET"

    lines = [
        f"{sport_emoji} <b>{stake_note}</b>",
        f"",
        f"<b>{bet['home_team']} vs {bet['away_team']}</b>",
        f"📅 {bet['match_date']} | {bet['league']}",
        f"",
        f"<b>Market:</b> {bet['market']}",
        f"<b>Selection:</b> {bet['selection']}",
        f"",
        f"<b>Odds:</b> {bet['bookmaker_odds']:.2f}",
        f"<b>Fair Value:</b> {bet['fair_value_odds']:.2f}",
        f"<b>Edge:</b> +{bet['edge_pct']:.1f}%",
        f"<b>Confidence:</b> {bet['confidence_pct']:.1f}%{dq_note}",
        f"",
        f"<b>Stake:</b> {bet['stake_units']:.0f}u (€{bet['stake_eur']:.0f})",
    ]

    if bet.get("model_factors"):
        lines += ["", f"<i>📊 {bet['model_factors']}</i>"]

    if bet.get("data_quality_flag"):
        lines += ["", "<i>* Confidence reduced due to limited data sample</i>"]

    return "\n".join(lines)


def send_value_bet(bet: dict) -> bool:
    """Send a single value bet alert to Telegram."""
    msg = format_bet_message(bet)
    return _send_message(msg)


def send_scan_summary(bets: list[dict]) -> bool:
    """Send a summary when a full scan is complete."""
    if not bets:
        msg = "🔍 <b>Scan complete</b>\nNo value bets found right now."
    else:
        n = len(bets)
        high_value = [b for b in bets if b["stake_units"] == 2.0]
        msg_lines = [
            f"🔍 <b>Scan complete — {n} value bet{'s' if n != 1 else ''} found</b>",
            "",
        ]
        for b in bets[:5]:  # Show top 5 in summary
            dq = "*" if b.get("data_quality_flag") else ""
            msg_lines.append(
                f"• {b['home_team']} vs {b['away_team']} | {b['selection']} "
                f"@ {b['bookmaker_odds']:.2f} | Edge: +{b['edge_pct']:.1f}% | "
                f"Conf: {b['confidence_pct']:.0f}%{dq} | {b['stake_units']:.0f}u"
            )
        if n > 5:
            msg_lines.append(f"  ...and {n - 5} more. See dashboard for full list.")
        if high_value:
            msg_lines.append(f"\n🔥 {len(high_value)} HIGH VALUE bet(s) — 2u recommended")
        msg = "\n".join(msg_lines)
    return _send_message(msg)


def send_test_message() -> bool:
    return _send_message("✅ <b>Value Bet Tracker connected.</b>\nTelegram alerts are working!")


def is_configured() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
