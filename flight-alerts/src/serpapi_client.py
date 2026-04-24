import logging
from datetime import date, timedelta

from serpapi import GoogleSearch

import db
from config import SERPAPI_KEY

log = logging.getLogger(__name__)


def _date_window(route: dict) -> list[date]:
    today = date.today()
    dates: list[date] = []
    for days_out in range(route["days_out_start"], route["days_out_end"] + 1, route["date_step"]):
        dates.append(today + timedelta(days=days_out))
    return dates


def _cheapest_offer(response: dict) -> dict | None:
    offers = (response.get("best_flights") or []) + (response.get("other_flights") or [])
    offers = [o for o in offers if o.get("price") is not None]
    if not offers:
        return None
    return min(offers, key=lambda o: o["price"])


def _offer_details(offer: dict) -> dict:
    segments = offer.get("flights") or []
    total_duration = offer.get("total_duration")
    if total_duration is None and segments:
        total_duration = sum(int(s.get("duration") or 0) for s in segments)
    airline = segments[0].get("airline") if segments else None
    return {
        "airline": airline,
        "stops": max(len(segments) - 1, 0),
        "duration_min": int(total_duration) if total_duration is not None else None,
    }


def fetch(route: dict, departure_date: date) -> list[dict]:
    params = {
        "engine": "google_flights",
        "api_key": SERPAPI_KEY,
        "departure_id": route["origin"],
        "arrival_id": route["destination"],
        "outbound_date": departure_date.isoformat(),
        "type": route["trip_type"],
        "currency": "USD",
        "hl": "en",
    }
    max_stops = route.get("max_stops")
    if max_stops is not None:
        # SerpApi stops: 1 = any, 2 = nonstop, 3 = <=1 stop, 4 = <=2 stops
        params["stops"] = max_stops + 2

    travel_class = route.get("travel_class")
    if travel_class is not None:
        # SerpApi travel_class: 1 = economy, 2 = premium economy, 3 = business, 4 = first
        params["travel_class"] = travel_class

    call_args = (
        route["origin"],
        route["destination"],
        departure_date,
        route["trip_type"],
        route["label"],
    )

    try:
        response = GoogleSearch(params).get_dict()
    except Exception as e:
        log.warning("SerpApi error for %s on %s: %s", route["label"], departure_date, e)
        db.log_api_call(*call_args, status="error", error_message=str(e))
        return []

    if "error" in response:
        log.warning(
            "SerpApi returned error for %s on %s: %s",
            route["label"],
            departure_date,
            response["error"],
        )
        db.log_api_call(
            *call_args, status="error", response=response, error_message=response["error"]
        )
        return []

    insights = response.get("price_insights") or {}
    typical_range = insights.get("typical_price_range") or [None, None]
    typical_low = typical_range[0] if len(typical_range) >= 1 else None
    typical_high = typical_range[1] if len(typical_range) >= 2 else None

    cheapest = _cheapest_offer(response)
    lowest_price = insights.get("lowest_price")
    if lowest_price is None and cheapest is not None:
        lowest_price = cheapest["price"]

    if lowest_price is None:
        log.info("No fares returned for %s on %s", route["label"], departure_date)
        db.log_api_call(*call_args, status="empty", response=response)
        return []

    db.log_api_call(*call_args, status="ok", response=response)

    details = (
        _offer_details(cheapest)
        if cheapest
        else {"airline": None, "stops": None, "duration_min": None}
    )

    return [
        {
            "origin": route["origin"],
            "destination": route["destination"],
            "departure_date": departure_date,
            "price": float(lowest_price),
            "price_level": insights.get("price_level"),
            "typical_low": float(typical_low) if typical_low is not None else None,
            "typical_high": float(typical_high) if typical_high is not None else None,
            **details,
        }
    ]
