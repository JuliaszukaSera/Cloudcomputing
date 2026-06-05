import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from app.models import FlightSearchRequest, FlightMatchResponse
from app.flight_service import search_flights_for_group

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FlightMatch",
    description="Dopasuj loty dla grupy podróżujących z różnych miast do wspólnego celu",
    version="1.0.0",
)

templates = Jinja2Templates(directory="templates")

# Runtime storage — nadpisuje zmienną środowiskową gdy ustawiony przez UI
_runtime_api_key: str = ""


class ApiKeyRequest(BaseModel):
    api_key: str


def get_api_key() -> str:
    key = _runtime_api_key or os.environ.get("SERPAPI_KEY", "")
    if not key:
        raise HTTPException(
            status_code=503,
            detail="Brak klucza SerpAPI. Skonfiguruj go w panelu ustawień lub ustaw zmienną SERPAPI_KEY.",
        )
    return key


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "FlightMatch"}


@app.get("/api/config")
async def get_config():
    env_key = os.environ.get("SERPAPI_KEY", "")
    active = _runtime_api_key or env_key
    return {
        "api_key_configured": bool(active),
        "source": "runtime" if _runtime_api_key else ("env" if env_key else "none"),
        # zwracamy tylko maskę klucza (4 ostatnie znaki)
        "api_key_hint": f"****{active[-4:]}" if active else None,
    }


@app.post("/api/config")
async def set_config(payload: ApiKeyRequest):
    global _runtime_api_key
    key = payload.api_key.strip()
    if not key:
        raise HTTPException(status_code=422, detail="Klucz API nie może być pusty.")
    _runtime_api_key = key
    logger.info("Klucz API AviationStack zaktualizowany przez użytkownika (hint: ****%s)", key[-4:])
    return {"status": "ok", "message": "Klucz API zapisany. Możesz teraz wyszukiwać loty."}


@app.post("/api/search", response_model=FlightMatchResponse)
async def search_flights(payload: FlightSearchRequest):
    api_key = get_api_key()

    flight_date_str = payload.flight_date.isoformat()
    dest = payload.destination_iata.upper()

    logger.info(
        "Szukam lotów do %s na %s dla %d podróżujących",
        dest, flight_date_str, len(payload.travelers),
    )

    results = await search_flights_for_group(
        api_key=api_key,
        travelers=payload.travelers,
        destination_iata=dest,
        flight_date=flight_date_str,
    )

    all_found = all(bool(r.flights) for r in results)

    return FlightMatchResponse(
        destination_iata=dest,
        flight_date=flight_date_str,
        results=results,
        all_found=all_found,
    )
