from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import math
from typing import Optional, List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENCHARGEMAP_API_KEY = os.getenv("OPENCHARGEMAP_API_KEY", "")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")

print(f"API Keys: OCM={bool(OPENCHARGEMAP_API_KEY)}, Google={bool(GOOGLE_PLACES_API_KEY)}")
# Redeploy trigger

class Location(BaseModel):
    address: str
    latitude: float
    longitude: float

class Charger(BaseModel):
    id: str
    name: str
    distance_km: float
    connectors: int
    power_kw: int
    network: str = "Unknown"
    source: str = "Unknown"

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

async def geocode(address):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1},
                headers={"User-Agent": "EVL/2.0"},
                timeout=10.0
            )
            data = response.json()
            if not data:
                return None
            return Location(
                address=data[0].get("display_name", address),
                latitude=float(data[0]["lat"]),
                longitude=float(data[0]["lon"])
            )
        except Exception as e:
            print(f"Geocode error: {e}")
            return None

async def get_chargers(lat, lon, radius):
    all_chargers = []
    
    # OpenChargeMap
    try:
        async with httpx.AsyncClient() as client:
            params = {"latitude": lat, "longitude": lon, "distance": radius, "distanceunit": "km", "maxresults": 100}
            if OPENCHARGEMAP_API_KEY:
                params["key"] = OPENCHARGEMAP_API_KEY
                print("Using OCM API key")
            
            response = await client.get("https://api.openchargemap.io/v3/poi/", params=params, timeout=20.0)
            
            if response.status_code == 200:
                data = response.json()
                print(f"OCM returned {len(data)} POIs")
                for poi in data:
                    try:
                        poi_lat = poi["AddressInfo"]["Latitude"]
                        poi_lon = poi["AddressInfo"]["Longitude"]
                        distance = haversine_distance(lat, lon, poi_lat, poi_lon)
                        connections = poi.get("Connections", [])
                        max_power = max([c.get("PowerKW", 0) for c in connections], default=0)
                        network = poi.get("OperatorInfo", {}).get("Title", "Unknown") if poi.get("OperatorInfo") else "Unknown"
                        
                        all_chargers.append(Charger(
                            id=f"ocm_{poi['ID']}",
                            name=poi["AddressInfo"].get("Title", "Unknown"),
                            distance_km=round(distance, 2),
                            connectors=len(connections),
                            power_kw=int(max_power),
                            network=network,
                            source="OpenChargeMap"
                        ))
                    except:
                        continue
            else:
                print(f"OCM error: {response.status_code}")
    except Exception as e:
        print(f"OCM exception: {e}")
    
    # Google Places
    if GOOGLE_PLACES_API_KEY:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                    params={
                        "location": f"{lat},{lon}",
                        "radius": min(radius * 1000, 50000),
                        "type": "electric_vehicle_charging_station",
                        "key": GOOGLE_PLACES_API_KEY
                    },
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") in ["OK", "ZERO_RESULTS"]:
                        places = data.get("results", [])
                        print(f"Google returned {len(places)} places")
                        for place in places:
                            try:
                                place_lat = place["geometry"]["location"]["lat"]
                                place_lon = place["geometry"]["location"]["lng"]
                                distance = haversine_distance(lat, lon, place_lat, place_lon)
                                name = place.get("name", "Unknown")
                                
                                all_chargers.append(Charger(
                                    id=f"google_{place['place_id']}",
                                    name=name,
                                    distance_km=round(distance, 2),
                                    connectors=2,
                                    power_kw=50,
                                    network="Unknown",
                                    source="Google"
                                ))
                            except:
                                continue
        except Exception as e:
            print(f"Google exception: {e}")
    
    all_chargers.sort(key=lambda x: x.distance_km)
    print(f"Total chargers: {len(all_chargers)}")
    return all_chargers

@app.get("/")
async def root():
    return {"service": "EVL API", "version": "2.3", "status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/api/analyze")
async def analyze(address: str = Query(...), radius: int = Query(5)):
    print(f"\nAnalyzing: {address} ({radius}km)")
    
    location = await geocode(address)
    if not location:
        raise HTTPException(404, "Location not found")
    
    chargers = await get_chargers(location.latitude, location.longitude, radius)
    
    nearby = len([c for c in chargers if c.distance_km < 2])
    score = max(0.3, min(0.9 - nearby * 0.1, 0.95))
    
    return {
        "location": location.dict(),
        "chargers": [c.dict() for c in chargers[:100]],
        "scores": {"overall": round(score, 2), "competition": round(score, 2), "demand": 0.85, "accessibility": 0.75, "demographics": 0.70},
        "roi_projection": {"estimated_annual_revenue": int(50000 * score), "payback_period_years": round(25000 / max(50000 * score / 12, 1000), 1), "monthly_revenue": int(50000 * score / 12)},
        "recommendations": [{"text": f"Found {len(chargers)} chargers"}, {"text": f"{nearby} within 2km"}]
    }
