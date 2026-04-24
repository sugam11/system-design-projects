#!/usr/bin/env python3
"""Interactive route manager for flight-alerts.

Edits routes.json. Run from the flight-alerts/ directory:

    ./venv/bin/python configure.py
"""

import json
import re
import sys
from pathlib import Path

ROUTES_PATH = Path(__file__).resolve().parent / "routes.json"
IATA_RE = re.compile(r"^[A-Z]{3}$")
SERPAPI_FREE_LIMIT = 250


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


def dates_per_run(r: dict) -> int:
    return (r["days_out_end"] - r["days_out_start"]) // r["date_step"] + 1


def list_routes(routes: list[dict]) -> None:
    if not routes:
        print("\nNo routes configured.")
        return
    print(f"\nConfigured routes ({len(routes)}):")
    for i, r in enumerate(routes):
        trip = "round trip" if r["trip_type"] == 1 else "one way"
        max_stops = r.get("max_stops")
        if max_stops is None:
            stops = "any stops"
        elif max_stops == 0:
            stops = "nonstop only"
        else:
            stops = f"max {max_stops} stop{'s' if max_stops > 1 else ''}"
        print(f"  [{i}] {r['label']}  ({trip}, {stops})")
        print(
            f"      {r['days_out_start']}–{r['days_out_end']} days out, "
            f"step {r['date_step']}  →  {dates_per_run(r)} dates per run"
        )


def show_budget(routes: list[dict]) -> None:
    if not routes:
        return
    total_dates = sum(dates_per_run(r) for r in routes)
    print("\nSerpApi call budget (free tier = 250/month):")
    for runs in (1, 2, 3):
        per_month = total_dates * runs * 30
        flag = "OK" if per_month <= SERPAPI_FREE_LIMIT else "OVER FREE TIER"
        print(f"  {runs}x/day  →  {total_dates * runs} calls/day, ~{per_month}/month  [{flag}]")


def add_route(routes: list[dict]) -> None:
    print("\nAdd a new route (Ctrl+C to cancel)")
    origin = prompt("Origin IATA (e.g. RDU)", validator=iata).upper()
    destination = prompt("Destination IATA (e.g. SFO)", validator=iata).upper()
    label = prompt("Label", default=f"{origin} → {destination}")
    trip_type = int(
        prompt("Trip type (1 = round trip, 2 = one way)", default="2", validator=choice(["1", "2"]))
    )
    start = int(prompt("Window start (days from today)", default="7", validator=int_in(1, 365)))
    end = int(
        prompt("Window end (days from today)", default="90", validator=int_in(start + 1, 365))
    )
    step = int(prompt("Date step (check every Nth day)", default="7", validator=int_in(1, 365)))
    max_stops = parse_max_stops(
        prompt(
            "Max stops (0 = nonstop, 1, 2, or 'any')",
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
            "days_out_start": start,
            "days_out_end": end,
            "date_step": step,
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
