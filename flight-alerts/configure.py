#!/usr/bin/env python3
"""Interactive route manager for flight-alerts.

Edits routes.json. Run from the flight-alerts/ directory:

    ./venv/bin/python configure.py
"""

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROUTES_PATH = Path(__file__).resolve().parent / "routes.json"
IATA_RE = re.compile(r"^[A-Z]{3}$")
SERPAPI_FREE_LIMIT = 250
DEFAULT_DATES_PER_RUN = 5
# Tue–Thu cron cadence: 3 runs/week × ~4.33 weeks ≈ 13 runs/month
RUNS_PER_MONTH = 13

TRAVEL_CLASS_NAMES = {1: "Economy", 2: "Premium economy", 3: "Business", 4: "First"}


def load_routes() -> list[dict]:
    if ROUTES_PATH.exists():
        return json.loads(ROUTES_PATH.read_text())
    return []


def save_routes(routes: list[dict]) -> None:
    ROUTES_PATH.write_text(json.dumps(routes, indent=2) + "\n")


def prompt(message: str, default=None, validator=None):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"{message}{suffix}: ").strip()
        if not raw and default is not None:
            raw = str(default)
        if not raw:
            print("  (required)")
            continue
        if validator:
            err = validator(raw)
            if err:
                print(f"  {err}")
                continue
        return raw


def iata(s: str) -> str | None:
    return None if IATA_RE.match(s.upper()) else "Must be a 3-letter IATA code"


def int_in(minimum=None, maximum=None):
    def check(s):
        try:
            n = int(s)
        except ValueError:
            return "Must be an integer"
        if minimum is not None and n < minimum:
            return f"Must be >= {minimum}"
        if maximum is not None and n > maximum:
            return f"Must be <= {maximum}"
        return None

    return check


def choice(choices):
    def check(s):
        return None if s in choices else f"Must be one of: {', '.join(choices)}"

    return check


def iso_date_future(min_date: date | None = None):
    def check(s):
        try:
            d = date.fromisoformat(s)
        except ValueError:
            return "Use YYYY-MM-DD format"
        if d <= date.today():
            return "Must be a future date"
        if min_date and d < min_date:
            return f"Must be on or after {min_date.isoformat()}"
        return None

    return check


def max_stops_validator(s):
    if s.lower() in ("", "any", "none", "-"):
        return None
    try:
        n = int(s)
    except ValueError:
        return "Enter 0, 1, 2, or 'any'"
    if n < 0 or n > 2:
        return "Must be 0 (nonstop), 1, 2, or 'any'"
    return None


def parse_max_stops(s: str):
    if s.lower() in ("", "any", "none", "-"):
        return None
    return int(s)


def describe_stops(max_stops) -> str:
    if max_stops is None:
        return "any stops"
    if max_stops == 0:
        return "nonstop only"
    return f"up to {max_stops} stop{'s' if max_stops > 1 else ''}"


def list_routes(routes: list[dict]) -> None:
    if not routes:
        print("\nNo routes configured.")
        return
    print(f"\nConfigured routes ({len(routes)}):")
    for i, r in enumerate(routes):
        trip = "round trip" if r["trip_type"] == 1 else "one way"
        travel_class = TRAVEL_CLASS_NAMES.get(r.get("travel_class", 1), "Economy")
        stops = describe_stops(r.get("max_stops"))
        dpr = r.get("dates_per_run", DEFAULT_DATES_PER_RUN)
        print(f"  [{i}] {r['label']}  ({trip}, {travel_class}, {stops})")
        print(
            f"      {r['search_start']} → {r['search_end']}  "
            f"|  {dpr} random dates/run (1 sticky + {dpr - 1} random)"
        )


def show_budget(routes: list[dict]) -> None:
    if not routes:
        return
    total_per_run = sum(r.get("dates_per_run", DEFAULT_DATES_PER_RUN) for r in routes)
    per_month = total_per_run * RUNS_PER_MONTH
    flag = "OK" if per_month <= SERPAPI_FREE_LIMIT else "OVER FREE TIER"
    print(f"\nSerpApi call budget (Tue–Thu × 1 run/day = {RUNS_PER_MONTH} runs/month):")
    print(
        f"  {total_per_run} calls/run × {RUNS_PER_MONTH} runs ≈ {per_month}/month  "
        f"(limit: {SERPAPI_FREE_LIMIT})  [{flag}]"
    )


def add_route(routes: list[dict]) -> None:
    print("\nAdd a new route (Ctrl+C to cancel)")
    origin = prompt("Origin IATA (e.g. RDU)", validator=iata).upper()
    destination = prompt("Destination IATA (e.g. SFO)", validator=iata).upper()
    label = prompt("Label", default=f"{origin} → {destination}")
    trip_type = int(
        prompt("Trip type (1 = round trip, 2 = one way)", default="2", validator=choice(["1", "2"]))
    )

    default_start = (date.today() + timedelta(days=14)).isoformat()
    search_start_str = prompt(
        "Search window start date (YYYY-MM-DD)",
        default=default_start,
        validator=iso_date_future(),
    )
    search_start = date.fromisoformat(search_start_str)
    default_end = (search_start + timedelta(days=60)).isoformat()
    search_end_str = prompt(
        "Search window end date (YYYY-MM-DD)",
        default=default_end,
        validator=iso_date_future(min_date=search_start + timedelta(days=1)),
    )

    dates_per_run = int(
        prompt(
            "Dates to sample per run (1 sticky cheapest + rest random)",
            default=str(DEFAULT_DATES_PER_RUN),
            validator=int_in(1, 50),
        )
    )

    travel_class = int(
        prompt(
            "Travel class (1 = Economy, 2 = Premium economy, 3 = Business, 4 = First)",
            default="1",
            validator=choice(["1", "2", "3", "4"]),
        )
    )

    max_stops = parse_max_stops(
        prompt(
            "Max stops (0 = nonstop only, 1 = up to 1 stop, 2 = up to 2 stops, or 'any')",
            default="any",
            validator=max_stops_validator,
        )
    )

    routes.append(
        {
            "origin": origin,
            "destination": destination,
            "label": label,
            "trip_type": trip_type,
            "search_start": search_start_str,
            "search_end": search_end_str,
            "dates_per_run": dates_per_run,
            "travel_class": travel_class,
            "max_stops": max_stops,
        }
    )
    save_routes(routes)
    print(f"\n✓ Added {label}")


def delete_route(routes: list[dict]) -> None:
    list_routes(routes)
    if not routes:
        return
    idx = int(prompt("Index to delete", validator=int_in(0, len(routes) - 1)))
    removed = routes.pop(idx)
    save_routes(routes)
    print(f"\n✓ Deleted {removed['label']}")


def main() -> None:
    while True:
        routes = load_routes()
        list_routes(routes)
        show_budget(routes)
        print("\nActions: [a]dd  [d]elete  [q]uit")
        action = input("> ").strip().lower()
        if action == "a":
            try:
                add_route(routes)
            except KeyboardInterrupt:
                print("\n(cancelled)")
        elif action == "d":
            try:
                delete_route(routes)
            except KeyboardInterrupt:
                print("\n(cancelled)")
        elif action == "q":
            return
        else:
            print("Unknown action.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)
