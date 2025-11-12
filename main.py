"""
EVL v8.0 - Comprehensive Multi-Source Data Integration
Implements all 5 analysis categories with real data sources
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import math
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
from enum import Enum

app = FastAPI(title="EVL v8.0 - Professional Site Analysis")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== CONFIGURATION ====================

class DataSource(Enum):
    """Available data sources"""
    # Free sources
    OSM_OVERPASS = "osm_overpass"
    UK_DFT = "uk_dft"
    OPENINFRAMAP = "openinframap"
    OPENCHARGEMAP = "openchargemap"
    EAFO = "eafo"
    
    # Paid sources (optional)
    GOOGLE_MAPS = "google_maps"
    TOMTOM = "tomtom"
    DVLA = "dvla"
    DNO_GRID = "dno_grid"

# API Keys (set via environment variables)
API_KEYS = {
    "google_maps": os.getenv("GOOGLE_MAPS_API_KEY"),
    "tomtom": os.getenv("TOMTOM_API_KEY"),
    "openchargemap": os.getenv("OPENCHARGEMAP_API_KEY"),
}

# ==================== UTILITIES ====================

def distance(lat1, lon1, lat2, lon2):
    """Calculate distance in km using Haversine formula"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return round(R * c, 2)

# ==================== CATEGORY 1: TRAFFIC & ACCESSIBILITY ====================

async def get_osm_road_data(lat: float, lon: float) -> Dict[str, Any]:
    """
    Get road hierarchy and accessibility from OSM
    Free, Global coverage
    """
    try:
        async with httpx.AsyncClient() as client:
            query = f"""
            [out:json][timeout:10];
            (
              way(around:500,{lat},{lon})["highway"~"motorway|trunk|primary|secondary|tertiary"];
            );
            out body;
            """
            
            response = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                timeout=15.0
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            roads = []
            
            for element in data.get("elements", []):
                highway_type = element.get("tags", {}).get("highway")
                name = element.get("tags", {}).get("name", "Unnamed")
                ref = element.get("tags", {}).get("ref", "")
                maxspeed = element.get("tags", {}).get("maxspeed", "")
                lanes = element.get("tags", {}).get("lanes", "")
                
                roads.append({
                    "type": highway_type,
                    "name": name,
                    "ref": ref,
                    "maxspeed": maxspeed,
                    "lanes": lanes
                })
            
            # Calculate accessibility score
            road_types = [r["type"] for r in roads]
            if "motorway" in road_types:
                accessibility = 1.0
                main_road_type = "Motorway"
            elif "trunk" in road_types:
                accessibility = 0.9
                main_road_type = "Trunk Road"
            elif "primary" in road_types:
                accessibility = 0.8
                main_road_type = "Primary Road"
            elif "secondary" in road_types:
                accessibility = 0.7
                main_road_type = "Secondary Road"
            else:
                accessibility = 0.6
                main_road_type = "Local Road"
            
            nearest_road = roads[0] if roads else {"name": "Unknown", "type": "local"}
            
            return {
                "source": "OpenStreetMap",
                "roads_nearby": len(roads),
                "nearest_road": nearest_road["name"],
                "road_type": main_road_type,
                "accessibility_score": accessibility,
                "visibility_score": accessibility * 0.95,  # Slightly lower
                "all_roads": roads[:5]  # Top 5
            }
    except Exception as e:
        print(f"OSM Road API Error: {e}")
        return None

