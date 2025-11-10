"""Robust EVL backend service.

Provides a FastAPI application that aggregates EV charging station
information from multiple providers.
"""
from __future__ import annotations

import asyncio
import logging
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

LOGGER = logging.getLogger("evl")
logging.basicConfig(level=logging.INFO, format="%(message)s")

OPENCHARGEMAP_ENDPOINT = "https://api.openchargemap.io/v3/poi/"
NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"
GOOGLE_PLACES_ENDPOINT = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
USER_AGENT = "evl-backend/1.0"


def miles_to_km(miles: float) -> float:
    return miles * 1.60934


def miles_to_meters(miles: float) -> float:
    return miles * 1609.34


class ChargerLocation(BaseModel):
    id: str = Field(description="Unique identifier for the charger within the provider")
    source: str = Field(description="The provider that returned the charger")
    name: str = Field(description="The human friendly name of the charger")
    latitude: float
    longitude: float
    distance_km: float = Field(description="Distance from the query location in kilometers")
    connectors: int = Field(description="Number of connectors reported by the provider", ge=0)
    power_kw: Optional[int] = Field(default=None, description="Maximum reported power in kW")
    network: str = Field(default="Unknown", description="Network/operator name if provided")
    address: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class LocationInfo(BaseModel):
    address: Optional[str]
    latitude: float
    longitude: float


class ScoreBreakdown(BaseModel):
    overall: float
    competition: float
    demand: float
    accessibility: float
    demographics: float


class ROIProjection(BaseModel):
    estimated_annual_revenue: int
    payback_period_years: float
    monthly_revenue: int


class Recommendation(BaseModel):
    text: str


class DebugInfo(BaseModel):
    address_provided: Optional[str]
    coordinates: Tuple[float, float]
    api_keys_working: Dict[str, bool]
    providers_queried: List[str]
    total_results_considered: int


class AnalyzeResponse(BaseModel):
    location: LocationInfo
    chargers: List[ChargerLocation]
    scores: ScoreBreakdown
    roi_projection: ROIProjection
    recommendations: List[Recommendation]
    debug_info: DebugInfo


