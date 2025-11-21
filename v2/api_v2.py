"""
EVL v2 API - Business-Focused Location Analysis
================================================

Provides comprehensive EV charging location analysis with:
- Demand assessment
- Competition analysis
- Financial projections
- Strategic recommendations
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel

# ============================================================================
# CRITICAL: Export router_v2 (required by main.py)
# ============================================================================
router_v2 = APIRouter()

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class LocationInput(BaseModel):
    """Location specification"""
    postcode: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    city: Optional[str] = None
    address: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "postcode": "NW6 7SD"
            }
        }

class AnalysisRequest(BaseModel):
    """Analysis request parameters"""
    location: LocationInput
    analysis_type: str = "full"  # full, quick, financial_only
    
    class Config:
        json_schema_extra = {
            "example": {
                "location": {"postcode": "NW6 7SD"},
                "analysis_type": "full"
            }
        }

# ============================================================================
# API ENDPOINTS
# ============================================================================

@router_v2.get("/")
async def v2_root():
    """V2 API root endpoint - shows available endpoints"""
    return {
        "version": "2.0",
        "status": "active",
        "description": "Business-focused EV charging location analysis API",
        "endpoints": {
            "analyze": "/api/v2/analyze-location",
            "health": "/api/v2/health",
            "docs": "/api/v2/docs"
        },
        "features": [
            "Demand analysis",
            "Competition assessment", 
            "Financial projections",
            "Strategic recommendations"
        ]
    }

@router_v2.post("/analyze-location")
async def analyze_location(request: AnalysisRequest) -> Dict[str, Any]:
    """
    Analyze a location for EV charging installation viability
    
    This endpoint provides comprehensive business intelligence including:
    - Market demand assessment
    - Competitive landscape analysis
    - Financial projections (ROI, payback period)
    - Strategic recommendations
    
    Args:
        request: Analysis request with location and parameters
        
    Returns:
        Complete location analysis with scores, insights, and recommendations
    """
    
    # Extract location
    location = request.location
    
    # Validate location input
    if not any([location.postcode, location.lat and location.lon, location.city, location.address]):
        raise HTTPException(
            status_code=400,
            detail="Must provide at least one location identifier: postcode, coordinates (lat/lon), city, or address"
        )
    
    # ========================================================================
    # TODO: INTEGRATE YOUR ANALYSIS LOGIC HERE
    # ========================================================================
    # This is a MINIMAL working version that returns mock data.
    # Replace this section with your actual analysis code:
    #
    # 1. Geocode location (if needed)
    # 2. Fetch nearby chargers (OpenChargeMap, etc.)
    # 3. Fetch facilities and POIs (OpenStreetMap)
    # 4. Calculate demand scores
    # 5. Analyze competition
    # 6. Generate financial projections
    # 7. Create recommendations
    #
    # For now, returning structured mock data so the server works.
    # ========================================================================
    
    # Determine location name
    location_name = (
        location.postcode or 
        location.city or 
        location.address or 
        f"{location.lat}, {location.lon}" if location.lat and location.lon else 
        "Unknown Location"
    )
    
    # Mock response structure (replace with real analysis)
    response = {
        "summary": {
            "verdict": "moderate",
            "overall_score": 65,
            "location_name": location_name,
            "recommendation": "Moderate potential for EV charging installation",
            "confidence": "medium"
        },
        
        "scores": {
            "overall": 65,
            "demand": 70,
            "competition": 60,
            "infrastructure": 65,
            "accessibility": 75
        },
        
        "demand": {
            "ev_density": 0.08,
            "population_density": 2500,
            "traffic_volume": 15000,
            "nearby_facilities": ["retail", "office"],
            "dwell_time_estimate": 45,
            "assessment": "Moderate EV adoption in area"
        },
        
        "competition": {
            "total_chargers_5km": 12,
            "nearest_charger_km": 0.8,
            "power_breakdown": {
                "7kW": 5,
                "22kW": 4,
                "50kW": 2,
                "150kW+": 1
            },
            "market_saturation": "medium",
            "competitive_pressure": "moderate"
        },
        
        "financials": {
            "capex_estimate": 150000,
            "annual_revenue_estimate": 45000,
            "payback_years": 3.3,
            "roi_5year": 0.35,
            "assumptions": {
                "utilization_rate": 0.25,
                "avg_session_revenue": 8.50,
                "sessions_per_day": 15
            }
        },
        
        "recommendations": [
            "Consider 50kW DC fast chargers based on area dwell time",
            "Partner with nearby retail locations for traffic capture",
            "Monitor local EV adoption trends quarterly"
        ],
        
        "risks": [
            "Moderate competition within 1km radius",
            "Grid connection costs may vary",
            "Utilization assumptions require validation"
        ],
        
        "next_steps": [
            "Conduct detailed site survey",
            "Engage with local grid operator",
            "Validate traffic patterns with on-site monitoring",
            "Review planning permissions requirements"
        ],
        
        "metadata": {
            "analysis_type": request.analysis_type,
            "timestamp": "2025-11-21T19:00:00Z",
            "data_sources": ["OpenChargeMap", "OpenStreetMap", "Mock Data"],
            "version": "2.0"
        },
        
        "warning": "⚠️ This is a mock response. Integrate your real analysis logic to replace this data."
    }
    
    return response

@router_v2.get("/health")
async def v2_health():
    """Health check endpoint for V2 API"""
    return {
        "status": "healthy",
        "version": "2.0",
        "message": "V2 API is operational",
        "endpoints_active": 3
    }

@router_v2.get("/capabilities")
async def v2_capabilities():
    """List V2 API capabilities and data sources"""
    return {
        "analysis_types": [
            "full",
            "quick", 
            "financial_only"
        ],
        "data_sources": [
            "OpenChargeMap - Charger locations",
            "OpenStreetMap - POI and facilities",
            "Traffic data - Road usage patterns",
            "Demographics - Population and income data"
        ],
        "outputs": [
            "Demand scores",
            "Competition analysis",
            "Financial projections",
            "Strategic recommendations",
            "Risk assessment",
            "Next steps guidance"
        ],
        "features": {
            "geocoding": True,
            "real_time_data": False,
            "historical_analysis": False,
            "financial_modeling": True,
            "competitive_analysis": True
        }
    }

# ============================================================================
# INTEGRATION NOTES
# ============================================================================

"""
This is a MINIMAL working v2 API that will:
1. ✅ Export router_v2 properly (fixes ImportError)
2. ✅ Provide working endpoints
3. ✅ Return structured mock data
4. ⚠️  Need your real analysis logic added

