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
    return (
        f"<b>Fare drop: {deal['origin']} -> {deal['destination']}</b>\n"
        f"${deal['price']:.2f} on {deal['departure_date'].isoformat()} "
        f"({deal['pct_off']:.0f}% below 30d median ${deal['median_price']:.2f})\n"
        f"Stops: {deal['stops']} | Duration: {deal['duration_min']} min | "
        f"Airline: {deal.get('airline') or 'n/a'}\n"
        f"{_google_flights_url(deal['origin'], deal['destination'], deal['departure_date'])}"
    )


def send_deal(deal: dict) -> bool:
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": _format_deal(deal),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
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
