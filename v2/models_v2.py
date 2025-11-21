"""
Models V2 Additions - To be added to v2/models_v2.py
=====================================================

Copy these model definitions to the END of your v2/models_v2.py file.
These models support the v2.2 enhancements.

Instructions:
1. Open v2/models_v2.py
2. Scroll to the bottom of the file
3. Add a comment: "# === V2.2 Enhancements - Model Additions ==="
4. Paste ALL the code below
5. Save the file

"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# ============================================================================
# COMPETITIVE GAP ANALYSIS MODELS
# ============================================================================

class CompetitivePowerBreakdown(BaseModel):
    """Breakdown of existing chargers by power level"""
    power_7kw: int = Field(..., description="Number of 7kW chargers")
    power_22kw: int = Field(..., description="Number of 22kW chargers")
    power_50kw: int = Field(..., description="Number of 50kW chargers")
    power_150kw: int = Field(..., description="Number of 150kW+ chargers")
    total_chargers: int = Field(..., description="Total chargers in area")

    class Config:
        json_schema_extra = {
            "example": {
                "power_7kw": 12,
                "power_22kw": 8,
                "power_50kw": 3,
                "power_150kw": 1,
                "total_chargers": 24
            }
        }


class PowerLevelGap(BaseModel):
    """Represents a gap in charger power levels"""
    power_level: str = Field(..., description="Power level (e.g., '7kW', '22kW')")
    current_count: int = Field(..., description="Current number of chargers at this level")
    market_average: int = Field(..., description="Market average for this area type")
    gap_size: int = Field(..., description="Difference from market average")
    gap_percentage: float = Field(..., description="Gap as percentage of market average")
    opportunity_score: float = Field(..., description="Opportunity score (0-10)")
    reasoning: str = Field(..., description="Explanation of the gap")
    is_blue_ocean: bool = Field(..., description="Whether this is a Blue Ocean opportunity")

    class Config:
        json_schema_extra = {
            "example": {
                "power_level": "150kW+",
                "current_count": 0,
                "market_average": 3,
                "gap_size": 3,
                "gap_percentage": 100.0,
                "opportunity_score": 8.5,
                "reasoning": "Gap of 3 chargers at 150kW+ vs market average. High demand potential with 12.5% EV adoption.",
                "is_blue_ocean": True
            }
        }


class BlueOceanOpportunity(BaseModel):
    """Blue Ocean opportunity details"""
    power_level: str = Field(..., description="Power level with opportunity")
    opportunity_score: float = Field(..., description="Opportunity score (0-10)")
    description: str = Field(..., description="Detailed description of opportunity")

    class Config:
        json_schema_extra = {
            "example": {
                "power_level": "150kW+",
                "opportunity_score": 8.5,
                "description": "Blue Ocean: 150kW+ chargers are severely underserved. Only 0 vs market average of 3. First-mover advantage available."
            }
        }


class CompetitiveGapSummary(BaseModel):
    """Summary of competitive gap analysis"""
    total_gap_chargers: int = Field(..., description="Total gap in number of chargers")
    average_opportunity_score: float = Field(..., description="Average opportunity score")
    blue_ocean_count: int = Field(..., description="Number of Blue Ocean opportunities")
    location_type: str = Field(..., description="Location type analyzed")

    class Config:
        json_schema_extra = {
            "example": {
                "total_gap_chargers": 8,
                "average_opportunity_score": 6.3,
                "blue_ocean_count": 2,
                "location_type": "urban_medium_density"
            }
        }


class CompetitiveGapAnalysisResponse(BaseModel):
    """Complete competitive gap analysis response"""
    power_breakdown: Dict[str, int] = Field(..., description="Current power level breakdown")
    gaps: List[PowerLevelGap] = Field(..., description="Identified gaps by power level")
    blue_ocean_opportunities: List[BlueOceanOpportunity] = Field(..., description="Blue Ocean opportunities")
    summary: CompetitiveGapSummary = Field(..., description="Analysis summary")

    class Config:
        json_schema_extra = {
            "example": {
                "power_breakdown": {
                    "7kW": 5,
                    "22kW": 3,
                    "50kW": 1,
                    "150kW+": 0
                },
                "gaps": [],
                "blue_ocean_opportunities": [],
                "summary": {
                    "total_gap_chargers": 8,
                    "average_opportunity_score": 6.3,
                    "blue_ocean_count": 2,
                    "location_type": "urban_medium_density"
                }
            }
        }


# ============================================================================
# CONFIDENCE ASSESSMENT MODELS
# ============================================================================

class ConfidenceAssessmentResponse(BaseModel):
    """Comprehensive confidence assessment"""
    overall_confidence: float = Field(..., ge=0, le=1, description="Overall confidence score (0-1)")
    data_quality_score: float = Field(..., ge=0, le=1, description="Data quality score (0-1)")
    sample_size_score: float = Field(..., ge=0, le=1, description="Sample size adequacy score (0-1)")
    source_reliability_score: float = Field(..., ge=0, le=1, description="Source reliability score (0-1)")
    consistency_score: float = Field(..., ge=0, le=1, description="Internal consistency score (0-1)")
    reasoning: str = Field(..., description="Human-readable confidence explanation")
    caveats: List[str] = Field(..., description="Important caveats and limitations")
    strengths: List[str] = Field(..., description="Analysis strengths")

    class Config:
        json_schema_extra = {
            "example": {
                "overall_confidence": 0.78,
                "data_quality_score": 0.85,
                "sample_size_score": 0.70,
                "source_reliability_score": 0.90,
                "consistency_score": 0.75,
                "reasoning": "High confidence in recommendations. Based on strong data quality, highly reliable sources.",
                "caveats": [
                    "Sample sizes for traffic data are limited",
                    "Seasonal variations not fully captured"
                ],
                "strengths": [
                    "Data from highly reliable government and industry sources",
                    "Internally consistent analysis across all metrics"
                ]
            }
        }


# ============================================================================
# ENHANCED OPPORTUNITY MODELS
# ============================================================================

class EnhancedOpportunityResponse(BaseModel):
    """Enhanced opportunity with detailed actionability"""
    title: str = Field(..., description="Opportunity title")
    description: str = Field(..., description="Detailed description")
    priority: str = Field(..., description="Priority level: critical, high, medium, low")
    impact_score: float = Field(..., ge=0, le=10, description="Expected impact (0-10)")
    effort_score: float = Field(..., ge=0, le=10, description="Required effort (0-10, higher = more effort)")
    roi_multiplier: float = Field(..., description="Expected ROI multiplier")
    timeframe: str = Field(..., description="Expected implementation timeframe")
    risk_level: str = Field(..., description="Risk level: low, medium, high, critical")
    risk_factors: List[str] = Field(..., description="Identified risk factors")
    mitigation_strategies: List[str] = Field(..., description="Risk mitigation strategies")
    success_metrics: List[str] = Field(..., description="Success measurement criteria")
    next_steps: List[str] = Field(..., description="Recommended next steps")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Blue Ocean Market Entry",
                "description": "Blue Ocean: 150kW+ chargers are severely underserved in this area.",
                "priority": "high",
                "impact_score": 9.0,
                "effort_score": 7.0,
                "roi_multiplier": 2.5,
                "timeframe": "12-18 months",
                "risk_level": "medium",
                "risk_factors": [
                    "First-mover risk - market may be unproven",
                    "Higher initial marketing costs"
                ],
                "mitigation_strategies": [
                    "Start with pilot phase (2-4 chargers)",
                    "Secure long-term site agreements"
                ],
                "success_metrics": [
                    "Market share >30% within 12 months",
                    "Utilization rate >40% within 6 months"
                ],
                "next_steps": [
                    "Conduct detailed site survey",
                    "Secure grid connection approval"
                ]
            }
        }


# ============================================================================
# UPDATED LOCATION ANALYSIS RESPONSE (ADD TO EXISTING)
# ============================================================================

# NOTE: You should UPDATE your existing LocationAnalysisResponse model
# to include these three new fields. Add them as optional fields first,
# then make them required once you've integrated the enhancements.

# Add these lines to your EXISTING LocationAnalysisResponse class:

    # V2.2 Enhancement Fields
    competitive_gaps: Optional[CompetitiveGapAnalysisResponse] = Field(
        None,
        description="Competitive gap analysis with Blue Ocean opportunities"
    )
    
    confidence_assessment: Optional[ConfidenceAssessmentResponse] = Field(
        None,
        description="Confidence assessment of the analysis"
    )
    
    enhanced_opportunities: Optional[List[EnhancedOpportunityResponse]] = Field(
        None,
        description="Enhanced opportunities with risk and ROI details"
    )


# ============================================================================
# USAGE NOTES
# ============================================================================

"""
After adding these models, your updated LocationAnalysisResponse will return:

{
    "summary": {...},              # Existing
    "scores": {...},               # Existing
    "demand": {...},               # Existing
    "competition": {...},          # Existing
    "location": {...},             # Existing
    "recommendations": [...],      # Existing
    "risks": [...],                # Existing
    "next_steps": [...],           # Existing
    "competitive_gaps": {...},     # NEW in v2.2
    "confidence_assessment": {...},# NEW in v2.2
    "enhanced_opportunities": [...] # NEW in v2.2
}

The three new fields provide:
1. Power level gap analysis with Blue Ocean opportunities
2. Meta-assessment of recommendation confidence
3. Detailed, actionable opportunities with risk/ROI

All existing functionality remains unchanged!
"""
