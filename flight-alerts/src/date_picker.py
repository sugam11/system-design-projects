"""Picks which departure dates to query each run.

Strategy: 1 sticky date (the cheapest observed in the last 7 days within
the current search window) plus N-1 random dates sampled from the window.
On the first run for a route, sticky is unavailable and we pick N random.
"""

import logging
import random
from datetime import date, timedelta

import db

log = logging.getLogger(__name__)

DEFAULT_DATES_PER_RUN = 5


def _valid_window(route: dict, today: date) -> tuple[date, date] | None:
    start = max(date.fromisoformat(route["search_start"]), today + timedelta(days=1))
    end = date.fromisoformat(route["search_end"])
    if start > end:
        return None
    return start, end


def select_dates(route: dict, today: date | None = None) -> list[date]:
    today = today or date.today()
    window = _valid_window(route, today)
    if window is None:
        log.info(
            "Route %s: search window %s–%s has expired, skipping",
            route["label"],
            route["search_start"],
            route["search_end"],
        )
        return []

    start, end = window
    all_dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    n = min(route.get("dates_per_run", DEFAULT_DATES_PER_RUN), len(all_dates))
    if n == 0:
        return []

    sticky = db.get_cheapest_recent_date(route["origin"], route["destination"], start, end)
    if sticky is not None and sticky not in all_dates:
        sticky = None

    pool = [d for d in all_dates if d != sticky]
    sample_size = min(n - (1 if sticky else 0), len(pool))
    sampled = random.sample(pool, sample_size)
    picked = sorted(([sticky] if sticky else []) + sampled)

    if sticky:
        log.info(
            "Route %s: %d dates selected (sticky=%s, random=%d)",
            route["label"],
            len(picked),
            sticky.isoformat(),
            len(sampled),
        )
    else:
        log.info(
            "Route %s: %d dates selected (no sticky yet, random=%d)",
            route["label"],
            len(picked),
            len(sampled),
        )

    return picked
