import httpx
import logging
from app.models import FlightInfo, Layover, TravelerResult, Traveler

logger = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search"


def _parse_flights(data: dict, dep_iata: str, arr_iata: str, flight_date: str) -> tuple[list[FlightInfo], int | None]:
    flights: list[FlightInfo] = []
    lowest_price: int | None = data.get("price_insights", {}).get("lowest_price")

    for group in [*data.get("best_flights", []), *data.get("other_flights", [])]:
        legs: list[dict] = group.get("flights", [])
        if not legs:
            continue

        first_leg = legs[0]
        last_leg  = legs[-1]

        layovers = [
            Layover(
                airport=lv.get("name") or lv.get("id", "?"),
                duration_min=lv.get("duration", 0),
            )
            for lv in group.get("layovers", [])
        ]

        flights.append(FlightInfo(
            flight_number=first_leg.get("flight_number", "N/A"),
            airline=first_leg.get("airline", "Unknown"),
            airline_logo=first_leg.get("airline_logo"),
            departure_airport=first_leg.get("departure_airport", {}).get("name", dep_iata),
            departure_iata=first_leg.get("departure_airport", {}).get("id", dep_iata),
            departure_time=first_leg.get("departure_airport", {}).get("time", ""),
            arrival_airport=last_leg.get("arrival_airport", {}).get("name", arr_iata),
            arrival_iata=last_leg.get("arrival_airport", {}).get("id", arr_iata),
            arrival_time=last_leg.get("arrival_airport", {}).get("time", ""),
            duration_min=group.get("total_duration", 0),
            price=group.get("price"),
            stops=len(layovers),
            layovers=layovers,
            airplane=first_leg.get("airplane"),
            travel_class=first_leg.get("travel_class"),
        ))

    return flights, lowest_price


async def fetch_flights(
    api_key: str,
    dep_iata: str,
    arr_iata: str,
    flight_date: str,
) -> tuple[list[FlightInfo], int | None]:
    params = {
        "engine":        "google_flights",
        "api_key":       api_key,
        "departure_id":  dep_iata.upper(),
        "arrival_id":    arr_iata.upper(),
        "outbound_date": flight_date,
        "type":          "2",   # one-way
        "currency":      "USD",
        "hl":            "en",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(SERPAPI_URL, params=params)
        response.raise_for_status()
        data = response.json()

    if data.get("search_metadata", {}).get("status") == "Error":
        raise ValueError(data.get("error", "SerpAPI error"))

    return _parse_flights(data, dep_iata, arr_iata, flight_date)


async def search_flights_for_group(
    api_key: str,
    travelers: list[Traveler],
    destination_iata: str,
    flight_date: str,
) -> list[TravelerResult]:
    results: list[TravelerResult] = []

    for traveler in travelers:
        try:
            flights, lowest_price = await fetch_flights(
                api_key=api_key,
                dep_iata=traveler.departure_iata,
                arr_iata=destination_iata,
                flight_date=flight_date,
            )
            results.append(TravelerResult(
                traveler_name=traveler.name,
                departure_iata=traveler.departure_iata.upper(),
                flights=flights,
                lowest_price=lowest_price,
            ))
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error for %s: %s", traveler.name, e)
            results.append(TravelerResult(
                traveler_name=traveler.name,
                departure_iata=traveler.departure_iata.upper(),
                flights=[],
                error=f"HTTP {e.response.status_code}: nie można pobrać lotów",
            ))
        except ValueError as e:
            logger.error("API error for %s: %s", traveler.name, e)
            results.append(TravelerResult(
                traveler_name=traveler.name,
                departure_iata=traveler.departure_iata.upper(),
                flights=[],
                error=str(e),
            ))
        except Exception as e:
            logger.error("Unexpected error for %s: %s", traveler.name, e)
            results.append(TravelerResult(
                traveler_name=traveler.name,
                departure_iata=traveler.departure_iata.upper(),
                flights=[],
                error="Nieoczekiwany błąd podczas pobierania lotów",
            ))

    return results
