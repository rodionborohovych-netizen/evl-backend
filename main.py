from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import math

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def distance(lat1, lon1, lat2, lon2):
    """Calculate distance in km between two coordinates"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return round(R * c, 2)

@app.get("/")
def root():
    return {"status": "ok", "version": "3.2-IMPROVED"}

@app.get("/api/analyze")
async def analyze(address: str = Query(...), radius: int = Query(5)):
    ocm_key = os.getenv("OPENCHARGEMAP_API_KEY", "")
    google_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    
    # Geocode
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "EVL"},
            timeout=10.0
        )
        data = r.json()
        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
    
    chargers = []
    
    # OpenChargeMap
    async with httpx.AsyncClient() as client:
        params = {
            "latitude": lat,
            "longitude": lon,
            "distance": radius,
            "distanceunit": "km",
            "maxresults": 100
        }
        if ocm_key:
            params["key"] = ocm_key
        
        r = await client.get("https://api.openchargemap.io/v3/poi/", params=params, timeout=20.0)
        
        if r.status_code == 200:
            data = r.json()
            for poi in data:
                try:
                    poi_lat = poi["AddressInfo"]["Latitude"]
                    poi_lon = poi["AddressInfo"]["Longitude"]
                    dist = distance(lat, lon, poi_lat, poi_lon)
                    
                    # Get real power from connections
                    connections = poi.get("Connections", [])
                    power_values = [c.get("PowerKW", 0) for c in connections if c.get("PowerKW")]
                    max_power = int(max(power_values)) if power_values else 7
                    
                    # Get network name
                    network = "Unknown"
                    if poi.get("OperatorInfo"):
                        network = poi["OperatorInfo"].get("Title", "Unknown")
                    
                    chargers.append({
                        "id": f"ocm_{poi['ID']}",
                        "name": poi["AddressInfo"].get("Title", "Unknown"),
                        "distance_km": dist,
                        "connectors": len(connections),
                        "power_kw": max_power,
                        "network": network,
                        "source": "OpenChargeMap"
                    })
                except:
                    pass
    
    # Google Places (if key exists)
    if google_key:
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(
                    "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                    params={
                        "location": f"{lat},{lon}",
                        "radius": min(radius * 1000, 50000),
                        "type": "electric_vehicle_charging_station",
                        "key": google_key
                    },
                    timeout=15.0
                )
                
                if r.status_code == 200:
                    data = r.json()
                    if data.get("status") in ["OK", "ZERO_RESULTS"]:
                        for place in data.get("results", []):
                            try:
                                plat = place["geometry"]["location"]["lat"]
                                plon = place["geometry"]["location"]["lng"]
                                dist = distance(lat, lon, plat, plon)
                                
                                name = place.get("name", "Unknown")
                                network = "Unknown"
                                # Try to extract network from name
                                for net in ["Tesla", "BP", "Shell", "Ionity", "ChargePoint"]:
                                    if net.lower() in name.lower():
                                        network = net
                                        break
                                
                                chargers.append({
                                    "id": f"google_{place['place_id']}",
                                    "name": name,
                                    "distance_km": dist,
                                    "connectors": 2,
                                    "power_kw": 50,
                                    "network": network,
                                    "source": "Google"
                                })
                            except:
                                pass
            except:
                pass
    
    # Sort by distance
    chargers.sort(key=lambda x: x["distance_km"])
    
    # Calculate scores
    nearby = len([c for c in chargers if c["distance_km"] < 2])
    score = max(0.3, min(0.9 - nearby * 0.1, 0.95))
    
    return {
        "location": {"address": address, "latitude": lat, "longitude": lon},
        "chargers": chargers[:100],
        "scores": {
            "overall": round(score, 2),
            "competition": round(score, 2),
            "demand": 0.85,
            "accessibility": 0.75,
            "demographics": 0.70
        },
        "roi_projection": {
            "estimated_annual_revenue": int(50000 * score),
            "payback_period_years": round(25000 / max(50000 * score / 12, 1000), 1),
            "monthly_revenue": int(50000 * score / 12)
        },
        "recommendations": [
            {"text": f"Found {len(chargers)} chargers"},
            {"text": f"{nearby} within 2km"}
        ]
    }










