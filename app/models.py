from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class Traveler(BaseModel):
    name: str
    departure_iata: str = Field(..., min_length=3, max_length=3)


class FlightSearchRequest(BaseModel):
    travelers: list[Traveler] = Field(..., min_length=1, max_length=10)
    destination_iata: str = Field(..., min_length=3, max_length=3)
    flight_date: date


class Layover(BaseModel):
    airport: str
    duration_min: int


class FlightInfo(BaseModel):
    flight_number: str
    airline: str
    airline_logo: Optional[str] = None
    departure_airport: str
    departure_iata: str
    departure_time: str
    arrival_airport: str
    arrival_iata: str
    arrival_time: str
    duration_min: int
    price: Optional[int] = None
    currency: str = "USD"
    stops: int = 0
    layovers: list[Layover] = []
    airplane: Optional[str] = None
    travel_class: Optional[str] = None


class TravelerResult(BaseModel):
    traveler_name: str
    departure_iata: str
    flights: list[FlightInfo]
    lowest_price: Optional[int] = None
    error: Optional[str] = None


class FlightMatchResponse(BaseModel):
    destination_iata: str
    flight_date: str
    results: list[TravelerResult]
    all_found: bool
