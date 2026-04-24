import logging
from datetime import date, datetime, timedelta
from pathlib import Path

import analyzer
import db
import notifier
import serpapi_client
from config import ROUTES

LOG_PATH = Path(__file__).resolve().parent.parent / "run.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()],
)
log = logging.getLogger("flight-alerts")

HEARTBEAT_HOUR = 7


def _date_window(route: dict) -> list[date]:
    today = date.today()
    return [
        today + timedelta(days=n)
        for n in range(route["days_out_start"], route["days_out_end"] + 1, route["date_step"])
    ]


def run_route(route: dict) -> tuple[int, int, int]:
    fares_seen = 0
    alerts_sent = 0
    api_calls = 0

    for departure_date in _date_window(route):
        try:
            fares = serpapi_client.fetch(route, departure_date)
        except Exception:
            log.exception("Fetch failed: %s on %s", route["label"], departure_date)
            continue
        api_calls += 1

        if not fares:
            continue

        fares_seen += len(fares)
        try:
            db.save_fares(fares)
        except Exception:
            log.exception("DB save failed: %s on %s", route["label"], departure_date)
            continue

        try:
            deals = analyzer.check_for_deals(fares, route, departure_date)
        except Exception:
            log.exception("Analyzer failed: %s on %s", route["label"], departure_date)
            continue

        for deal in deals:
            if notifier.send(deal):
                db.record_alert(
                    deal["origin"], deal["destination"], deal["departure_date"], deal["price"]
                )
                alerts_sent += 1

    return fares_seen, alerts_sent, api_calls


def main() -> None:
    started = datetime.utcnow()
    log.info("Flight alerts run starting")

    db.init_schema()

    total_fares = 0
    total_alerts = 0
    total_calls = 0
    for route in ROUTES:
        try:
            fares, alerts, calls = run_route(route)
            total_fares += fares
            total_alerts += alerts
            total_calls += calls
            log.info(
                "Route %s: fetched %d fares via %d calls, sent %d alerts",
                route["label"],
                fares,
                calls,
                alerts,
            )
        except Exception:
            log.exception("Route %s failed", route["label"])

    elapsed = (datetime.utcnow() - started).total_seconds()
    month_calls = db.count_api_calls_this_month()
    log.info(
        "Done in %.1fs (fares=%d, alerts=%d, api_calls_this_run=%d, api_calls_this_month=%d/250)",
        elapsed,
        total_fares,
        total_alerts,
        total_calls,
        month_calls,
    )

    if datetime.now().hour == HEARTBEAT_HOUR:
        notifier.send_heartbeat(
            f"flight-alerts ok: {total_fares} fares, {total_alerts} alerts, "
            f"{total_calls} calls ({month_calls}/250 this month), {elapsed:.0f}s"
        )


if __name__ == "__main__":
    main()
