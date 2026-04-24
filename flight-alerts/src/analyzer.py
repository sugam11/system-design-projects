import logging

import db
from config import DEAL_THRESHOLD, MIN_HISTORY_DAYS

log = logging.getLogger(__name__)


def _build_deal(fare: dict, baseline: float, baseline_source: str,
                typical_low: float | None, typical_high: float | None) -> dict:
    pct_off = (baseline - fare["price"]) / baseline * 100.0
    return {
        **fare,
        "baseline": baseline,
        "baseline_source": baseline_source,
        "typical_low": typical_low if typical_low is not None else fare.get("typical_low"),
        "typical_high": typical_high if typical_high is not None else fare.get("typical_high"),
        "pct_off": pct_off,
    }


def check_for_deals(fares: list[dict], route: dict, departure_date) -> list[dict]:
    deals: list[dict] = []
    for fare in fares:
        price = fare["price"]
        typical_low = fare.get("typical_low")
        typical_high = fare.get("typical_high")

        deal: dict | None = None

        if typical_low is not None and price < typical_low * DEAL_THRESHOLD:
            deal = _build_deal(fare, typical_low, "serpapi", typical_low, typical_high)
        else:
            median, day_count = db.get_median_price(fare["origin"], fare["destination"], departure_date)
            if median is not None and day_count >= MIN_HISTORY_DAYS and price < median * DEAL_THRESHOLD:
                deal = _build_deal(fare, median, "history", typical_low, typical_high)

        if deal is None:
            continue

        if db.was_recently_alerted(fare["origin"], fare["destination"], departure_date):
            log.info("Skipping %s on %s — already alerted in cooldown window",
                     route["label"], departure_date)
            continue

        deals.append(deal)

    return deals
