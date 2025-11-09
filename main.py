from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

app = FastAPI()

# Enable CORS - THIS IS CRITICAL!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for development)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

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

async def geocode(address: str) -> Location:
    """Geocode an address using Nominatim"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1},
                headers={"User-Agent": "EVL-Analyzer/1.0"}
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
            print(f"Geocoding error: {e}")
            return None

async def get_chargers(lat: float, lon: float, radius: int) -> list[Charger]:
    """Get EV chargers near a location using OpenChargeMap"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.openchargemap.io/v3/poi/",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "distance": radius,
                    "distanceunit": "km",
                    "maxresults": 50,
                    "compact": "true",
                    "verbose": "false"
                },
                timeout=10.0
            )
            data = response.json()
            
            chargers = []
            for poi in data:
                try:
                    # Calculate distance
                    import math
                    poi_lat = poi["AddressInfo"]["Latitude"]
                    poi_lon = poi["AddressInfo"]["Longitude"]
                    
                    # Haversine distance
                    R = 6371  # Earth radius in km
                    dlat = math.radians(poi_lat - lat)
                    dlon = math.radians(poi_lon - lon)
                    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(poi_lat)) * math.sin(dlon/2)**2
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                    distance = R * c
                    
                    # Get connections info
                    connections = poi.get("Connections", [])
                    num_connectors = len(connections)
                    max_power = max([conn.get("PowerKW", 0) for conn in connections], default=0)
                    
                    # Get network operator
                    network = poi.get("OperatorInfo", {}).get("Title", "Unknown") if poi.get("OperatorInfo") else "Unknown"
                    
                    chargers.append(Charger(
                        id=str(poi["ID"]),
                        name=poi["AddressInfo"].get("Title", "Unknown Location"),
                        distance_km=round(distance, 2),
                        connectors=num_connectors,
                        power_kw=int(max_power),
                        network=network
                    ))
                except Exception as e:
                    print(f"Error parsing charger: {e}")
                    continue
            
            # Sort by distance
            chargers.sort(key=lambda x: x.distance_km)
            return chargers
            
        except Exception as e:
            print(f"OpenChargeMap API error: {e}")
            return []

@app.get("/")
async def root():
    return {
        "service": "EVL Backend API",
        "status": "operational",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "cors_enabled": True}

@app.get("/api/analyze")
async def analyze(address: str = Query(..., description="Location to analyze"), 
                 radius: int = Query(5, description="Search radius in km")):
    """
    Analyze a location for EV charger installation potential
    """
    # Geocode the address
    location = await geocode(address)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Get nearby chargers
    chargers = await get_chargers(location.latitude, location.longitude, radius)
    
    # Calculate scores
    nearby_chargers = len([c for c in chargers if c.distance_km < 2])
    competition_score = max(0.3, min(0.9 - nearby_chargers * 0.1, 0.95))
    
    # Simple overall score (you can make this more sophisticated)
    overall_score = round(competition_score, 2)
    
    # Calculate ROI projection
    base_revenue = 50000
    estimated_revenue = int(base_revenue * overall_score)
    payback_period = round(25000 / max(estimated_revenue / 12, 1000), 1)  # Assuming 25k investment
    
    # Generate recommendations
    recommendations = []
    if overall_score >= 0.8:
        recommendations.append({"text": "Excellent location with high potential for EV charger installation"})
    elif overall_score >= 0.6:
        recommendations.append({"text": "Good location with moderate competition"})
    else:
        recommendations.append({"text": "High competition area - consider alternative locations"})
    
    recommendations.append({"text": f"Found {len(chargers)} existing chargers within {radius}km"})
    recommendations.append({"text": f"{nearby_chargers} chargers within 2km - {'low' if nearby_chargers < 3 else 'high'} competition"})
    
    return {
        "location": location.dict(),
        "chargers": [c.dict() for c in chargers],
        "scores": {
            "overall": overall_score,
            "competition": competition_score,
            "demand": round(min(0.85, overall_score + 0.1), 2),
            "accessibility": 0.75,
            "demographics": 0.70
        },
        "roi_projection": {
            "estimated_annual_revenue": estimated_revenue,
            "payback_period_years": payback_period,
            "monthly_revenue": int(estimated_revenue / 12)
        },
        "recommendations": recommendations
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