TO INTEGRATE YOUR ANALYSIS:

1. Replace the mock response in analyze_location() with your real code
2. Import your data fetching functions
3. Import your scoring/calculation functions  
4. Use the actual data instead of mock values

Example integration:
```python
from v2.data_fetchers import fetch_chargers, fetch_facilities
from v2.scoring import calculate_demand_score, calculate_competition_score

@router_v2.post("/analyze-location")
async def analyze_location(request: AnalysisRequest):
    location = request.location
    
    # 1. Geocode
    coords = await geocode_location(location)
    
    # 2. Fetch data
    chargers = await fetch_chargers(coords.lat, coords.lon, radius=5)
    facilities = await fetch_facilities(coords.lat, coords.lon)
    
    # 3. Calculate scores
    demand_score = calculate_demand_score(facilities, population_data)
    competition_score = calculate_competition_score(chargers)
    
    # 4. Return real analysis
    return {
        "summary": generate_summary(scores),
        "scores": scores,
        "demand": demand_details,
        # ... etc
    }
```

For v2.2 enhancements (competitive gaps, confidence, opportunities):
- Add after you have real data working
- Follow api_v2_additions.py integration guide
- Import from v2.enhancements_v22
"""

# ============================================================================
# ROUTER EXPORT CONFIRMATION
# ============================================================================

# Verify router_v2 is defined and exported
assert router_v2 is not None, "router_v2 must be defined"
assert isinstance(router_v2, APIRouter), "router_v2 must be an APIRouter instance"

# This file exports: router_v2
# Can be imported by main.py: from v2.api_v2 import router_v2
