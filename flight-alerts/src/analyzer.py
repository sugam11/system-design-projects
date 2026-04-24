import logging

import db
from config import DEAL_THRESHOLD, MIN_HISTORY_DAYS

log = logging.getLogger(__name__)


def find_deals(fares: list[dict]) -> list[dict]:
    deals: list[dict] = []
    median_cache: dict[tuple[str, str], tuple[float | None, int]] = {}

    for fare in fares:
        key = (fare["origin"], fare["destination"])
        if key not in median_cache:
            median_cache[key] = db.get_median_price(*key)
        median, day_count = median_cache[key]

        if median is None or day_count < MIN_HISTORY_DAYS:
            continue

        if fare["price"] >= median * DEAL_THRESHOLD:
            continue

        pct_off = (median - fare["price"]) / median * 100.0
        deals.append({**fare, "median_price": median, "pct_off": pct_off})

    return deals
