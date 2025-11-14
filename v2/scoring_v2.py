"""
EVL v2.0 - Scoring Engine
==========================

Converts raw data into simple 0-100 scores with human-readable interpretations.
"""

from dataclasses import dataclass
from typing import Literal, Optional


def clamp(value: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
    """Clamp value between min and max"""
    return max(min_value, min(max_value, value))


# ==================== INPUT DATA CLASSES ====================

@dataclass
class DemandInputs:
    """Inputs for demand score calculation"""
    ev_density_per_1000_cars: float  # EVs per 1000 cars in area
    traffic_intensity_index: float  # 0-1 normalized traffic
    ev_growth_yoy_percent: float  # Year-over-year EV growth %
    facility_attractiveness_index: float  # 0-1 quality of nearby facilities


@dataclass
class CompetitionInputs:
    """Inputs for competition score"""
    total_chargers: int  # Total chargers in radius
    fast_dc_chargers: int  # Fast DC chargers (≥100 kW)
    radius_km: float  # Search radius
    ev_count_in_area: Optional[float] = None  # Estimated EVs in area


@dataclass
class GridInputs:
    """Inputs for grid feasibility score"""
    distance_km: float  # Distance to nearest substation
    connection_cost_gbp: float  # Estimated connection cost
    available_capacity_kw: float  # Available grid capacity
    required_kw: float  # Required power for installation


@dataclass
class ParkingFacilitiesInputs:
    """Inputs for parking & facilities score"""
    parking_spaces: int  # Number of parking spaces
    facilities_count: int  # Number of relevant facilities (café, shop, etc.)
    site_type: Optional[str] = None  # retail_park, roadside, etc.


# ==================== SCORING FUNCTIONS ====================

def calc_demand_score(inp: DemandInputs) -> int:
    """
    Calculate demand score 0-100
    
    Weights:
    - 40% EV density
    - 30% Traffic intensity
    - 20% EV growth
    - 10% Facility attractiveness
    """
    # Normalize inputs to 0-100
    # 50 EVs per 1000 cars = 100 score
    ev_density_norm = clamp(inp.ev_density_per_1000_cars / 50 * 100)
    
    # Already 0-1, scale to 100
    traffic_norm = clamp(inp.traffic_intensity_index * 100)
    
    # 40%+ growth = 100 score
    growth_norm = clamp(inp.ev_growth_yoy_percent / 40 * 100)
    
    # Already 0-1, scale to 100
    facility_norm = clamp(inp.facility_attractiveness_index * 100)
    
    # Weighted sum
    score = (
        0.4 * ev_density_norm +
        0.3 * traffic_norm +
        0.2 * growth_norm +
        0.1 * facility_norm
    )
    
    return int(round(score))


def calc_competition_score(inp: CompetitionInputs) -> int:
    """
    Calculate competition score 0-100
    
    Higher score = LESS competition (better for user)
    
    Simple v1 logic:
    - 0 fast DC chargers → 90-100 (excellent)
    - 1-2 fast DC → 70-80 (good)
    - 3-5 fast DC → 50-60 (moderate)
    - 6-10 fast DC → 30-40 (high competition)
    - 10+ fast DC → 0-20 (very high competition)
    """
    fast_dc = inp.fast_dc_chargers
    
    if fast_dc == 0:
        # No fast DC competition - excellent!
        return 95
    elif fast_dc <= 2:
        # Some competition but still good
        return 75
    elif fast_dc <= 5:
        # Moderate competition
        return 55
    elif fast_dc <= 10:
        # High competition
        return 35
    else:
        # Very high competition
        return 15


def calc_grid_score(inp: GridInputs) -> int:
    """
    Calculate grid feasibility score 0-100
    
    Weights:
    - 30% Distance to substation
    - 40% Connection cost
    - 30% Available capacity
    """
    # Distance score: >5km = 0, <0.5km = 100
    dist_score = 100 - clamp(inp.distance_km * 20, 0, 100)
    
    # Cost score: >£50k = 0, <£5k = 100
    cost_score = 100 - clamp(inp.connection_cost_gbp / 500, 0, 100)
    
    # Capacity score: need at least required_kw
    if inp.required_kw > 0:
        cap_ratio = inp.available_capacity_kw / inp.required_kw
        cap_score = clamp(cap_ratio * 100, 0, 100)
    else:
        cap_score = 50  # Unknown
    
    # Weighted sum
    score = (
        0.3 * dist_score +
        0.4 * cost_score +
        0.3 * cap_score
    )
    
    return int(round(score))


def calc_parking_facilities_score(inp: ParkingFacilitiesInputs) -> int:
    """
    Calculate parking & facilities score 0-100
    
    Weights:
    - 60% Parking availability
    - 40% Nearby facilities
    """
    # Parking score: 50+ spaces = 100
    parking_score = clamp(inp.parking_spaces / 50 * 100, 0, 100)
    
    # Facilities score: 5+ good facilities = 100
    facilities_score = clamp(inp.facilities_count / 5 * 100, 0, 100)
    
    # Weighted sum
    score = (
        0.6 * parking_score +
        0.4 * facilities_score
    )
    
    return int(round(score))


def calc_overall_score(
    demand: int,
    competition: int,
    grid: int,
    parking_facilities: int
) -> int:
    """
    Calculate overall score 0-100
    
    Weights:
    - 40% Demand
    - 30% Competition
    - 20% Grid
    - 10% Parking/Facilities
    """
    score = (
        0.4 * demand +
        0.3 * competition +
        0.2 * grid +
        0.1 * parking_facilities
    )
    
    return int(round(score))


# ==================== INTERPRETATION FUNCTIONS ====================

def verdict_from_score(score: int) -> Literal["EXCELLENT", "GOOD", "MODERATE", "WEAK", "NOT_RECOMMENDED"]:
    """Convert overall score to verdict"""
    if score >= 80:
        return "EXCELLENT"
    elif score >= 65:
        return "GOOD"
    elif score >= 50:
        return "MODERATE"
    elif score >= 30:
        return "WEAK"
    else:
        return "NOT_RECOMMENDED"


def interpret_score(score: int) -> tuple[str, str]:
    """
    Interpret any score 0-100
    
    Returns: (category, description)
    """
    if score >= 80:
        return ("EXCELLENT", "Outstanding opportunity")
    elif score >= 65:
        return ("GOOD", "Strong potential")
    elif score >= 50:
        return ("MODERATE", "Viable but with considerations")
    elif score >= 30:
        return ("WEAK", "Significant challenges")
    else:
        return ("VERY_WEAK", "Not recommended")


def interpret_demand(score: int) -> str:
    """Demand-specific interpretation"""
    if score >= 80:
        return "Very high EV demand with strong growth. Excellent market potential."
    elif score >= 65:
        return "Good EV presence and traffic. Strong charging demand expected."
    elif score >= 50:
        return "Moderate demand. Suitable for strategic installations."
    elif score >= 30:
        return "Low demand. Consider targeting specific user groups."
    else:
        return "Very weak demand. EV adoption still emerging in this area."


def interpret_competition(score: int) -> str:
    """Competition-specific interpretation"""
    if score >= 80:
        return "Minimal competition. Excellent opportunity to establish presence."
    elif score >= 65:
        return "Low competition. Good positioning opportunity."
    elif score >= 50:
        return "Moderate competition. Differentiation through speed/service recommended."
    elif score >= 30:
        return "High competition. Market already well-served."
    else:
        return "Very high competition. Saturated market."


def interpret_grid(score: int) -> str:
    """Grid-specific interpretation"""
    if score >= 80:
        return "Excellent grid access. Low connection cost expected."
    elif score >= 65:
        return "Good grid feasibility. Standard connection process."
    elif score >= 50:
        return "Moderate grid challenges. Confirm capacity with DNO."
    elif score >= 30:
        return "Difficult grid connection. High costs likely."
    else:
        return "Poor grid access. Major infrastructure investment required."


def connection_cost_category(cost_gbp: float) -> Literal["LOW", "MEDIUM", "HIGH"]:
    """Categorize connection cost"""
    if cost_gbp < 10000:
        return "LOW"
    elif cost_gbp < 50000:
        return "MEDIUM"
    else:
        return "HIGH"


def roi_classification(payback_years: Optional[float]) -> Literal["EXCELLENT", "GOOD", "MODERATE", "WEAK", "POOR"]:
    """Classify ROI based on payback period"""
    if payback_years is None or payback_years < 0:
        return "POOR"
    elif payback_years < 3:
        return "EXCELLENT"
    elif payback_years < 5:
        return "GOOD"
    elif payback_years < 7:
        return "MODERATE"
    elif payback_years < 10:
        return "WEAK"
    else:
        return "POOR"


# ==================== RECOMMENDATION LOGIC ====================

def generate_key_reasons(
    demand_score: int,
    competition_score: int,
    grid_score: int,
    parking_score: int,
    fast_dc_count: int,
    connection_cost: float
) -> list[str]:
    """Generate 3-5 key reasons for the verdict"""
    reasons = []
    
    # Demand reasons
    if demand_score >= 70:
        reasons.append("High EV density and strong growth potential")
    elif demand_score >= 50:
        reasons.append("Moderate EV demand with growth opportunity")
    
    # Competition reasons
    if competition_score >= 80:
        reasons.append("No fast DC chargers nearby - strong market gap")
    elif fast_dc_count == 0:
        reasons.append("No comparable fast chargers in area")
    elif competition_score >= 60:
        reasons.append("Limited competition for fast charging")
    
    # Grid reasons
    if grid_score >= 70:
        reasons.append("Favorable grid connection conditions")
    elif connection_cost < 10000:
        reasons.append("Low grid connection cost estimated")
    
    # Parking/facilities
    if parking_score >= 70:
        reasons.append("Good parking availability and facilities")
    
    # Limit to 5 most important
    return reasons[:5]


def generate_headline_recommendation(
    plugs: int,
    power_per_plug_kw: float,
    charger_type: str,
    verdict: str
) -> str:
    """Generate one-line recommendation"""
    if verdict in ["EXCELLENT", "GOOD"]:
        return f"Recommended: Install {plugs} × {power_per_plug_kw:.0f} kW {charger_type} chargers"
    elif verdict == "MODERATE":
        return f"Viable: Consider {plugs} × {power_per_plug_kw:.0f} kW {charger_type} chargers after validation"
    elif verdict == "WEAK":
        return f"Caution: {plugs} × {power_per_plug_kw:.0f} kW {charger_type} may face challenges"
    else:
        return f"Not recommended: Location unsuitable for {charger_type} charging hub"


def generate_gap_analysis(fast_dc_count: int, total_count: int, radius_km: float) -> str:
    """Generate competition gap analysis"""
    if fast_dc_count == 0:
        return f"⚡ No fast DC chargers within {radius_km}km - strong opportunity to fill charging gap"
    elif fast_dc_count < 3:
        return f"Limited fast charging options ({fast_dc_count} fast DC stations) - good positioning opportunity"
    elif fast_dc_count < 6:
        return f"Moderate fast charging presence ({fast_dc_count} stations) - differentiation recommended"
    else:
        return f"High competition ({fast_dc_count} fast DC stations) - market already well-served"


def generate_next_steps(verdict: str, grid_score: int) -> list[str]:
    """Generate recommended next steps"""
    steps = []
    
    if verdict in ["EXCELLENT", "GOOD", "MODERATE"]:
        if grid_score < 70:
            steps.append("Submit grid capacity request to DNO/DSO - confirm available capacity")
        else:
            steps.append("Initiate formal grid connection enquiry")
        
        steps.append("Validate land ownership and lease terms")
        steps.append("Conduct detailed site survey and access assessment")
        steps.append("Begin planning permission process")
        steps.append("Develop detailed business case with updated financials")
    else:
        steps.append("Reconsider location - explore alternative sites")
        steps.append("Evaluate lower-power installation options")
        steps.append("Conduct market research on specific user needs")
    
    return steps[:5]


def generate_risks(
    verdict: str,
    competition_score: int,
    grid_score: int,
    demand_score: int
) -> list[str]:
    """Generate key risks to consider"""
    risks = []
    
    if grid_score < 60:
        risks.append("Grid capacity must be confirmed with DNO - costs may vary significantly")
    
    if competition_score < 50:
        risks.append("High competition may limit market share and pricing power")
    
    if demand_score < 50:
        risks.append("Demand projections uncertain - market still developing in this area")
    
    risks.append("Regulatory changes could impact charging tariffs and profitability")
    
    if verdict in ["MODERATE", "WEAK"]:
        risks.append("Payback period may extend beyond projections")
    
    return risks[:5]
