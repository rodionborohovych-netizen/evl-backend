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

def calculate_installation_cost(power_per_plug, num_plugs):
    """Calculate installation cost based on charger specs"""
    # Base costs per plug by power level
    cost_per_plug = {
        7: 1500,    # Level 2 home charger
        11: 2000,   # Level 2 commercial
        22: 3000,   # Level 2 fast
        50: 25000,  # DC fast charger
        150: 50000, # DC ultra-rapid
        350: 80000  # DC ultra-fast (Tesla Supercharger level)
    }
    
    # Find closest power level
    closest_power = min(cost_per_plug.keys(), key=lambda x: abs(x - power_per_plug))
    base_cost = cost_per_plug[closest_power]
    
    # Installation cost = (base cost per plug * number of plugs) + infrastructure
    infrastructure_cost = 5000  # Grid connection, electrical work, etc.
    total_cost = (base_cost * num_plugs) + infrastructure_cost
    
    return total_cost

def calculate_revenue(power_per_plug, num_plugs, competition_score):
    """Calculate projected annual revenue"""
    # Revenue factors by power level (annual per plug)
    revenue_per_plug = {
        7: 2000,    # Home/workplace charging
        11: 3000,   # Destination charging
        22: 5000,   # Fast charging
        50: 15000,  # DC fast
        150: 30000, # Ultra-rapid
        350: 50000  # Ultra-fast
    }
    
    # Find closest power level
    closest_power = min(revenue_per_plug.keys(), key=lambda x: abs(x - power_per_plug))
    base_revenue = revenue_per_plug[closest_power]
    
    # Total revenue = base per plug * number of plugs * competition factor
    total_revenue = base_revenue * num_plugs * competition_score
    
    return int(total_revenue)

@app.get("/")
def root():
    return {
        "status": "ok",
        "version": "4.0-CUSTOM-INSTALLATION",
        "features": ["custom_power", "custom_plugs", "roi_calculator"]
    }

