"""
API V2 Additions - To be added to v2/api_v2.py
================================================

This file shows what code to ADD to your existing v2/api_v2.py file.
Follow the instructions carefully to integrate v2.2 enhancements.

"""

# ============================================================================
# STEP 1: ADD IMPORT AT THE TOP OF THE FILE
# ============================================================================

"""
At the TOP of your v2/api_v2.py file, ADD this import:
(Add it after your other imports, before any function definitions)
"""

from v2.enhancements_v22 import (
    CompetitiveGapAnalyzer,
    ConfidenceAssessor,
    OpportunityEnhancer
)


# ============================================================================
# STEP 2: ADD THIS CODE IN analyze_location FUNCTION
# ============================================================================

"""
In your analyze_location() function, find where you create the response object
(usually near the end, before the return statement).

ADD this code BEFORE the return statement:
"""

def analyze_location_ADDITIONS():
    """
    This is NOT a complete function - just showing what to ADD
    to your existing analyze_location function.
    
    Add this code BEFORE your final return statement.
    """
    
    # === V2.2 Enhancements ===
    # Initialize enhancers
    gap_analyzer = CompetitiveGapAnalyzer()
    confidence_assessor = ConfidenceAssessor()
    opportunity_enhancer = OpportunityEnhancer()
    
    # 1. Competitive Gap Analysis
    # Extract power breakdown from competition data
    power_breakdown = {
        "7kW": 0,
        "22kW": 0,
        "50kW": 0,
        "150kW+": 0
    }
    
    # Count chargers by power level from nearby_chargers
    if nearby_chargers:
        for charger in nearby_chargers:
            power = charger.get("power_kw", 0)
            if power <= 7:
                power_breakdown["7kW"] += 1
            elif power <= 22:
                power_breakdown["22kW"] += 1
            elif power <= 50:
                power_breakdown["50kW"] += 1
            else:
                power_breakdown["150kW+"] += 1
    
    # Determine location type based on population density or facility types
    location_type = "urban_medium_density"  # Default
    
    # Adjust based on available data
    if ev_density and ev_density > 0.15:
        location_type = "urban_high_density"
    elif ev_density and ev_density < 0.05:
        location_type = "suburban"
    
    # Run gap analysis
    competitive_gaps = gap_analyzer.analyze_gaps(
        power_breakdown=power_breakdown,
        location_type=location_type,
        ev_density=ev_density if ev_density else 0.0
    )
    
    # 2. Confidence Assessment
    # Prepare data sources info
    data_sources = {
        "OpenChargeMap": {"quality_score": 0.85},
        "OpenStreetMap": {"quality_score": 0.80},
    }
    
    # Add real API sources if available
    if "entso_e" in locals() or "entso_e" in globals():
        data_sources["ENTSO-E"] = {"quality_score": 0.95}
    if "national_grid" in locals() or "national_grid" in globals():
        data_sources["National Grid"] = {"quality_score": 0.95}
    
    # Prepare sample sizes
    sample_sizes = {
        "chargers": len(nearby_chargers) if nearby_chargers else 0,
        "facilities": len(nearby_facilities) if nearby_facilities else 0,
        "traffic": 100,  # Estimated
    }
    
    # Run confidence assessment
    confidence_assessment = confidence_assessor.assess_confidence(
        data_sources=data_sources,
        sample_sizes=sample_sizes,
        analysis_results={
            "scores": {
                "overall": scores.get("overall", 50),
                "demand": scores.get("demand", 50),
                "competition": scores.get("competition", 50),
            },
            "summary": {
                "verdict": summary.get("verdict", "neutral")
            }
        }
    )
    
    # 3. Enhanced Opportunities
    # Get basic opportunities from existing analysis
    basic_opportunities = opportunities if opportunities else []
    
    # If you have a list of opportunity strings, use them:
    # basic_opportunities = [
    #     "High EV density suggests strong demand",
    #     "Limited competition in area",
    #     # ... etc
    # ]
    
    # Enhance opportunities
    enhanced_opportunities = opportunity_enhancer.enhance_opportunities(
        basic_opportunities=basic_opportunities,
        scores=scores,
        competitive_data=competitive_gaps,
        financial_data={
            "capex": financials.get("capex_total", 0) if financials else 0,
            "revenue": financials.get("revenue_annual", 0) if financials else 0,
            "payback_years": financials.get("payback_years", 0) if financials else 0,
        }
    )
    
    # === END V2.2 Enhancements ===


# ============================================================================
# STEP 3: UPDATE YOUR RETURN STATEMENT
# ============================================================================

"""
Find your existing return statement. It probably looks something like:

return {
    "summary": summary,
    "scores": scores,
    "demand": demand_details,
    "competition": competition_details,
    # ... other fields ...
}

UPDATE it to include the three new fields:
"""

def analyze_location_RETURN_STATEMENT():
    """
    Example of updated return statement.
    Add the three new fields at the end of your existing return dict.
    """
    
    return {
        # === Existing fields (keep these) ===
        "summary": summary,
        "scores": scores,
        "demand": demand_details,
        "competition": competition_details,
        "location": location_details,
        "recommendations": recommendations,
        "risks": risks,
        "next_steps": next_steps,
        "financials": financials,
        
        # === NEW V2.2 fields (add these) ===
        "competitive_gaps": competitive_gaps,
        "confidence_assessment": confidence_assessment.to_dict(),
        "enhanced_opportunities": [opp.to_dict() for opp in enhanced_opportunities],
    }