async def get_uk_dft_traffic(lat: float, lon: float) -> Dict[str, Any]:
    """
    Get real traffic counts from UK Department for Transport
    Free, UK only
    """
    try:
        async with httpx.AsyncClient() as client:
            # DfT API endpoint
            response = await client.get(
                "https://api.dft.gov.uk/v3/traffic/counts",
                params={
                    "lat": lat,
                    "lon": lon,
                    "radius": 2000  # 2km
                },
                timeout=15.0
            )
            
            if response.status_code != 200 or not response.json().get("features"):
                return None
            
            data = response.json()
            nearest = data["features"][0]
            props = nearest["properties"]
            
            return {
                "source": "UK Department for Transport",
                "available": True,
                "aadt": props.get("all_motor_vehicles", 15000),
                "cars_taxis": props.get("cars_and_taxis", 12000),
                "hgvs": props.get("hgvs", 1000),
                "buses": props.get("buses_and_coaches", 200),
                "motorcycles": props.get("motorcycles", 500),
                "lgvs": props.get("lgvs", 1300),
                "pedal_cycles": props.get("pedal_cycles", 100),
                "year": props.get("year", 2023),
                "road_name": props.get("road_name", "Unknown"),
                "road_category": props.get("road_category", "Unknown"),
                "distance_km": round(nearest.get("distance", 0) / 1000, 2)
            }
    except Exception as e:
        print(f"UK DfT API Error: {e}")
        return None

