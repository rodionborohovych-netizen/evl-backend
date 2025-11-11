from fastapi import FastAPI, Query, HTTPException
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

OCM_KEY = os.getenv("OPENCHARGEMAP_API_KEY", "")
GOOGLE_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")

print("=" * 60)
print("🚀 EVL BACKEND STARTING")
print(f"🔑 OpenChargeMap Key: {'✅ SET' if OCM_KEY else '❌ NOT SET'}")
print(f"🔑 Google Places Key: {'✅ SET' if GOOGLE_KEY else '❌ NOT SET'}")
print("=" * 60)

def distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@app.get("/")
def root():
    return {
        "service": "EVL Backend",
        "version": "3.0-WORKING",
        "keys": {
            "ocm": bool(OCM_KEY),
            "google": bool(GOOGLE_KEY)
        }
    }

@app.get("/test")
def test():
    return {
        "ocm_key_length": len(OCM_KEY),
        "google_key_length": len(GOOGLE_KEY),
        "ocm_key_set": bool(OCM_KEY),
        "google_key_set": bool(GOOGLE_KEY)
    }

@app.get("/api/analyze")
async def analyze(address: str = Query(...), radius: int = Query(5)):
    print(f"\n{'='*60}")
    print(f"📍 NEW REQUEST: {address} (radius: {radius}km)")
    
    # Geocode
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1},
                headers={"User-Agent": "EVL/3.0"},
                timeout=10.0
            )
            data = r.json()
            if not data:
                raise HTTPException(404, "Location not found")
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            print(f"✅ Geocoded: {lat}, {lon}")
        except Exception as e:
            print(f"❌ Geocode failed: {e}")
            raise HTTPException(500, f"Geocoding failed: {e}")
    
    chargers = []
    
    # Try OpenChargeMap
    async with httpx.AsyncClient() as client:
        try:
            url = "https://api.openchargemap.io/v3/poi/"
            params = {
                "latitude": lat,
                "longitude": lon,
                "distance": radius,
                "distanceunit": "km",
                "maxresults": 100,
                "compact": "false"
            }
            
            if OCM_KEY:
                params["key"] = OCM_KEY
                print(f"🔑 Using OCM API key")
            else:
                print(f"⚠️  No OCM API key")
            
            print(f"🌐 Fetching: {url}")
            print(f"📦 Params: {params}")
            
            r = await client.get(url, params=params, timeout=30.0)
            print(f"📡 OCM Status: {r.status_code}")
            print(f"📦 OCM Content-Type: {r.headers.get('content-type')}")
            print(f"📏 OCM Content Length: {len(r.content)} bytes")
            
            if r.status_code == 200:
                try:
                    data = r.json()
                    print(f"✅ OCM Parsed: {len(data)} POIs")
                    
                    for poi in data:
                        try:
                            poi_lat = poi["AddressInfo"]["Latitude"]
                            poi_lon = poi["AddressInfo"]["Longitude"]
                            dist = distance(lat, lon, poi_lat, poi_lon)
                            
                            chargers.append({
                                "id": f"ocm_{poi['ID']}",
                                "name": poi["AddressInfo"].get("Title", "Unknown"),
                                "distance_km": round(dist, 2),
                                "connectors": len(poi.get("Connections", [])),
                                "power_kw": max([c.get("PowerKW", 0) for c in poi.get("Connections", [])], default=0),
                                "network": poi.get("OperatorInfo", {}).get("Title", "Unknown") if poi.get("OperatorInfo") else "Unknown",
                                "source": "OpenChargeMap"
                            })
                        except:
                            continue
                    
                    print(f"✅ Parsed {len(chargers)} chargers from OCM")
                except Exception as e:
                    print(f"❌ OCM JSON Parse Error: {e}")
                    print(f"📄 Response preview: {r.text[:500]}")
            else:
                print(f"❌ OCM HTTP Error: {r.status_code}")
                print(f"📄 Response: {r.text[:500]}")
        except Exception as e:
            print(f"❌ OCM Exception: {e}")
    
    # Try Google Places
    if GOOGLE_KEY and len(chargers) < 20:
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(
                    "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                    params={
                        "location": f"{lat},{lon}",
                        "radius": min(radius * 1000, 50000),
                        "type": "electric_vehicle_charging_station",
                        "key": GOOGLE_KEY
                    },
                    timeout=15.0
                )
                
                if r.status_code == 200:
                    data = r.json()
                    if data.get("status") in ["OK", "ZERO_RESULTS"]:
                        places = data.get("results", [])
                        print(f"✅ Google: {len(places)} places")
                        
                        for p in places:
                            try:
                                plat = p["geometry"]["location"]["lat"]
                                plon = p["geometry"]["location"]["lng"]
                                dist = distance(lat, lon, plat, plon)
                                
                                chargers.append({
                                    "id": f"google_{p['place_id']}",
                                    "name": p.get("name", "Unknown"),
                                    "distance_km": round(dist, 2),
                                    "connectors": 2,
                                    "power_kw": 50,
                                    "network": "Unknown",
                                    "source": "Google"
                                })
                            except:
                                continue
                    else:
                        print(f"⚠️  Google status: {data.get('status')}")
            except Exception as e:
                print(f"❌ Google Exception: {e}")
    
    print(f"📊 TOTAL CHARGERS: {len(chargers)}")
    print(f"{'='*60}\n")
    
    nearby = len([c for c in chargers if c["distance_km"] < 2])
    score = max(0.3, min(0.9 - nearby * 0.1, 0.95))
    
    return {
        "location": {"address": address, "latitude": lat, "longitude": lon},
        "chargers": sorted(chargers, key=lambda x: x["distance_km"])[:100],
        "scores": {"overall": round(score, 2), "competition": round(score, 2), "demand": 0.85, "accessibility": 0.75, "demographics": 0.70},
        "roi_projection": {"estimated_annual_revenue": int(50000 * score), "payback_period_years": round(25000 / max(50000 * score / 12, 1000), 1), "monthly_revenue": int(50000 * score / 12)},
        "recommendations": [{"text": f"Found {len(chargers)} chargers"}, {"text": f"{nearby} within 2km"}]
    }
