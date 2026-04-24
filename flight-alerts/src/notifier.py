import logging
from urllib.parse import urlencode

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

log = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def _google_flights_url(origin: str, destination: str, departure_date) -> str:
    q = f"flights from {origin} to {destination} on {departure_date.isoformat()}"
    return f"https://www.google.com/travel/flights?{urlencode({'q': q})}"


def _format_deal(deal: dict) -> str:
    dep = deal["departure_date"].strftime("%B %-d")
    link = _google_flights_url(deal["origin"], deal["destination"], deal["departure_date"])
    typical_low = deal.get("typical_low")
    typical_high = deal.get("typical_high")

    if typical_low is not None and typical_high is not None:
        typical_str = f"(${typical_low:.0f}–${typical_high:.0f})"
        typical_line = f"Typical range: ${typical_low:.0f} – ${typical_high:.0f}"
    else:
        typical_str = f"(baseline ${deal['baseline']:.0f})"
        typical_line = f"Baseline ({deal['baseline_source']}): ${deal['baseline']:.0f}"

    return (
        "✈️ Flight Deal Alert\n\n"
        f"{deal['origin']} → {deal['destination']}\n"
        f"📅 Departure: {dep}\n"
        f"💰 ${deal['price']:.0f} — {deal['pct_off']:.0f}% below typical {typical_str}\n"
        f"🔗 {link}\n\n"
        f"{typical_line}"
    )


def send(deal: dict) -> bool:
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": _format_deal(deal),
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(TELEGRAM_API, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        log.error("Telegram send failed: %s", e)
        return False


def send_heartbeat(text: str) -> None:
    try:
        requests.post(
            TELEGRAM_API,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "disable_notification": True,
            },
            timeout=10,
        )
    except requests.RequestException as e:
        log.warning("Heartbeat send failed: %s", e)