app = FastAPI(title="EVL Backend", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def geocode_address(client: httpx.AsyncClient, address: str) -> Tuple[float, float]:
    LOGGER.info("🔍 Analyzing: %s", address)
    params = {"q": address, "format": "json", "limit": 1}
    headers = {"User-Agent": USER_AGENT}
    response = await client.get(NOMINATIM_ENDPOINT, params=params, headers=headers, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    if not data:
        raise ValueError("Address could not be geocoded")
    first = data[0]
    lat = float(first["lat"])
    lon = float(first["lon"])
    LOGGER.info("📍 Coordinates: %.4f, %.4f", lat, lon)
    return lat, lon


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute the distance in kilometers between two coordinates."""
    radius = 6371.0
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


async def fetch_openchargemap(
    client: httpx.AsyncClient,
    latitude: float,
    longitude: float,
    radius_miles: float,
    api_key: Optional[str],
) -> Tuple[List[ChargerLocation], bool]:
    if not api_key:
        LOGGER.info("🔑 OpenChargeMap: No API key provided, using anonymous quota…")
    else:
        LOGGER.info("🔑 OpenChargeMap: Trying WITH API key…")

    params = {
        "output": "json",
        "latitude": latitude,
        "longitude": longitude,
        "distance": round(miles_to_km(radius_miles), 3),
        "distanceunit": "KM",
        "maxresults": 200,
    }
    headers = {"User-Agent": USER_AGENT}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        response = await client.get(
            OPENCHARGEMAP_ENDPOINT,
            params=params,
            headers=headers,
            timeout=45.0,
        )
        response.raise_for_status()
        results = response.json()
    except Exception as exc:  # pragma: no cover - network issues
        LOGGER.warning("⚠️ OpenChargeMap failed: %s", exc)
        return [], False

    chargers: List[ChargerLocation] = []
    for item in results:
        address_info = item.get("AddressInfo", {})
        poi_lat = address_info.get("Latitude")
        poi_lon = address_info.get("Longitude")
        if poi_lat is None or poi_lon is None:
            continue

        connections = item.get("Connections", []) or []
        power_values = [conn.get("PowerKW") for conn in connections if conn.get("PowerKW") is not None]
        max_power = int(max(power_values)) if power_values else None
        network = "Unknown"
        if isinstance(item.get("OperatorInfo"), dict):
            network = item["OperatorInfo"].get("Title", "Unknown") or "Unknown"

        chargers.append(
            ChargerLocation(
                id=f"ocm_{item.get('ID')}",
                source="OpenChargeMap",
                name=address_info.get("Title", "Unknown Charger"),
                latitude=float(poi_lat),
                longitude=float(poi_lon),
                distance_km=round(haversine_distance(latitude, longitude, float(poi_lat), float(poi_lon)), 2),
                connectors=len(connections),
                power_kw=max_power,
                network=network,
                address=address_info.get("AddressLine1"),
                details={"openchargemap_id": item.get("ID")},
            )
        )

    LOGGER.info("✅ OpenChargeMap: %d POIs", len(chargers))
    return chargers, True


async def fetch_google_places(
    client: httpx.AsyncClient,
    latitude: float,
    longitude: float,
    radius_miles: float,
    api_key: Optional[str],
) -> Tuple[List[ChargerLocation], bool]:
    if not api_key:
        LOGGER.info("🔑 Google Places: Skipped (missing API key)")
        return [], False

    LOGGER.info("📍 Google Places: Fetching…")
    radius_meters = min(int(miles_to_meters(radius_miles)), 50000)

    params = {
        "location": f"{latitude},{longitude}",
        "radius": radius_meters,
        "keyword": "ev charger",
        "type": "point_of_interest",
        "key": api_key,
    }

    try:
        response = await client.get(
            GOOGLE_PLACES_ENDPOINT,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=45.0,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # pragma: no cover - network issues
        LOGGER.warning("⚠️ Google Places failed: %s", exc)
        return [], False

    status = payload.get("status")
    if status not in {"OK", "ZERO_RESULTS"}:
        LOGGER.warning("⚠️ Google Places returned status %s", status)
        return [], False

    if status == "ZERO_RESULTS":
        LOGGER.info("✅ Google Places: zero results returned within %dm", radius_meters)
        return [], True

    chargers: List[ChargerLocation] = []
    for result in payload.get("results", []):
        geometry = result.get("geometry", {}).get("location", {})
        lat = geometry.get("lat")
        lon = geometry.get("lng")
        if lat is None or lon is None:
            continue

        chargers.append(
            ChargerLocation(
                id=f"google_{result.get('place_id')}",
                source="Google Places",
                name=result.get("name", "Unknown Charger"),
                latitude=float(lat),
                longitude=float(lon),
                distance_km=round(haversine_distance(latitude, longitude, float(lat), float(lon)), 2),
                connectors=2,
                power_kw=50,
                network="Unknown",
                address=result.get("vicinity"),
                details={"place_id": result.get("place_id")},
            )
        )

    LOGGER.info("✅ Google Places: %d chargers", len(chargers))
    return chargers, True


def deduplicate_chargers(chargers: List[ChargerLocation]) -> List[ChargerLocation]:
    seen: Dict[str, bool] = {}
    deduped: List[ChargerLocation] = []
    for charger in sorted(chargers, key=lambda c: c.distance_km):
        key = charger.id or f"{charger.source}:{round(charger.latitude, 5)}:{round(charger.longitude, 5)}"
        if key in seen:
            continue
        seen[key] = True
        deduped.append(charger)
    return deduped


async def gather_data(
    latitude: float,
    longitude: float,
    radius_miles: float,
) -> Tuple[List[ChargerLocation], Dict[str, bool]]:
    openchargemap_key = os.getenv("OPENCHARGEMAP_API_KEY")
    google_key = os.getenv("GOOGLE_PLACES_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")

    async with httpx.AsyncClient() as client:
        tasks = [
            fetch_openchargemap(client, latitude, longitude, radius_miles, openchargemap_key),
            fetch_google_places(client, latitude, longitude, radius_miles, google_key),
        ]
        results = await asyncio.gather(*tasks)

    chargers: List[ChargerLocation] = []
    key_status = {
        "openchargemap": results[0][1],
        "google_places": results[1][1],
    }

    for provider_chargers, _ in results:
        chargers.extend(provider_chargers)

    chargers = deduplicate_chargers(chargers)
    LOGGER.info("📊 Total unique chargers: %d", len(chargers))
    return chargers, key_status


@app.get("/api/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/analyze", response_model=AnalyzeResponse)
async def analyze(
    address: Optional[str] = Query(None, description="Address to search around"),
    radius: float = Query(5.0, ge=0.1, le=50.0, description="Radius to search in miles"),
    latitude: Optional[float] = Query(None, description="Latitude override"),
    longitude: Optional[float] = Query(None, description="Longitude override"),
) -> AnalyzeResponse:
    if address is None and (latitude is None or longitude is None):
        raise HTTPException(status_code=400, detail="Provide either an address or latitude/longitude")

    async with httpx.AsyncClient() as client:
        lat = latitude
        lon = longitude
        if address and (lat is None or lon is None):
            try:
                lat, lon = await geocode_address(client, address)
            except Exception as exc:  # pragma: no cover - network
                raise HTTPException(status_code=500, detail=str(exc)) from exc
        elif lat is not None and lon is not None:
            LOGGER.info("📍 Coordinates provided: %.4f, %.4f", lat, lon)

    if lat is None or lon is None:
        raise HTTPException(status_code=500, detail="Coordinates could not be determined")

    chargers, key_status = await gather_data(lat, lon, radius)

    nearby = len([charger for charger in chargers if charger.distance_km < 2])
    score = max(0.3, min(0.9 - nearby * 0.1, 0.95))
    annual_revenue = int(50000 * score)
    monthly_revenue = int(annual_revenue / 12)
    payback_period_years = round(25000 / max(monthly_revenue, 1000), 1)

    location_info = LocationInfo(address=address, latitude=lat, longitude=lon)
    debug = DebugInfo(
        address_provided=address,
        coordinates=(lat, lon),
        api_keys_working=key_status,
        providers_queried=[provider for provider, worked in key_status.items() if worked],
        total_results_considered=len(chargers),
    )

    return AnalyzeResponse(
        location=location_info,
        chargers=chargers[:100],
        scores=ScoreBreakdown(
            overall=round(score, 2),
            competition=round(score, 2),
            demand=0.85,
            accessibility=0.75,
            demographics=0.70,
        ),
        roi_projection=ROIProjection(
            estimated_annual_revenue=annual_revenue,
            payback_period_years=payback_period_years,
            monthly_revenue=monthly_revenue,
        ),
        recommendations=[
            Recommendation(text=f"Found {len(chargers)} chargers"),
            Recommendation(text=f"{nearby} within 2km"),
        ],
        debug_info=debug,
    )


@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "EVL backend is running"}


@app.get("/test")
async def test() -> Dict[str, Dict[str, Any]]:
    openchargemap_key = os.getenv("OPENCHARGEMAP_API_KEY", "")
    google_key = os.getenv("GOOGLE_PLACES_API_KEY", "") or os.getenv("GOOGLE_MAPS_API_KEY", "")
    return {
        "api_keys_set": {
            "openchargemap": bool(openchargemap_key),
            "google": bool(google_key),
        },
        "api_key_values": {
            "ocm_length": len(openchargemap_key),
            "google_length": len(google_key),
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