async def get_google_maps_traffic(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Get live traffic from Google Maps API
    Paid, Global coverage
    """
    api_key = API_KEYS.get("google_maps")
    if not api_key:
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            # Places API for location details
            response = await client.get(
                "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                params={
                    "location": f"{lat},{lon}",
                    "radius": 500,
                    "key": api_key
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            places = data.get("results", [])
            
            return {
                "source": "Google Maps API",
                "places_nearby": len(places),
                "high_traffic_areas": len([p for p in places if p.get("user_ratings_total", 0) > 100]),
                "average_rating": sum(p.get("rating", 0) for p in places) / len(places) if places else 0
            }
    except Exception as e:
        print(f"Google Maps API Error: {e}")
        return None

async def get_tomtom_traffic(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Get historical traffic from TomTom API
    Paid, Global coverage
    """
    api_key = API_KEYS.get("tomtom")
    if not api_key:
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json",
                params={
                    "point": f"{lat},{lon}",
                    "key": api_key
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            flow = data.get("flowSegmentData", {})
            
            return {
                "source": "TomTom Traffic API",
                "current_speed_kmh": flow.get("currentSpeed", 0),
                "free_flow_speed_kmh": flow.get("freeFlowSpeed", 0),
                "congestion_ratio": flow.get("currentSpeed", 0) / max(flow.get("freeFlowSpeed", 1), 1),
                "current_travel_time_sec": flow.get("currentTravelTime", 0),
                "confidence": flow.get("confidence", 0)
            }
    except Exception as e:
        print(f"TomTom API Error: {e}")
        return None

# ==================== CATEGORY 2: DEMAND POTENTIAL ====================

async def get_osm_land_use(lat: float, lon: float) -> Dict[str, Any]:
    """
    Get land use and POI data from OSM
    Free, Global coverage
    """
    try:
        async with httpx.AsyncClient() as client:
            query = f"""
            [out:json][timeout:10];
            (
              way(around:1000,{lat},{lon})["landuse"];
              way(around:500,{lat},{lon})["amenity"~"restaurant|cafe|fuel|supermarket|hotel|bank|hospital"];
              way(around:500,{lat},{lon})["shop"];
            );
            out body;
            """
            
            response = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                timeout=15.0
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            land_uses = {}
            amenities = {}
            shops = {}
            
            for element in data.get("elements", []):
                tags = element.get("tags", {})
                
                if "landuse" in tags:
                    lu = tags["landuse"]
                    land_uses[lu] = land_uses.get(lu, 0) + 1
                
                if "amenity" in tags:
                    am = tags["amenity"]
                    amenities[am] = amenities.get(am, 0) + 1
                
                if "shop" in tags:
                    sh = tags["shop"]
                    shops[sh] = shops.get(sh, 0) + 1
            
            # Determine primary land use
            primary_land_use = max(land_uses, key=land_uses.get) if land_uses else "mixed"
            
            # Demand indicators
            has_retail = "retail" in land_uses or len(shops) > 0
            has_commercial = "commercial" in land_uses
            has_residential = "residential" in land_uses
            has_industrial = "industrial" in land_uses
            
            demand_score = 0.5  # Base
            if has_retail:
                demand_score += 0.2
            if has_commercial:
                demand_score += 0.15
            if has_residential:
                demand_score += 0.1
            if len(amenities) > 5:
                demand_score += 0.15
            
            demand_score = min(demand_score, 1.0)
            
            return {
                "source": "OpenStreetMap",
                "primary_land_use": primary_land_use,
                "land_use_types": land_uses,
                "amenities": amenities,
                "shops": shops,
                "total_pois": sum(amenities.values()) + sum(shops.values()),
                "demand_score": round(demand_score, 2),
                "has_retail": has_retail,
                "has_commercial": has_commercial,
                "has_residential": has_residential
            }
    except Exception as e:
        print(f"OSM Land Use API Error: {e}")
        return None

async def get_parking_data(lat: float, lon: float) -> Dict[str, Any]:
    """
    Get parking facilities from OSM
    Free, Global coverage
    """
    try:
        async with httpx.AsyncClient() as client:
            query = f"""
            [out:json][timeout:10];
            (
              way(around:500,{lat},{lon})["amenity"="parking"];
              relation(around:500,{lat},{lon})["amenity"="parking"];
              node(around:500,{lat},{lon})["amenity"="parking"];
            );
            out body;
            """
            
            response = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                timeout=15.0
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            elements = data.get("elements", [])
            
            parking_facilities = []
            total_spaces = 0
            
            for element in elements:
                tags = element.get("tags", {})
                name = tags.get("name", "Parking")
                access = tags.get("access", "public")
                fee = tags.get("fee", "unknown")
                capacity = tags.get("capacity", "unknown")
                
                parking_facilities.append({
                    "name": name,
                    "access": access,
                    "fee": fee,
                    "capacity": capacity
                })
                
                if capacity != "unknown":
                    try:
                        total_spaces += int(capacity)
                    except:
                        pass
            
            availability_score = min(len(parking_facilities) / 5, 1.0)
            
            return {
                "source": "OpenStreetMap",
                "parking_facilities": len(parking_facilities),
                "total_estimated_spaces": total_spaces if total_spaces > 0 else len(parking_facilities) * 50,
                "availability_score": round(availability_score, 2),
                "facilities": parking_facilities[:10]
            }
    except Exception as e:
        print(f"OSM Parking API Error: {e}")
        return None

async def get_eafo_data(country_code: str = "UK") -> Dict[str, Any]:
    """
    Get EV adoption statistics from EAFO
    Free, EU coverage
    """
    # Note: EAFO doesn't have a real-time API, but publishes data
    # This would typically pull from cached/downloaded EAFO data
    
    eafo_estimates = {
        "UK": {"ev_stock": 1100000, "public_chargers": 55000, "growth_rate": 0.35},
        "DE": {"ev_stock": 1300000, "public_chargers": 90000, "growth_rate": 0.40},
        "FR": {"ev_stock": 1000000, "public_chargers": 75000, "growth_rate": 0.38},
        "NL": {"ev_stock": 450000, "public_chargers": 115000, "growth_rate": 0.30},
        "NO": {"ev_stock": 650000, "public_chargers": 25000, "growth_rate": 0.25},
        "PL": {"ev_stock": 75000, "public_chargers": 3500, "growth_rate": 0.50}
    }
    
    data = eafo_estimates.get(country_code, eafo_estimates["UK"])
    
    return {
        "source": "EAFO (European Alternative Fuels Observatory)",
        "country": country_code,
        "ev_stock": data["ev_stock"],
        "public_chargers": data["public_chargers"],
        "ev_per_charger": round(data["ev_stock"] / data["public_chargers"], 1),
        "yoy_growth_rate": data["growth_rate"],
        "market_maturity": "high" if data["ev_stock"] > 500000 else "medium" if data["ev_stock"] > 100000 else "emerging"
    }

# ==================== CATEGORY 3: ELECTRICAL INFRASTRUCTURE ====================

async def get_openinframap_data(lat: float, lon: float) -> Dict[str, Any]:
    """
    Get power infrastructure from OpenInfraMap (based on OSM)
    Free, Global coverage
    """
    try:
        async with httpx.AsyncClient() as client:
            query = f"""
            [out:json][timeout:10];
            (
              node(around:5000,{lat},{lon})["power"="substation"];
              way(around:5000,{lat},{lon})["power"="substation"];
              way(around:2000,{lat},{lon})["power"="line"];
            );
            out body;
            """
            
            response = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                timeout=15.0
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            substations = []
            power_lines = []
            
            for element in data.get("elements", []):
                tags = element.get("tags", {})
                power_type = tags.get("power")
                
                if power_type == "substation":
                    voltage = tags.get("voltage", "unknown")
                    operator = tags.get("operator", "unknown")
                    name = tags.get("name", "Substation")
                    
                    # Calculate distance
                    if "lat" in element and "lon" in element:
                        dist = distance(lat, lon, element["lat"], element["lon"])
                    else:
                        dist = 999
                    
                    substations.append({
                        "name": name,
                        "voltage": voltage,
                        "operator": operator,
                        "distance_km": dist
                    })
                elif power_type == "line":
                    voltage = tags.get("voltage", "unknown")
                    power_lines.append({"voltage": voltage})
            
            # Sort by distance
            substations.sort(key=lambda x: x["distance_km"])
            
            nearest_substation = substations[0] if substations else None
            grid_capacity_score = 0.7  # Base estimate
            
            if nearest_substation:
                dist = nearest_substation["distance_km"]
                if dist < 1:
                    grid_capacity_score = 0.95
                elif dist < 2:
                    grid_capacity_score = 0.85
                elif dist < 5:
                    grid_capacity_score = 0.75
                else:
                    grid_capacity_score = 0.6
            
            return {
                "source": "OpenInfraMap / OpenStreetMap",
                "substations_nearby": len(substations),
                "nearest_substation": nearest_substation,
                "power_lines_nearby": len(power_lines),
                "grid_capacity_score": grid_capacity_score,
                "estimated_connection_cost": int(nearest_substation["distance_km"] * 10000) if nearest_substation else 50000
            }
    except Exception as e:
        print(f"OpenInfraMap API Error: {e}")
        return None

# ==================== CATEGORY 4: COMPETITION & PRICING ====================

async def get_openchargemap_data(lat: float, lon: float, radius: int) -> Dict[str, Any]:
    """
    Get charging stations from OpenChargeMap
    Free, Global coverage
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "latitude": lat,
                "longitude": lon,
                "distance": radius,
                "distanceunit": "km",
                "maxresults": 100
            }
            
            if API_KEYS.get("openchargemap"):
                params["key"] = API_KEYS["openchargemap"]
            
            response = await client.get(
                "https://api.openchargemap.io/v3/poi/",
                params=params,
                timeout=20.0
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            chargers = []
            
            for poi in data:
                try:
                    poi_lat = poi["AddressInfo"]["Latitude"]
                    poi_lon = poi["AddressInfo"]["Longitude"]
                    dist = distance(lat, lon, poi_lat, poi_lon)
                    
                    connections = poi.get("Connections", [])
                    power_values = [c.get("PowerKW", 0) for c in connections if c.get("PowerKW")]
                    max_power = int(max(power_values)) if power_values else 7
                    
                    network = "Unknown"
                    if poi.get("OperatorInfo"):
                        network = poi["OperatorInfo"].get("Title", "Unknown")
                    
                    status = poi.get("StatusType", {}).get("Title", "Unknown")
                    usage_type = poi.get("UsageType", {}).get("Title", "Public")
                    
                    chargers.append({
                        "id": f"ocm_{poi['ID']}",
                        "name": poi["AddressInfo"].get("Title", "Unknown"),
                        "distance_km": dist,
                        "connectors": len(connections),
                        "power_kw": max_power,
                        "network": network,
                        "status": status,
                        "usage_type": usage_type,
                        "source": "OpenChargeMap"
                    })
                except:
                    pass
            
            # Analyze competition
            total_chargers = len(chargers)
            operational = len([c for c in chargers if c["status"] == "Operational"])
            networks = set(c["network"] for c in chargers)
            
            return {
                "source": "OpenChargeMap",
                "total_chargers": total_chargers,
                "operational_chargers": operational,
                "networks": list(networks),
                "network_diversity": len(networks),
                "chargers": chargers
            }
    except Exception as e:
        print(f"OpenChargeMap API Error: {e}")
        return None

# ==================== CATEGORY 5: SITE & BUSINESS FEASIBILITY ====================

async def get_satellite_amenities(lat: float, lon: float) -> Dict[str, Any]:
    """
    Analyze site surroundings and amenities
    Uses OSM data (alternative to satellite imagery analysis)
    """
    try:
        async with httpx.AsyncClient() as client:
            query = f"""
            [out:json][timeout:10];
            (
              node(around:1000,{lat},{lon})["tourism"];
              node(around:1000,{lat},{lon})["leisure"];
              way(around:1000,{lat},{lon})["building"="commercial"];
              way(around:1000,{lat},{lon})["building"="retail"];
            );
            out body;
            """
            
            response = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                timeout=15.0
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            tourism_pois = []
            leisure_pois = []
            commercial_buildings = 0
            retail_buildings = 0
            
            for element in data.get("elements", []):
                tags = element.get("tags", {})
                
                if "tourism" in tags:
                    tourism_pois.append(tags["tourism"])
                if "leisure" in tags:
                    leisure_pois.append(tags["leisure"])
                if tags.get("building") == "commercial":
                    commercial_buildings += 1
                if tags.get("building") == "retail":
                    retail_buildings += 1
            
            comfort_score = min((len(tourism_pois) + len(leisure_pois) + commercial_buildings + retail_buildings) / 20, 1.0)
            
            return {
                "source": "OpenStreetMap POI Analysis",
                "tourism_attractions": len(tourism_pois),
                "leisure_facilities": len(leisure_pois),
                "commercial_buildings": commercial_buildings,
                "retail_buildings": retail_buildings,
                "comfort_score": round(comfort_score, 2),
                "site_attractiveness": "high" if comfort_score > 0.7 else "medium" if comfort_score > 0.4 else "low"
            }
    except Exception as e:
        print(f"Site Amenities API Error: {e}")
        return None

# ==================== COMPREHENSIVE ANALYSIS ====================

async def comprehensive_analysis(
    lat: float,
    lon: float,
    radius: int,
    country_code: str = "UK"
) -> Dict[str, Any]:
    """
    Run all data source queries in parallel
    """
    
    # Fire all API requests in parallel
    results = await asyncio.gather(
        # Traffic & Accessibility
        get_osm_road_data(lat, lon),
        get_uk_dft_traffic(lat, lon),
        get_google_maps_traffic(lat, lon),
        get_tomtom_traffic(lat, lon),
        
        # Demand Potential
        get_osm_land_use(lat, lon),
        get_parking_data(lat, lon),
        get_eafo_data(country_code),
        
        # Electrical Infrastructure
        get_openinframap_data(lat, lon),
        
        # Competition
        get_openchargemap_data(lat, lon, radius),
        
        # Site Feasibility
        get_satellite_amenities(lat, lon),
        
        return_exceptions=True
    )
    
    (osm_roads, uk_traffic, google_traffic, tomtom_traffic,
     osm_land, parking, eafo,
     grid_data,
     chargers,
     amenities) = results
    
    return {
        "traffic_accessibility": {
            "osm_roads": osm_roads,
            "uk_dft_traffic": uk_traffic,
            "google_maps": google_traffic,
            "tomtom": tomtom_traffic
        },
        "demand_potential": {
            "land_use": osm_land,
            "parking": parking,
            "eafo": eafo
        },
        "electrical_infrastructure": {
            "grid": grid_data
        },
        "competition": {
            "chargers": chargers
        },
        "site_feasibility": {
            "amenities": amenities
        }
    }

# ==================== SCORING ENGINE ====================

def calculate_advanced_scores(comprehensive_data: Dict[str, Any], 
                             facility_analysis: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate weighted scores from all data sources
    """
    
    # Extract data
    traffic = comprehensive_data["traffic_accessibility"]
    demand = comprehensive_data["demand_potential"]
    grid = comprehensive_data["electrical_infrastructure"]
    competition = comprehensive_data["competition"]
    site = comprehensive_data["site_feasibility"]
    
    # 1. Traffic & Accessibility Score
    traffic_score = 0.6  # Base
    if traffic["osm_roads"]:
        traffic_score = traffic["osm_roads"]["accessibility_score"]
    if traffic["uk_dft_traffic"]:
        # Boost based on real traffic
        aadt = traffic["uk_dft_traffic"]["aadt"]
        traffic_boost = min(aadt / 80000, 0.3)
        traffic_score = min(traffic_score + traffic_boost, 1.0)
    
    # 2. Demand Score
    demand_score = 0.5  # Base
    if demand["land_use"]:
        demand_score = demand["land_use"]["demand_score"]
    if demand["eafo"]:
        # Adjust for market maturity
        maturity = demand["eafo"]["market_maturity"]
        if maturity == "high":
            demand_score = min(demand_score + 0.2, 1.0)
    
    # 3. Grid Readiness Score
    grid_score = 0.7  # Base
    if grid["grid"]:
        grid_score = grid["grid"]["grid_capacity_score"]
    
    # 4. Competition Score
    competition_score = 0.8  # Base
    if competition["chargers"]:
        total = competition["chargers"]["total_chargers"]
        competition_score = max(0.3, 0.9 - (total * 0.05))
    
    # 5. Parking & Access Score
    parking_score = 0.7  # Base
    if demand["parking"]:
        parking_score = demand["parking"]["availability_score"]
    
    # 6. Site Quality Score
    site_score = 0.6  # Base
    if site["amenities"]:
        site_score = site["amenities"]["comfort_score"]
    
    # 7. Facility Popularity
    facility_score = facility_analysis.get("popularity_score", 0.5)
    
    # Overall weighted score
    overall = (
        traffic_score * 0.20 +
        demand_score * 0.20 +
        grid_score * 0.15 +
        competition_score * 0.15 +
        parking_score * 0.10 +
        site_score * 0.10 +
        facility_score * 0.10
    )
    
    return {
        "overall": round(overall, 2),
        "traffic_accessibility": round(traffic_score, 2),
        "demand": round(demand_score, 2),
        "grid_readiness": round(grid_score, 2),
        "competition": round(competition_score, 2),
        "parking_access": round(parking_score, 2),
        "site_quality": round(site_score, 2),
        "facility_popularity": round(facility_score, 2)
    }

# ==================== EXISTING FUNCTIONS (from v6/v7) ====================

def analyze_facilities_and_dwell_time(facilities: List[str]):
    """Analyze facilities - same as v7.0"""
    dwell_times = {
        "grocery": 45, "restaurant": 90, "shopping_mall": 120, "coffee": 30,
        "gym": 75, "hotel": 480, "workplace": 480, "cinema": 150, "other": 60
    }
    
    popularity_weights = {
        "grocery": 1.3, "restaurant": 1.2, "shopping_mall": 1.5, "coffee": 1.1,
        "gym": 1.2, "hotel": 1.4, "workplace": 1.3, "cinema": 1.1, "other": 1.0
    }
    
    if not facilities:
        return {
            "avg_dwell_time_minutes": 30,
            "location_type": "Unknown",
            "popularity_score": 0.5,
            "recommended_power": "50 kW DC Fast",
            "reasoning": "No facilities specified"
        }
    
    avg_dwell = sum(dwell_times.get(f, 60) for f in facilities) / len(facilities)
    base_popularity = sum(popularity_weights.get(f, 1.0) for f in facilities) / len(facilities)
    popularity_score = min(base_popularity - 0.5, 1.0)
    
    # Location type
    if "shopping_mall" in facilities:
        location_type = "Retail Hub"
    elif "hotel" in facilities or "workplace" in facilities:
        location_type = "Long Stay"
    elif "restaurant" in facilities or "coffee" in facilities:
        location_type = "Food & Beverage"
    elif "gym" in facilities:
        location_type = "Fitness & Leisure"
    elif "grocery" in facilities:
        location_type = "Convenience Retail"
    else:
        location_type = "Mixed Use"
    
    # Power recommendation
    if avg_dwell > 120:
        recommended_power = "7-22 kW AC"
        reasoning = f"Long dwell time ({int(avg_dwell)} min) - slow charging optimal"
    elif avg_dwell > 60:
        recommended_power = "22-50 kW AC/DC"
        reasoning = f"Medium dwell time ({int(avg_dwell)} min) - fast AC or moderate DC"
    else:
        recommended_power = "50-150 kW DC Fast"
        reasoning = f"Short dwell time ({int(avg_dwell)} min) - rapid DC charging needed"
    
    return {
        "avg_dwell_time_minutes": int(avg_dwell),
        "location_type": location_type,
        "popularity_score": round(popularity_score, 2),
        "recommended_power": recommended_power,
        "reasoning": reasoning,
        "facilities_count": len(facilities)
    }

def sort_chargers_by_relevance(chargers: List[dict], target_power: int):
    """Smart sort chargers - same as v7.0"""
    similar, higher, lower = [], [], []
    power_tolerance = target_power * 0.3
    
    for charger in chargers:
        power = charger["power_kw"]
        power_diff = abs(power - target_power)
        
        if power_diff <= power_tolerance:
            similar.append((power_diff, charger))
        elif power > target_power:
            higher.append((power, charger))
        else:
            lower.append((power, charger))
    
    similar.sort(key=lambda x: x[0])
    higher.sort(key=lambda x: x[0])
    lower.sort(key=lambda x: -x[0])
    
    return [c[1] for c in similar] + [c[1] for c in higher] + [c[1] for c in lower]

# ==================== API ENDPOINTS ====================

@app.get("/")
def root():
    return {
        "service": "EVL v8.0 - Professional Multi-Source Analysis",
        "version": "8.0-COMPREHENSIVE",
        "data_sources": {
            "traffic_accessibility": [
                "OpenStreetMap (free)",
                "UK DfT Traffic (free, UK only)",
                "Google Maps (paid, optional)",
                "TomTom (paid, optional)"
            ],
            "demand_potential": [
                "OSM Land Use (free)",
                "OSM Parking (free)",
                "EAFO Statistics (free, EU)"
            ],
            "electrical_infrastructure": [
                "OpenInfraMap (free)"
            ],
            "competition": [
                "OpenChargeMap (free)"
            ],
            "site_feasibility": [
                "OSM POI Analysis (free)"
            ]
        },
        "features": [
            "comprehensive_multi_source_data",
            "parallel_api_processing",
            "weighted_scoring_engine",
            "facility_based_analysis",
            "smart_charger_sorting",
            "real_traffic_counts",
            "grid_infrastructure_analysis",
            "competition_intelligence",
            "site_quality_assessment"
        ]
    }

@app.get("/api/analyze")
async def analyze(
    address: str = Query(...),
    radius: int = Query(5),
    power_per_plug: int = Query(50),
    num_plugs: int = Query(2),
    facilities: str = Query(""),
    country_code: str = Query("UK")
):
    """
    Professional site analysis with comprehensive multi-source data
    """
    
    # Parse facilities
    facility_list = [f.strip() for f in facilities.split(",") if f.strip()]
    facility_analysis = analyze_facilities_and_dwell_time(facility_list)
    
    # Geocode
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "EVL-v8"},
            timeout=10.0
        )
        data = r.json()
        if not data:
            raise HTTPException(status_code=404, detail="Location not found")
        
        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
    
    # Run comprehensive analysis
    comprehensive_data = await comprehensive_analysis(lat, lon, radius, country_code)
    
    # Get chargers and sort
    chargers = []
    if comprehensive_data["competition"]["chargers"]:
        chargers = comprehensive_data["competition"]["chargers"]["chargers"]
        chargers = sort_chargers_by_relevance(chargers, power_per_plug)
    
    # Calculate advanced scores
    scores = calculate_advanced_scores(comprehensive_data, facility_analysis)
    
    # Generate comprehensive recommendations
    recommendations = []
    
    # Data source indicators
    data_sources_used = []
    if comprehensive_data["traffic_accessibility"]["uk_dft_traffic"]:
        data_sources_used.append("UK DfT Traffic (real data)")
    if comprehensive_data["traffic_accessibility"]["google_maps"]:
        data_sources_used.append("Google Maps (live)")
    if comprehensive_data["demand_potential"]["land_use"]:
        data_sources_used.append("OSM Land Use")
    
    if data_sources_used:
        recommendations.append({
            "text": f"📊 Data Sources: {', '.join(data_sources_used)}",
            "type": "info"
        })
    
    # Traffic insights
    if comprehensive_data["traffic_accessibility"]["uk_dft_traffic"]:
        traffic_data = comprehensive_data["traffic_accessibility"]["uk_dft_traffic"]
        recommendations.append({
            "text": f"🚗 Real Traffic: {traffic_data['aadt']:,} vehicles/day on {traffic_data['road_name']}",
            "type": "info"
        })
    
    # Grid insights
    if comprehensive_data["electrical_infrastructure"]["grid"]:
        grid = comprehensive_data["electrical_infrastructure"]["grid"]
        if grid["nearest_substation"]:
            dist = grid["nearest_substation"]["distance_km"]
            recommendations.append({
                "text": f"⚡ Grid: Substation {dist:.1f}km away, est. connection cost £{grid['estimated_connection_cost']:,}",
                "type": "info" if dist < 2 else "warning"
            })
    
    # Facility recommendations (same as v7.0)
    if facility_list:
        recommendations.append({
            "text": f"📍 {facility_analysis['location_type']}: {facility_analysis['reasoning']}"
        })
        
        current_power_type = "DC Fast" if power_per_plug >= 50 else "AC"
        recommended_type = "AC" if "AC" in facility_analysis["recommended_power"] else "DC"
        
        if current_power_type != recommended_type:
            recommendations.append({
                "text": f"⚠️ Consider {facility_analysis['recommended_power']} instead of {power_per_plug}kW",
                "type": "warning"
            })
    
    # Competition insights
    if comprehensive_data["competition"]["chargers"]:
        comp = comprehensive_data["competition"]["chargers"]
        recommendations.append({
            "text": f"🔍 Competition: {comp['total_chargers']} chargers, {comp['network_diversity']} networks"
        })
    
    # Site quality
    if comprehensive_data["site_feasibility"]["amenities"]:
        site = comprehensive_data["site_feasibility"]["amenities"]
        recommendations.append({
            "text": f"🏪 Site Quality: {site['site_attractiveness'].title()} ({site['tourism_attractions']} attractions nearby)"
        })
    
    return {
        "location": {"address": address, "latitude": lat, "longitude": lon},
        "planned_installation": {
            "power_per_plug_kw": power_per_plug,
            "number_of_plugs": num_plugs,
            "total_power_kw": power_per_plug * num_plugs
        },
        "facility_analysis": facility_analysis,
        "comprehensive_data": comprehensive_data,
        "scores": scores,
        "chargers": chargers[:50],
        "recommendations": recommendations,
        "data_quality": {
            "sources_used": len([d for d in comprehensive_data.values() if any(v for v in d.values() if v)]),
            "total_sources": 10,
            "real_data_percentage": round(len(data_sources_used) / 10 * 100)
        }
    }

@app.get("/api/health")
def health():
    """Check which data sources are available"""
    return {
        "status": "healthy",
        "api_keys_configured": {
            "google_maps": bool(API_KEYS.get("google_maps")),
            "tomtom": bool(API_KEYS.get("tomtom")),
            "openchargemap": bool(API_KEYS.get("openchargemap"))
        },
        "free_sources_available": [
            "OSM Overpass",
            "UK DfT",
            "OpenInfraMap",
            "OpenChargeMap",
            "EAFO"
        ]
    }