@app.get("/api/analyze")
async def analyze(
    address: str = Query(..., description="Location to analyze"),
    radius: int = Query(5, description="Search radius in km"),
    power_per_plug: int = Query(50, description="Power per plug in kW (e.g., 7, 22, 50, 150)"),
    num_plugs: int = Query(2, description="Number of charging plugs to install")
):
    """
    Analyze location for EV charger installation with custom specifications
    
    Parameters:
    - address: Location to analyze
    - radius: Search radius for existing chargers (km)
    - power_per_plug: Power per charging plug in kW (7, 11, 22, 50, 150, 350)
    - num_plugs: Number of charging plugs you plan to install
    """
    
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
                    
                    connections = poi.get("Connections", [])
                    power_values = [c.get("PowerKW", 0) for c in connections if c.get("PowerKW")]
                    max_power = int(max(power_values)) if power_values else 7
                    
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
    
    # Google Places
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
    
    # Analyze competition based on planned installation
    nearby_chargers = len([c for c in chargers if c["distance_km"] < 2])
    
    # Count similar power level chargers (within 50% of planned power)
    similar_power_nearby = len([
        c for c in chargers 
        if c["distance_km"] < 2 and 
        abs(c["power_kw"] - power_per_plug) < power_per_plug * 0.5
    ])
    
    # Calculate competition score (0.3 = high competition, 0.95 = low competition)
    competition_score = max(0.3, min(0.9 - nearby_chargers * 0.08 - similar_power_nearby * 0.05, 0.95))
    
    # Calculate custom installation costs and revenue
    installation_cost = calculate_installation_cost(power_per_plug, num_plugs)
    annual_revenue = calculate_revenue(power_per_plug, num_plugs, competition_score)
    monthly_revenue = int(annual_revenue / 12)
    
    # Calculate payback period
    if monthly_revenue > 0:
        payback_years = round(installation_cost / monthly_revenue / 12, 1)
    else:
        payback_years = 999
    
    # Generate recommendations
    recommendations = []
    
    # Installation summary
    recommendations.append({
        "text": f"📊 Your planned installation: {num_plugs} plug(s) at {power_per_plug}kW each"
    })
    
    # Competition analysis
    recommendations.append({
        "text": f"🔍 Found {len(chargers)} chargers within {radius}km ({nearby_chargers} within 2km)"
    })
    
    if similar_power_nearby > 0:
        recommendations.append({
            "text": f"⚠️ {similar_power_nearby} similar chargers ({power_per_plug}kW) within 2km - moderate competition"
        })
    else:
        recommendations.append({
            "text": f"✅ No similar chargers ({power_per_plug}kW) within 2km - low competition"
        })
    
    # ROI assessment
    if payback_years < 3:
        recommendations.append({
            "text": f"🎯 Excellent ROI: {payback_years} year payback period"
        })
    elif payback_years < 5:
        recommendations.append({
            "text": f"✅ Good ROI: {payback_years} year payback period"
        })
    elif payback_years < 8:
        recommendations.append({
            "text": f"⚠️ Moderate ROI: {payback_years} year payback period"
        })
    else:
        recommendations.append({
            "text": f"❌ Low ROI: {payback_years}+ year payback period - consider different location or specs"
        })
    
    # Power level recommendations
    if power_per_plug < 50:
        recommendations.append({
            "text": "💡 Consider higher power (50kW+) for faster charging and better revenue"
        })
    elif power_per_plug >= 150:
        recommendations.append({
            "text": "⚡ Ultra-rapid charging attracts premium customers and higher revenue"
        })
    
    return {
        "location": {
            "address": address,
            "latitude": lat,
            "longitude": lon
        },
        "planned_installation": {
            "power_per_plug_kw": power_per_plug,
            "number_of_plugs": num_plugs,
            "total_power_kw": power_per_plug * num_plugs,
            "charger_type": "Level 2" if power_per_plug < 50 else "DC Fast" if power_per_plug < 150 else "DC Ultra-Rapid"
        },
        "chargers": chargers[:100],
        "scores": {
            "overall": round(competition_score, 2),
            "competition": round(competition_score, 2),
            "demand": 0.85,
            "accessibility": 0.75,
            "demographics": 0.70
        },
        "roi_projection": {
            "installation_cost": installation_cost,
            "estimated_annual_revenue": annual_revenue,
            "monthly_revenue": monthly_revenue,
            "payback_period_years": payback_years,
            "break_even_month": int(payback_years * 12)
        },
        "competition_analysis": {
            "total_chargers_in_area": len(chargers),
            "chargers_within_2km": nearby_chargers,
            "similar_power_chargers_nearby": similar_power_nearby
        },
        "recommendations": recommendations
    }

@app.get("/api/power-options")
def power_options():
    """Get available power level options with descriptions"""
    return {
        "options": [
            {
                "power_kw": 7,
                "name": "Level 2 - Home/Workplace",
                "description": "3-5 hours for full charge",
                "installation_cost": 1500,
                "revenue_potential": "Low",
                "use_case": "Workplace, residential"
            },
            {
                "power_kw": 22,
                "name": "Level 2 - Fast",
                "description": "1-2 hours for full charge",
                "installation_cost": 3000,
                "revenue_potential": "Medium",
                "use_case": "Shopping centers, hotels"
            },
            {
                "power_kw": 50,
                "name": "DC Fast Charging",
                "description": "20-30 minutes for 80% charge",
                "installation_cost": 25000,
                "revenue_potential": "High",
                "use_case": "Highway stops, public stations"
            },
            {
                "power_kw": 150,
                "name": "DC Ultra-Rapid",
                "description": "10-15 minutes for 80% charge",
                "installation_cost": 50000,
                "revenue_potential": "Very High",
                "use_case": "Major highways, commercial hubs"
            },
            {
                "power_kw": 350,
                "name": "DC Ultra-Fast (Tesla Supercharger)",
                "description": "5-10 minutes for 80% charge",
                "installation_cost": 80000,
                "revenue_potential": "Premium",
                "use_case": "Premium locations, major routes"
            }
        ]
    }
