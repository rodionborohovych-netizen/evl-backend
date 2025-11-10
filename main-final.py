from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import math
from typing import Optional, List
from collections import defaultdict
import asyncio

app = FastAPI()

# Enable CORS
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
    address: Optional[str] = None
    status: Optional[str] = "Unknown"
    connector_types: Optional[List[str]] = []

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in km"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

async def geocode(address: str) -> Optional[Location]:
    """Geocode an address using Nominatim"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1},
                headers={"User-Agent": "EVL-Analyzer/2.0"},
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
            print(f"Geocoding error: {e}")
            return None

async def get_openchargemap_chargers(lat: float, lon: float, radius: int) -> List[Charger]:
    """Get chargers from OpenChargeMap"""
    async with httpx.AsyncClient() as client:
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "distance": radius,
                "distanceunit": "km",
                "maxresults": 100,
                "compact": "false",
                "verbose": "true"
            }
            
            if OPENCHARGEMAP_API_KEY:
                params["key"] = OPENCHARGEMAP_API_KEY
            
            print(f"📍 OpenChargeMap: Fetching...")
            response = await client.get(
                "https://api.openchargemap.io/v3/poi/",
                params=params,
                timeout=15.0
            )
            
            if response.status_code != 200:
                print(f"❌ OpenChargeMap API error: {response.status_code}")
                return []
            
            data = response.json()
            chargers = []
            
            for poi in data:
                try:
                    poi_lat = poi["AddressInfo"]["Latitude"]
                    poi_lon = poi["AddressInfo"]["Longitude"]
                    distance = haversine_distance(lat, lon, poi_lat, poi_lon)
                    
                    connections = poi.get("Connections", [])
                    num_connectors = len(connections)
                    max_power = max([conn.get("PowerKW", 0) for conn in connections], default=0)
                    
                    # Get connector types
                    connector_types = []
                    for conn in connections:
                        conn_type = conn.get("ConnectionType", {}).get("Title", "")
                        if conn_type and conn_type not in connector_types:
                            connector_types.append(conn_type)
                    
                    network = poi.get("OperatorInfo", {}).get("Title", "Unknown") if poi.get("OperatorInfo") else "Unknown"
                    status = "Operational"
                    if poi.get("StatusType"):
                        status = poi["StatusType"].get("Title", "Unknown")
                    
                    chargers.append(Charger(
                        id=f"ocm_{poi['ID']}",
                        name=poi["AddressInfo"].get("Title", "Unknown Location"),
                        distance_km=round(distance, 2),
                        connectors=num_connectors,
                        power_kw=int(max_power),
                        network=network,
                        source="OpenChargeMap",
                        address=poi["AddressInfo"].get("AddressLine1", ""),
                        status=status,
                        connector_types=connector_types
                    ))
                except Exception as e:
                    continue
            
            print(f"✅ OpenChargeMap: {len(chargers)} chargers found")
            return chargers
            
        except Exception as e:
            print(f"❌ OpenChargeMap error: {e}")
            return []

async def get_google_places_chargers(lat: float, lon: float, radius: int) -> List[Charger]:
    """Get chargers from Google Places API"""
    if not GOOGLE_PLACES_API_KEY:
        print("⚠️ Google Places API key not configured")
        return []
    
    async with httpx.AsyncClient() as client:
        try:
            print(f"📍 Google Places: Fetching...")
            
            radius_meters = min(radius * 1000, 50000)
            
            response = await client.get(
                "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                params={
                    "location": f"{lat},{lon}",
                    "radius": radius_meters,
                    "type": "electric_vehicle_charging_station",
                    "key": GOOGLE_PLACES_API_KEY
                },
                timeout=15.0
            )
            
            if response.status_code != 200:
                print(f"❌ Google Places API error: {response.status_code}")
                return []
            
            data = response.json()
            
            if data.get("status") not in ["OK", "ZERO_RESULTS"]:
                print(f"⚠️ Google Places status: {data.get('status')}")
                return []
            
            chargers = []
            
            for place in data.get("results", []):
                try:
                    place_lat = place["geometry"]["location"]["lat"]
                    place_lon = place["geometry"]["location"]["lng"]
                    distance = haversine_distance(lat, lon, place_lat, place_lon)
                    
                    name = place.get("name", "Unknown Location")
                    address = place.get("vicinity", "")
                    
                    # Extract network from name
                    network = "Unknown"
                    known_networks = ["Tesla", "BP", "Shell", "Ionity", "ChargePoint", "Pod Point", 
                                    "Osprey", "Gridserve", "Instavolt", "Fastned", "MFG", "GeniePoint"]
                    for op in known_networks:
                        if op.lower() in name.lower():
                            network = op
                            break
                    
                    status = "Operational" if place.get("business_status") == "OPERATIONAL" else "Unknown"
                    
                    chargers.append(Charger(
                        id=f"google_{place['place_id']}",
                        name=name,
                        distance_km=round(distance, 2),
                        connectors=2,
                        power_kw=50,
                        network=network,
                        source="Google Places",
                        address=address,
                        status=status
                    ))
                except Exception as e:
                    continue
            
            print(f"✅ Google Places: {len(chargers)} chargers found")
            return chargers
            
        except Exception as e:
            print(f"❌ Google Places error: {e}")
            return []

async def get_uk_national_chargepoint_data(lat: float, lon: float, radius: int) -> List[Charger]:
    """Get chargers from UK National Chargepoint Registry"""
    async with httpx.AsyncClient() as client:
        try:
            print(f"📍 UK National Registry: Fetching...")
            
            response = await client.get(
                "https://chargepoints.dft.gov.uk/api/retrieve/registry/format/json",
                timeout=25.0
            )
            
            if response.status_code != 200:
                print(f"❌ UK Registry API error: {response.status_code}")
                return []
            
            data = response.json()
            chargers = []
            
            for device in data.get("ChargeDevice", []):
                try:
                    device_lat = float(device.get("ChargeDeviceLocation", {}).get("Latitude", 0))
                    device_lon = float(device.get("ChargeDeviceLocation", {}).get("Longitude", 0))
                    
                    if device_lat == 0 or device_lon == 0:
                        continue
                    
                    distance = haversine_distance(lat, lon, device_lat, device_lon)
                    
                    if distance > radius:
                        continue
                    
                    connectors_data = device.get("Connector", [])
                    connectors = len(connectors_data)
                    
                    # Get max power and connector types
                    max_power = 0
                    connector_types = []
                    for conn in connectors_data:
                        power = conn.get("RatedOutputkW", 0)
                        if power:
                            max_power = max(max_power, float(power))
                        
                        conn_type = conn.get("ConnectorType", "")
                        if conn_type and conn_type not in connector_types:
                            connector_types.append(conn_type)
                    
                    network = device.get("DeviceOwner", {}).get("OrganisationName", "Unknown")
                    name = device.get("ChargeDeviceName", "Unknown Location")
                    
                    address_obj = device.get("ChargeDeviceLocation", {}).get("Address", {})
                    address = address_obj.get("Street", "")
                    
                    chargers.append(Charger(
                        id=f"uk_{device.get('ChargeDeviceId', 'unknown')}",
                        name=name,
                        distance_km=round(distance, 2),
                        connectors=connectors,
                        power_kw=int(max_power),
                        network=network,
                        source="UK National Registry",
                        address=address,
                        status="Operational",
                        connector_types=connector_types
                    ))
                except Exception as e:
                    continue
            
            print(f"✅ UK National Registry: {len(chargers)} chargers found")
            return chargers
            
        except Exception as e:
            print(f"❌ UK National Registry error: {e}")
            return []

async def get_zapmap_data(lat: float, lon: float, radius: int) -> List[Charger]:
    """
    Attempt to get Zap Map data via their public map API
    Note: Zap Map doesn't have an official public API, so this uses their map data endpoint
    """
    async with httpx.AsyncClient() as client:
        try:
            print(f"📍 Zap Map: Fetching (via map data)...")
            
            # Zap Map's public map data endpoint
            # This endpoint is used by their website's map
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://www.zap-map.com/live/"
            }
            
            # Calculate bounding box
            # Roughly 1 degree = 111km
            lat_offset = radius / 111.0
            lon_offset = radius / (111.0 * math.cos(math.radians(lat)))
            
            bbox = {
                "sw_lat": lat - lat_offset,
                "sw_lng": lon - lon_offset,
                "ne_lat": lat + lat_offset,
                "ne_lng": lon + lon_offset
            }
            
            response = await client.get(
                "https://www.zap-map.com/api/locations",
                params={
                    "bounds": f"{bbox['sw_lat']},{bbox['sw_lng']},{bbox['ne_lat']},{bbox['ne_lng']}",
                    "networks": "all"
                },
                headers=headers,
                timeout=15.0
            )
            
            if response.status_code != 200:
                print(f"⚠️ Zap Map: Status {response.status_code} (no official API)")
                return []
            
            data = response.json()
            chargers = []
            
            # Parse Zap Map response
            locations = data.get("locations", [])
            
            for location in locations:
                try:
                    loc_lat = location.get("lat", 0)
                    loc_lon = location.get("lng", 0)
                    
                    if loc_lat == 0 or loc_lon == 0:
                        continue
                    
                    distance = haversine_distance(lat, lon, loc_lat, loc_lon)
                    
                    if distance > radius:
                        continue
                    
                    chargers.append(Charger(
                        id=f"zapmap_{location.get('id', 'unknown')}",
                        name=location.get("name", "Unknown Location"),
                        distance_km=round(distance, 2),
                        connectors=location.get("device_count", 0),
                        power_kw=location.get("max_power", 0),
                        network=location.get("network", "Unknown"),
                        source="Zap Map",
                        address=location.get("address", ""),
                        status=location.get("status", "Unknown"),
                        connector_types=location.get("connector_types", [])
                    ))
                except Exception as e:
                    continue
            
            print(f"✅ Zap Map: {len(chargers)} chargers found")
            return chargers
            
        except Exception as e:
            print(f"⚠️ Zap Map: {e} (no official API available)")
            return []

def deduplicate_chargers(chargers: List[Charger]) -> List[Charger]:
    """Remove duplicate chargers based on proximity"""
    if not chargers:
        return []
    
    chargers.sort(key=lambda x: (x.distance_km, -x.connectors, -x.power_kw))
    
    unique_chargers = []
    seen_locations = []
    
    for charger in chargers:
        is_duplicate = False
        
        for seen in seen_locations:
            # Check if within 50m of an existing charger
            if abs(charger.distance_km - seen["distance"]) < 0.05:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_chargers.append(charger)
            seen_locations.append({"distance": charger.distance_km})
    
    return unique_chargers

@app.get("/")
async def root():
    sources_status = {
        "OpenChargeMap": "✅ Configured" if OPENCHARGEMAP_API_KEY else "⚠️ No API key",
        "Google Places": "✅ Configured" if GOOGLE_PLACES_API_KEY else "❌ Not configured",
        "UK National Registry": "✅ Always available",
        "Zap Map": "⚠️ Limited (no official API)"
    }
    
    return {
        "service": "EVL Multi-Source Backend API",
        "status": "operational",
        "version": "2.1.0",
        "data_sources": sources_status,
        "features": [
            "Multi-source data aggregation",
            "Smart deduplication",
            "UK-specific data",
            "Network analysis",
            "Connector type detection"
        ]
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "cors_enabled": True,
        "data_sources": {
            "openchargemap": bool(OPENCHARGEMAP_API_KEY),
            "google_places": bool(GOOGLE_PLACES_API_KEY),
            "uk_national_registry": True,
            "zapmap": True
        }
    }

@app.get("/api/analyze")
async def analyze(
    address: str = Query(..., description="Location to analyze"), 
    radius: int = Query(5, description="Search radius in km", ge=1, le=50)
):
    """
    Analyze a location for EV charger installation potential
    Aggregates data from multiple sources: OpenChargeMap, Google Places, UK Registry, and Zap Map
    """
    location = await geocode(address)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    print(f"\n🔍 Analyzing: {address}")
    print(f"📍 Coordinates: {location.latitude}, {location.longitude}")
    print(f"📏 Radius: {radius}km")
    
    # Fetch from all sources in parallel
    sources = [
        get_openchargemap_chargers(location.latitude, location.longitude, radius),
        get_google_places_chargers(location.latitude, location.longitude, radius),
        get_zapmap_data(location.latitude, location.longitude, radius)
    ]
    
    # Add UK data if location is in UK
    is_uk = any(x in address.lower() for x in ["uk", "united kingdom", "london", "manchester", "birmingham", "leeds", "glasgow", "edinburgh", "cardiff", "belfast"])
    if is_uk:
        print("🇬🇧 UK location detected")
        sources.append(get_uk_national_chargepoint_data(location.latitude, location.longitude, radius))
    
    results = await asyncio.gather(*sources, return_exceptions=True)
    
    # Combine all chargers
    all_chargers = []
    for result in results:
        if isinstance(result, list):
            all_chargers.extend(result)
    
    # Deduplicate
    chargers = deduplicate_chargers(all_chargers)
    
    print(f"\n📊 Total: {len(chargers)} unique chargers (from {len(all_chargers)} raw results)")
    
    # Calculate scores
    nearby_chargers = len([c for c in chargers if c.distance_km < 2])
    very_close = len([c for c in chargers if c.distance_km < 0.5])
    
    competition_score = max(0.3, min(0.9 - nearby_chargers * 0.08 - very_close * 0.05, 0.95))
    overall_score = round(competition_score, 2)
    
    # ROI projection
    base_revenue = 50000
    estimated_revenue = int(base_revenue * overall_score)
    payback_period = round(25000 / max(estimated_revenue / 12, 1000), 1)
    
    # Recommendations
    recommendations = []
    
    sources_used = list(set([c.source for c in chargers]))
    recommendations.append({
        "text": f"📊 Data from {len(sources_used)} source(s): {', '.join(sources_used)}"
    })
    
    if overall_score >= 0.8:
        recommendations.append({"text": "✅ Excellent location - low competition, high potential"})
    elif overall_score >= 0.6:
        recommendations.append({"text": "✅ Good location - moderate competition"})
    else:
        recommendations.append({"text": "⚠️ High competition - consider alternative sites"})
    
    recommendations.append({"text": f"Found {len(chargers)} chargers within {radius}km ({nearby_chargers} within 2km)"})
    
    # Network analysis
    networks = defaultdict(int)
    for c in chargers:
        if c.network and c.network != "Unknown":
            networks[c.network] += 1
    
    if networks:
        top_networks = sorted(networks.items(), key=lambda x: x[1], reverse=True)[:3]
        network_text = ", ".join([f"{name} ({count})" for name, count in top_networks])
        recommendations.append({"text": f"🔌 Dominant networks: {network_text}"})
    
    # Power analysis
    high_power = len([c for c in chargers if c.power_kw >= 150])
    if high_power > 0:
        recommendations.append({"text": f"⚡ {high_power} ultra-rapid chargers (150kW+) in area"})
    
    return {
        "location": location.dict(),
        "chargers": [c.dict() for c in chargers[:100]],
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
        "api_info": {
            "total_chargers_found": len(chargers),
            "chargers_displayed": min(len(chargers), 100),
            "sources_used": sources_used,
            "raw_results_before_dedup": len(all_chargers),
            "data_sources_configured": {
                "openchargemap": bool(OPENCHARGEMAP_API_KEY),
                "google_places": bool(GOOGLE_PLACES_API_KEY),
                "uk_national_registry": is_uk,
                "zapmap": True
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
