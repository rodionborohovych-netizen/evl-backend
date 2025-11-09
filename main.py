from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx, asyncio, time
from datetime import datetime

app = FastAPI(title="EVL API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
OPEN_CHARGE_MAP_KEY = "553131e9-33b0-49ee-834b-416fc9d4202a"
last_call = 0

class Location(BaseModel):
    latitude: float
    longitude: float
    address: str
    city: str
    country: str

class Charger(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    distance_km: float
    connectors: int
    power_kw: float

async def geocode(address):
    global last_call
    await asyncio.sleep(max(0, 1 - (time.time() - last_call)))
    last_call = time.time()
    async with httpx.AsyncClient() as c:
        r = await c.get("https://nominatim.openstreetmap.org/search", params={"q": address, "format": "json", "limit": 1}, headers={"User-Agent": "EVL/1.0"}, timeout=10.0)
        d = r.json()
        if d: return Location(latitude=float(d[0]["lat"]), longitude=float(d[0]["lon"]), address=d[0]["display_name"], city="", country="")

async def get_chargers(lat, lng, radius):
    async with httpx.AsyncClient() as c:
        r = await c.get("https://api.openchargemap.io/v3/poi/", params={"output": "json", "latitude": lat, "longitude": lng, "distance": radius, "maxresults": 50, "key": OPEN_CHARGE_MAP_KEY}, timeout=15.0)
        result = []
        for p in r.json():
            if not p.get("AddressInfo"): continue
            a = p["AddressInfo"]
            result.append(Charger(id=str(p["ID"]), name=a.get("Title", "Unknown"), latitude=a["Latitude"], longitude=a["Longitude"], distance_km=round(a.get("Distance", 0), 2), connectors=len(p.get("Connections", [])), power_kw=max([c.get("PowerKW", 0) for c in p.get("Connections", [])] or [0])))
        return result

@app.get("/")
async def root():
    return {"service": "EVL API", "status": "operational"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/api/analyze")
async def analyze(address: str = Query(...), radius: int = Query(5)):
    loc = await geocode(address)
    if not loc: raise HTTPException(404, "Not found")
    chargers = await get_chargers(loc.latitude, loc.longitude, radius)
    score = max(0.3, min(0.9 - len([c for c in chargers if c.distance_km < 2]) * 0.1, 0.95))
    return {"location": loc.dict(), "chargers": [c.dict() for c in chargers], "scores": {"overall": round(score, 2)}, "roi_projection": {"estimated_annual_revenue": int(50000 * score)}, "recommendations": [{"text": f"Score: {int(score*100)}%"}, {"text": f"Found {len(chargers)} chargers"}]}
