from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "version": "3.1"}

@app.get("/api/analyze")
async def analyze(address: str = Query(...), radius: int = Query(5)):
    ocm_key = os.getenv("OPENCHARGEMAP_API_KEY", "")
    
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
                    chargers.append({
                        "id": f"ocm_{poi['ID']}",
                        "name": poi["AddressInfo"].get("Title", "Unknown"),
                        "distance_km": 0,
                        "connectors": len(poi.get("Connections", [])),
                        "power_kw": 50,
                        "network": "Unknown",
                        "source": "OpenChargeMap"
                    })
                except:
                    pass
    
    return {
        "location": {"address": address, "latitude": lat, "longitude": lon},
        "chargers": chargers[:100],
        "scores": {"overall": 0.8, "competition": 0.8, "demand": 0.85, "accessibility": 0.75, "demographics": 0.70},
        "roi_projection": {"estimated_annual_revenue": 40000, "payback_period_years": 7.5, "monthly_revenue": 3333},
        "recommendations": [{"text": f"Found {len(chargers)} chargers"}]
    }
