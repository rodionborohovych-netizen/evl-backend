from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import math
from typing import Optional, List

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys
OPENCHARGEMAP_API_KEY = os.getenv("OPENCHARGEMAP_API_KEY", "")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")

print(f"🔑 OpenChargeMap API Key configured: {bool(OPENCHARGEMAP_API_KEY)}")
print(f"🔑 Google Places API Key configured: {bool(GOOGLE_PLACES_API_KEY)}")

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

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

async def geocode(address: str) -> Optional[Location]:
    async with httpx.AsyncClient() as client:
        try:
            print(f"🌍 Geocoding: {address}")
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1},
                headers={"User-Agent": "EVL-Analyzer/2.0"},
                timeout=10.0
            )
            data = response.json()
            if not data:
                print("❌ Geocoding failed - no results")
                return None
            
            location = Location(
                address=data[0].get("display_name", address),
                latitude=float(data[0]["lat"]),
                longitude=float(data[0]["lon"])
            )
            print(f"✅ Geocoded to: {location.latitude}, {location.longitude}")
            return location
        except Exception as e:
            print(f"❌ Geocoding error: {e}")
            return None

async def get_chargers(lat: float, lon: float, radius: int) -> List[Charger]:
    """Fetch chargers from OpenChargeMap"""
    all_chargers = []
    
    # OpenChargeMap
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "latitude": lat,
                "longitude": lon,
                "distance": radius,
                "distanceunit": "km",
                "maxresults": 100,
                "compact": "false"
            }
            
            if OPENCHARGEMAP_API_KEY:
                params["key"] = OPENCHARGEMAP_API_KEY
                print(f"🔑 Using OpenChargeMap API key")
            else:
                print(f"⚠️ No OpenChargeMap API key - limited results")
            
            print(f"📍 Fetching from OpenChargeMap (lat={lat}, lon={lon}, radius={radius}km)...")
            
            response = await client.get(
                "https://api.openchargemap.io/v3/poi/",
                params=params,
                timeout=20.0
            )
            
            print(f"📡 OpenChargeMap response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ OpenChargeMap error: {response.status_code}")
                print(f"Response: {response.text[:200]}")
            else:
                data = response.json()
                print(f"📊 OpenChargeMap returned {len(data)} POIs")
                
                for poi in data:
                    try:
                        poi_lat = poi["AddressInfo"]["Latitude"]
                        poi_lon = poi["AddressInfo"]["Longitude"]
                        distance = haversine_distance(lat, lon, poi_lat, poi_lon)
                        
                        connections = poi.get("Connections", [])
                        num_connectors = len(connections)
                        max_power = max([conn.get("PowerKW", 0) for conn in connections], default=0)
                        network = poi.get("OperatorInfo", {}).get("Title", "Unknown") if poi.get("OperatorInfo") else "Unknown"
                        
                        all_chargers.append(Charger(
                            id=f"ocm_{poi['ID']}",
                            name=poi["AddressInfo"].get("Title", "Unknown Location"),
                            distance_km=round(distance, 2),
                            connectors=num_connectors,
                            power_kw=int(max_power),
                            network=network,
                            source="OpenChargeMap"
                        ))
                    except Exception as e:
                        print(f"⚠️ Error parsing charger: {e}")
                        continue
                
                print(f"✅ Parsed {len(all_chargers)} chargers from OpenChargeMap")
    except Exception as e:
        print(f"❌ OpenChargeMap request failed: {e}")
    
    # Google Places
    if GOOGLE_PLACES_API_KEY:
        try:
            async with httpx.AsyncClient() as client:
                print(f"📍 Fetching from Google Places...")
                
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
                
                print(f"📡 Google Places response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    places = data.get("results", [])
                    print(f"📊 Google Places returned {len(places)} places")
                    
                    for place in places:
                        try:
                            place_lat = place["geometry"]["location"]["lat"]
                            place_lon = place["geometry"]["location"]["lng"]
                            distance = haversine_distance(lat, lon, place_lat, place_lon)
                            
                            name = place.get("name", "Unknown")
                            network = "Unknown"
                            for op in ["Tesla", "BP", "Shell", "Ionity", "ChargePoint", "Pod Point"]:
                                if op.lower() in name.lower():
                                    network = op
                                    break
                            
                            all_chargers.append(Charger(
                                id=f"google_{place['place_id']}",
                                name=name,
                                distance_km=round(distance, 2),
                                connectors=2,
                                power_kw=50,
                                network=network,
                                source="Google Places"
                            ))
                        except Exception as e:
                            continue
                    
                    print(f"✅ Added {len([c for c in all_chargers if c.source == 'Google Places'])} chargers from Google Places")
        except Exception as e:
            print(f"❌ Google Places request failed: {e}")
    else:
        print(f"⚠️ Google Places API key not configured")
    
    print(f"🎯 Total chargers found: {len(all_chargers)}")
    
    all_chargers.sort(key=lambda x: x.distance_km)
    return all_chargers

@app.get("/")
async def root():
    return {
        "service": "EVL Backend API - Debug Version",
        "status": "operational",
        "version": "2.2.0-debug",
        "api_keys": {
            "openchargemap": bool(OPENCHARGEMAP_API_KEY),
            "google_places": bool(GOOGLE_PLACES_API_KEY)
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "cors_enabled": True,
        "api_keys_configured": {
            "openchargemap": bool(OPENCHARGEMAP_API_KEY),
            "google_places": bool(GOOGLE_PLACES_API_KEY)
        }
    }

@app.get("/api/analyze")
async def analyze(
    address: str = Query(..., description="Location to analyze"), 
    radius: int = Query(5, description="Search radius in km", ge=1, le=50)
):
    """Analyze a location for EV charger installation potential"""
    
    print(f"\n{'='*60}")
    print(f"🔍 NEW REQUEST: {address} (radius: {radius}km)")
    print(f"{'='*60}")
    
    # Geocode
    location = await geocode(address)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Get chargers
    chargers = await get_chargers(location.latitude, location.longitude, radius)
    
    print(f"\n📊 FINAL RESULTS:")
    print(f"   Location: {location.address}")
    print(f"   Chargers found: {len(chargers)}")
    if chargers:
        print(f"   Closest charger: {chargers[0].name} ({chargers[0].distance_km}km)")
        sources = list(set([c.source for c in chargers]))
        print(f"   Sources: {', '.join(sources)}")
    print(f"{'='*60}\n")
    
    # Calculate scores
    nearby_chargers = len([c for c in chargers if c.distance_km < 2])
    competition_score = max(0.3, min(0.9 - nearby_chargers * 0.1, 0.95))
    overall_score = round(competition_score, 2)
    
    # ROI
    base_revenue = 50000
    estimated_revenue = int(base_revenue * overall_score)
    payback_period = round(25000 / max(estimated_revenue / 12, 1000), 1)
    
    # Recommendations
    recommendations = []
    
    if len(chargers) == 0:
        recommendations.append({"text": "⚠️ No chargers found - check API keys and logs"})
    else:
        sources_used = list(set([c.source for c in chargers]))
        recommendations.append({"text": f"📊 Data from: {', '.join(sources_used)}"})
    
    if overall_score >= 0.8:
        recommendations.append({"text": "✅ Excellent location - low competition"})
    elif overall_score >= 0.6:
        recommendations.append({"text": "✅ Good location - moderate competition"})
    else:
        recommendations.append({"text": "⚠️ High competition"})
    
    recommendations.append({"text": f"Found {len(chargers)} chargers within {radius}km"})
    
    return {
        "location": location.dict(),
        "chargers": [c.dict() for c in chargers[:50]],
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
        "recommendations": recommendations,
        "debug_info": {
            "total_chargers": len(chargers),
            "api_keys_used": {
                "openchargemap": bool(OPENCHARGEMAP_API_KEY),
                "google_places": bool(GOOGLE_PLACES_API_KEY)
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
