import logging
from datetime import datetime
from pathlib import Path

import amadeus_client
import analyzer
import db
import notifier
from config import ROUTES

LOG_PATH = Path(__file__).resolve().parent.parent / "flight-alerts.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()],
)
log = logging.getLogger("flight-alerts")


def run_route(route: dict) -> tuple[int, int]:
    fares = amadeus_client.fetch_route_fares(route)
    db.insert_fares(fares)
    deals = analyzer.find_deals(fares)

    sent = 0
    for deal in deals:
        if db.was_recently_alerted(deal["origin"], deal["destination"], deal["departure_date"]):
            continue
        if notifier.send_deal(deal):
            db.record_alert(
                deal["origin"], deal["destination"], deal["departure_date"],
                deal["price"], deal["median_price"], deal["pct_off"],
            )
            sent += 1
    return len(fares), sent


def main() -> None:
    started = datetime.utcnow()
    log.info("Flight alerts run starting")

    db.init_schema()

    total_fares = 0
    total_alerts = 0
    for route in ROUTES:
        label = f"{route['origin']}->{route['destination']}"
        try:
            fares, alerts = run_route(route)
            total_fares += fares
            total_alerts += alerts
            log.info("Route %s: fetched %d fares, sent %d alerts", label, fares, alerts)
        except Exception:
            log.exception("Route %s failed", label)

    elapsed = (datetime.utcnow() - started).total_seconds()
    notifier.send_heartbeat(
        f"flight-alerts ok: {total_fares} fares, {total_alerts} alerts, {elapsed:.0f}s"
    )
    log.info("Done in %.1fs (fares=%d, alerts=%d)", elapsed, total_fares, total_alerts)


if __name__ == "__main__":
    main()
