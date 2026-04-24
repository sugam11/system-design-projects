import logging
from datetime import date, timedelta

from amadeus import Client, ResponseError

from config import (
    AMADEUS_CLIENT_ID,
    AMADEUS_CLIENT_SECRET,
    AMADEUS_ENV,
)

log = logging.getLogger(__name__)

_client = Client(
    client_id=AMADEUS_CLIENT_ID,
    client_secret=AMADEUS_CLIENT_SECRET,
    hostname="production" if AMADEUS_ENV == "production" else "test",
)


def _parse_duration(iso_duration: str) -> int:
    # e.g. "PT11H30M" -> 690
    body = iso_duration.replace("PT", "")
    hours = 0
    minutes = 0
    if "H" in body:
        h, body = body.split("H", 1)
        hours = int(h)
    if "M" in body:
        m, _ = body.split("M", 1)
        minutes = int(m)
    return hours * 60 + minutes


def _offer_to_fare(offer: dict, origin: str, destination: str, departure_date: date) -> dict:
    itinerary = offer["itineraries"][0]
    segments = itinerary["segments"]
    return {
        "origin": origin,
        "destination": destination,
        "departure_date": departure_date,
        "price": float(offer["price"]["total"]),
        "stops": max(len(segments) - 1, 0),
        "duration_min": _parse_duration(itinerary["duration"]),
        "airline": segments[0].get("carrierCode"),
    }


def fetch_route_fares(route: dict) -> list[dict]:
    fares: list[dict] = []
    today = date.today()
    for days_out in route["search_days_out"]:
        departure_date = today + timedelta(days=days_out)
        try:
            resp = _client.shopping.flight_offers_search.get(
                originLocationCode=route["origin"],
                destinationLocationCode=route["destination"],
                departureDate=departure_date.isoformat(),
                adults=1,
                currencyCode="USD",
                max=route["max_results"],
            )
        except ResponseError as e:
            log.warning("Amadeus error for %s->%s on %s: %s",
                        route["origin"], route["destination"], departure_date, e)
            continue

        for offer in resp.data:
            try:
                fares.append(_offer_to_fare(offer, route["origin"], route["destination"], departure_date))
            except (KeyError, ValueError) as e:
                log.warning("Skipping malformed offer: %s", e)
    return fares
