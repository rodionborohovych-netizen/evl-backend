"""
EVL v2 API - Business-Focused Location Analysis
Response structure matches frontend (index.html) expectations
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel

# Export router_v2 (required by main.py)
router_v2 = APIRouter()

# ============================================================================
# REQUEST MODELS
# ============================================================================

class LocationInput(BaseModel):
    postcode: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    city: Optional[str] = None
    address: Optional[str] = None

class PlannedInstallation(BaseModel):
    charger_type: str = "DC"
    power_per_plug_kw: float = 150
    plugs: int = 2

class FinancialParams(BaseModel):
    energy_cost_per_kwh: float = 0.20
    tariff_per_kwh: float = 0.50
    fixed_costs_per_month: float = 500

class AnalysisOptions(BaseModel):
    include_raw_sources: bool = False

class AnalysisRequest(BaseModel):
    location: LocationInput
    radius_km: float = 1.0
    planned_installation: PlannedInstallation = PlannedInstallation()
    financial_params: FinancialParams = FinancialParams()
    options: AnalysisOptions = AnalysisOptions()

# ============================================================================
# API ENDPOINTS
# ============================================================================

@router_v2.get("/")
async def v2_root():
    """V2 API root endpoint"""
    return {
        "version": "2.0",
        "status": "active",
        "description": "Business-focused EV charging location analysis API",
        "endpoints": {
            "analyze": "/api/v2/analyze-location",
            "health": "/api/v2/health"
        }
    }

@router_v2.post("/analyze-location")
async def analyze_location(request: AnalysisRequest) -> Dict[str, Any]:
    """
    Analyze location for EV charging - returns mock data matching frontend structure
    
    TODO: Replace this mock response with real analysis logic
    """
    
    location = request.location
    install = request.planned_installation
    financial = request.financial_params
    
    # Validate location
    if not any([location.postcode, location.lat and location.lon, location.city, location.address]):
        raise HTTPException(
            status_code=400,
            detail="Must provide location: postcode, coordinates, city, or address"
        )
    
    location_name = (
        location.postcode or location.city or location.address or 
        f"{location.lat}, {location.lon}" if location.lat else "Unknown"
    )
    
    # Calculate some basic values from inputs
    total_power_kw = install.power_per_plug_kw * install.plugs
    
    # Hardware cost estimation
    hardware_cost = install.power_per_plug_kw * install.plugs * 800  # £800/kW
    installation_cost = hardware_cost * 0.20  # 20% of hardware
    grid_connection = 15000  # Estimated
    other_costs = (hardware_cost + installation_cost + grid_connection) * 0.05
    total_capex = hardware_cost + installation_cost + grid_connection + other_costs
    
    # Revenue estimation (mock)
    sessions_per_day = 17.6  # Mock value
    kwh_per_session = 30
    daily_kwh = sessions_per_day * kwh_per_session
    daily_revenue = daily_kwh * financial.tariff_per_kwh
    monthly_revenue = daily_revenue * 30
    annual_revenue = monthly_revenue * 12
    
    # Costs
    energy_cost_annual = daily_kwh * financial.energy_cost_per_kwh * 365
    fixed_cost_annual = financial.fixed_costs_per_month * 12
    total_opex = energy_cost_annual + fixed_cost_annual
    
    # Gross margin
    gross_margin_per_kwh = financial.tariff_per_kwh - financial.energy_cost_per_kwh
    annual_gross_margin = daily_kwh * gross_margin_per_kwh * 365
    
    # Net profit & payback
    net_profit_annual = annual_gross_margin - fixed_cost_annual
    payback_years = total_capex / net_profit_annual if net_profit_annual > 0 else None
    payback_months = int(payback_years * 12) if payback_years else None
    
    # ROI
    simple_roi_percent = (net_profit_annual / total_capex * 100) if total_capex > 0 else 0
    
    # Determine ROI classification
    if simple_roi_percent >= 20:
        roi_class = "EXCELLENT"
    elif simple_roi_percent >= 15:
        roi_class = "GOOD"
    elif simple_roi_percent >= 10:
        roi_class = "MODERATE"
    elif simple_roi_percent >= 5:
        roi_class = "WEAK"
    else:
        roi_class = "POOR"
    
    # Financial summary text
    if payback_years and payback_years < 7:
        financial_summary = f"✅ Good financials: {payback_years:.1f} year payback, £{int(monthly_revenue):,}/month revenue"
    elif payback_years:
        financial_summary = f"⚠️ Long payback period: {payback_years:.1f} years. Consider reducing CAPEX or increasing utilization."
    else:
        financial_summary = "❌ Not profitable with current assumptions. Requires demand increase or cost reduction."
    
    # ========================================================================
    # RESPONSE STRUCTURE - MATCHES FRONTEND EXPECTATIONS
    # ========================================================================
    
    response = {
        # Summary section
        "summary": {
            "verdict": "GOOD",  # EXCELLENT, GOOD, MODERATE, WEAK, NOT_RECOMMENDED
            "overall_score": 68,
            "headline_recommendation": f"Install {install.plugs} × {install.power_per_plug_kw} kW {install.charger_type} chargers",
            "key_reasons": [
                "High EV density and strong growth",
                f"No fast {install.charger_type} chargers nearby",
                "Low grid connection cost",
                f"{roi_class.title()} ROI: {simple_roi_percent:.1f}% annually"
            ]
        },
        
        # Detailed scores
        "scores": {
            "demand": 72,
            "competition": 85,
            "grid_feasibility": 65,
            "parking_facilities": 60
        },
        
        # Demand analysis block
        "demand_block": {
            "ev_density_per_1000_cars": 35.2,
            "population_density_per_km2": 8500,
            "ev_growth_yoy_percent": 28.5,
            "estimated_sessions_per_day": {
                "low": sessions_per_day * 0.7,
                "central": sessions_per_day,
                "high": sessions_per_day * 1.4
            },
            "demand_interpretation": "Good EV presence and growing market"
        },
        
        # Competition analysis block
        "competition_block": {
            "total_stations": 12,
            "fast_dc_stations": 0,  # No fast DC - market gap!
            "ac_only_stations": 12,
            "competition_index": 0.15,
            "gap_analysis": f"No fast {install.charger_type} chargers within {request.radius_km}km - strong opportunity"
        },
        
        # Grid analysis block
        "grid_block": {
            "nearest_substation_distance_km": 1.5,
            "estimated_connection_cost_gbp": grid_connection,
            "connection_cost_category": "LOW" if grid_connection < 20000 else "MEDIUM",
            "capacity_category": "high",
            "assumptions": [
                "Grid connection cost is estimated - DNO quote required",
                "Assumes adequate grid capacity available",
                "~50 parking spaces estimated for location"
            ]
        },
        
        # Financial analysis
        "financials": {
            # CAPEX breakdown
            "capex": {
                "charger_hardware": hardware_cost,
                "installation_and_civils": installation_cost,
                "grid_connection": grid_connection,
                "other": other_costs,
                "total_capex": total_capex
            },
            
            # Revenue projections
            "revenue": {
                "sessions_per_day": sessions_per_day,
                "avg_kwh_per_session": kwh_per_session,
                "tariff_per_kwh": financial.tariff_per_kwh,
                "energy_cost_per_kwh": financial.energy_cost_per_kwh,
                "gross_margin_per_kwh": gross_margin_per_kwh,
                "monthly_revenue": monthly_revenue,
                "annual_revenue": annual_revenue,
                "annual_gross_margin": annual_gross_margin
            },
            
            # OPEX breakdown
            "opex": {
                "energy_cost_per_year": energy_cost_annual,
                "other_fixed_costs_per_year": fixed_cost_annual,
                "total_opex_per_year": total_opex
            },
            
            # ROI metrics
            "roi": {
                "payback_years": payback_years,
                "payback_months": payback_months,
                "simple_roi_percent": simple_roi_percent if simple_roi_percent > 0 else None,
                "roi_classification": roi_class
            },
            
            "financial_summary": financial_summary
        },
        
        # Recommended configuration
        "recommended_configuration": {
            "primary": {
                "charger_type": install.charger_type,
                "power_per_plug_kw": install.power_per_plug_kw,
                "plugs": install.plugs,
                "rationale": f"Optimal configuration for demand level and grid capacity. Fills market gap for fast {install.charger_type} charging."
            }
        },
        
        # Action items
        "next_steps": [
            "Submit grid capacity request to DNO/DSO",
            "Validate land ownership and lease terms",
            "Conduct detailed site survey and access assessment",
            "Begin planning permission process",
            "Finalize equipment procurement strategy"
        ],
        
        # Risk factors
        "risks": [
            "Grid capacity must be confirmed with DNO - costs may vary",
            f"Competition could increase if networks add fast {install.charger_type} chargers nearby",
            "Utilization assumptions based on market averages - site-specific validation recommended",
            "Regulatory and planning permission timeline could delay project"
        ],
        
        # Data quality (optional)
        "data_sources": {
            "quality_score": 65,
            "sources_used": 7,
            "sources_total": 15,
            "sources": [
                {"name": "OpenChargeMap", "status": "ok"},
                {"name": "OpenStreetMap", "status": "ok"},
                {"name": "Mock Data", "status": "ok"},
                {"name": "Calculated Estimates", "status": "ok"}
            ]
        } if request.options.include_raw_sources else None,
        
        # Metadata
        "metadata": {
            "location_name": location_name,
            "analysis_timestamp": "2025-11-21T19:30:00Z",
            "api_version": "2.0",
            "is_mock_data": True
        }
    }
    
    return response

@router_v2.get("/health")
async def v2_health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0",
        "message": "V2 API operational with mock data"
    }

# ============================================================================
# INTEGRATION NOTES
# ============================================================================

"""
This API returns MOCK DATA that matches your frontend's expected structure.

The response includes:
✅ summary.headline_recommendation (frontend expects this)
✅ summary.key_reasons[] (frontend expects this)
✅ demand_block with all expected fields
✅ competition_block with all expected fields
✅ grid_block with all expected fields
✅ financials with nested CAPEX, revenue, OPEX, ROI
✅ recommended_configuration.primary
✅ next_steps[], risks[]
✅ data_sources (optional)

TO ADD REAL DATA:
1. Import your data fetching functions
2. Replace mock values with real API calls
3. Keep the response structure exactly as is
4. Frontend will work without changes

Example:
```python
from v2.data_fetchers import fetch_chargers, calculate_ev_density

@router_v2.post("/analyze-location")
async def analyze_location(request: AnalysisRequest):
    # Get real data
    chargers = await fetch_chargers(lat, lon, radius)
    ev_density = await calculate_ev_density(location)
    
    # Return same structure with real values
    return {
        "summary": {...},
        "scores": {...},
        "demand_block": {
            "ev_density_per_1000_cars": ev_density,  # Real value
            # ...
        }
    }
```
"""

# Verify router export
assert router_v2 is not None
assert isinstance(router_v2, APIRouter)