# ============================================================================
# COMPLETE INTEGRATION EXAMPLE
# ============================================================================

"""
Here's how your analyze_location function should look after integration:
(This is a simplified example - your actual function will be longer)
"""

from typing import Dict, Any
from v2.enhancements_v22 import (
    CompetitiveGapAnalyzer,
    ConfidenceAssessor,
    OpportunityEnhancer
)

async def analyze_location(
    location: Dict[str, Any],
    analysis_type: str = "full"
) -> Dict[str, Any]:
    """
    Analyze a location for EV charging viability
    
    This is a SIMPLIFIED example showing the integration points.
    Your actual function will have much more code.
    """
    
    # ... Your existing code ...
    # (fetch data, calculate scores, generate summary, etc.)
    
    # Example placeholders for existing data
    nearby_chargers = []  # Your fetched charger data
    nearby_facilities = []  # Your fetched facilities
    ev_density = 0.10  # Your calculated EV density
    scores = {"overall": 75, "demand": 80, "competition": 70}
    summary = {"verdict": "good"}
    opportunities = ["High demand area", "Limited competition"]
    financials = {"capex_total": 250000, "revenue_annual": 100000}
    
    # =====================================================
    # V2.2 ENHANCEMENTS START HERE
    # =====================================================
    
    # Initialize enhancers
    gap_analyzer = CompetitiveGapAnalyzer()
    confidence_assessor = ConfidenceAssessor()
    opportunity_enhancer = OpportunityEnhancer()
    
    # 1. Competitive Gap Analysis
    power_breakdown = {"7kW": 0, "22kW": 0, "50kW": 0, "150kW+": 0}
    
    if nearby_chargers:
        for charger in nearby_chargers:
            power = charger.get("power_kw", 0)
            if power <= 7:
                power_breakdown["7kW"] += 1
            elif power <= 22:
                power_breakdown["22kW"] += 1
            elif power <= 50:
                power_breakdown["50kW"] += 1
            else:
                power_breakdown["150kW+"] += 1
    
    location_type = "urban_medium_density"
    if ev_density and ev_density > 0.15:
        location_type = "urban_high_density"
    elif ev_density and ev_density < 0.05:
        location_type = "suburban"
    
    competitive_gaps = gap_analyzer.analyze_gaps(
        power_breakdown=power_breakdown,
        location_type=location_type,
        ev_density=ev_density if ev_density else 0.0
    )
    
    # 2. Confidence Assessment
    data_sources = {
        "OpenChargeMap": {"quality_score": 0.85},
        "OpenStreetMap": {"quality_score": 0.80},
    }
    
    sample_sizes = {
        "chargers": len(nearby_chargers) if nearby_chargers else 0,
        "facilities": len(nearby_facilities) if nearby_facilities else 0,
        "traffic": 100,
    }
    
    confidence_assessment = confidence_assessor.assess_confidence(
        data_sources=data_sources,
        sample_sizes=sample_sizes,
        analysis_results={
            "scores": scores,
            "summary": summary
        }
    )
    
    # 3. Enhanced Opportunities
    enhanced_opportunities = opportunity_enhancer.enhance_opportunities(
        basic_opportunities=opportunities,
        scores=scores,
        competitive_data=competitive_gaps,
        financial_data=financials
    )
    
    # =====================================================
    # V2.2 ENHANCEMENTS END HERE
    # =====================================================
    
    # Return complete response with new fields
    return {
        # Existing fields
        "summary": summary,
        "scores": scores,
        # ... other existing fields ...
        
        # NEW v2.2 fields
        "competitive_gaps": competitive_gaps,
        "confidence_assessment": confidence_assessment.to_dict(),
        "enhanced_opportunities": [opp.to_dict() for opp in enhanced_opportunities],
    }


# ============================================================================
# TROUBLESHOOTING
# ============================================================================

"""
Common Issues:

1. ImportError: Cannot import CompetitiveGapAnalyzer
   Solution: Make sure v2_enhancements.py is renamed to enhancements_v22.py
   and placed in the v2/ directory

2. NameError: nearby_chargers not defined
   Solution: Use whatever variable name you use in your code for charger data

3. AttributeError: has no attribute 'to_dict'
   Solution: The confidence_assessment and opportunity objects have to_dict() methods
   built in. Make sure you're using the correct objects.

4. KeyError: 'power_kw'
   Solution: Adjust the key names to match your charger data structure

5. Response validation error
   Solution: Make sure you've added the new model fields to LocationAnalysisResponse
   in models_v2.py (see models_v2_additions.py)
"""


# ============================================================================
# TESTING YOUR INTEGRATION
# ============================================================================

"""
After integration, test with:

```bash
curl -X POST http://localhost:8000/api/v2/analyze-location \
  -H "Content-Type: application/json" \
  -d '{
    "location": {"postcode": "NW6 7SD"},
    "analysis_type": "full"
  }'
```

You should see three new fields in the response:
- competitive_gaps
- confidence_assessment  
- enhanced_opportunities

If you don't see them, check:
1. Did you add the import at the top?
2. Did you add the enhancement code before return?
3. Did you update the return statement?
4. Did you add the models to models_v2.py?
"""
