from .enhancements_v22 import (
    CompetitiveGapsAnalysis,
    ConfidenceAssessment,
    EnhancedOpportunities
)
"""
EVL v2.0 - Simplified Business-Focused Models
==============================================

User-focused output with clear verdicts and recommendations.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ==================== REQUEST MODELS ====================

class LocationInput(BaseModel):
    """Location can be postcode or coordinates"""
    postcode: Optional[str] = Field(None, description="UK postcode, e.g. 'NW6 7SD'")
    lat: Optional[float] = Field(None, description="Latitude")
    lon: Optional[float] = Field(None, description="Longitude")


class PlannedInstallation(BaseModel):
    """What the user plans to install"""
    charger_type: Literal["AC", "DC"] = Field(..., description="AC or DC charging")
    power_per_plug_kw: float = Field(..., description="Power per plug in kW")
    plugs: int = Field(..., description="Number of plugs")


class SiteContext(BaseModel):
    """Optional site details"""
    site_type: Optional[str] = Field(None, description="retail_park, roadside, logistics, etc.")
    open_hours: Optional[str] = Field(None, description="24/7 or specific hours")
    parking_spaces: Optional[int] = Field(None, description="Number of parking spaces")


class FinancialParams(BaseModel):
    """Financial assumptions"""
    energy_cost_per_kwh: float = Field(0.20, description="Cost to buy electricity (£/kWh)")
    tariff_per_kwh: float = Field(0.50, description="Charging price to customers (£/kWh)")
    capex_overrides: Optional[float] = Field(None, description="Override total CAPEX if known")
    fixed_costs_per_month: float = Field(500.0, description="Monthly fixed costs (rent, maintenance, etc.)")


class AnalysisOptions(BaseModel):
    """Optional flags"""
    include_raw_sources: bool = Field(False, description="Include detailed data source info")


class AnalyzeLocationRequestV2(BaseModel):
    """
    V2 API Request - Simplified
    """
    location: LocationInput
    radius_km: float = Field(1.0, description="Search radius in km")
    planned_installation: PlannedInstallation
    site_context: Optional[SiteContext] = None
    financial_params: FinancialParams
    options: Optional[AnalysisOptions] = AnalysisOptions()


# ==================== RESPONSE MODELS ====================

class SummaryBlock(BaseModel):
    """5-Second Summary - What user sees first"""
    verdict: Literal["EXCELLENT", "GOOD", "MODERATE", "WEAK", "NOT_RECOMMENDED"] = Field(
        ..., description="Final verdict"
    )
    overall_score: int = Field(..., description="Overall score 0-100")
    headline_recommendation: str = Field(..., description="One-line recommendation")
    key_reasons: List[str] = Field(..., description="3-5 bullet points why")


class ScoresBlock(BaseModel):
    """All scores 0-100"""
    demand: int = Field(..., description="Market demand score")
    competition: int = Field(..., description="Competition score (higher = less competition)")
    grid_feasibility: int = Field(..., description="Grid connection feasibility")
    parking_facilities: int = Field(..., description="Parking and facilities score")
    overall: int = Field(..., description="Weighted overall score")


class SessionsRange(BaseModel):
    """Estimated charging sessions per day"""
    low: float = Field(..., description="Conservative estimate")
    central: float = Field(..., description="Most likely")
    high: float = Field(..., description="Optimistic estimate")


class DemandBlock(BaseModel):
    """Section 1 - Market & Demand"""
    ev_density_per_1000_cars: Optional[float] = Field(None, description="EVs per 1000 cars")
    population_density_per_km2: Optional[float] = Field(None, description="People per km²")
    estimated_sessions_per_day: SessionsRange = Field(..., description="Charging sessions/day")
    ev_growth_yoy_percent: Optional[float] = Field(None, description="EV growth year-over-year %")
    demand_interpretation: str = Field(..., description="Simple text explanation")


class CompetitionBlock(BaseModel):
    """Section 2 - Competition (filtered)"""
    total_stations: int = Field(..., description="Total chargers in radius")
    fast_dc_stations: int = Field(..., description="Fast DC chargers (≥100 kW)")
    ac_only_stations: int = Field(..., description="AC/slow chargers only")
    competition_index: float = Field(..., description="0-1 competition level")
    gap_analysis: str = Field(..., description="Key opportunity/gap identified")
    notes: List[str] = Field(..., description="Short competitive insights")


class GridBlock(BaseModel):
    """Section 3 - Grid & Technical"""
    nearest_substation_distance_km: Optional[float] = Field(None, description="Distance to substation")
    estimated_connection_cost_gbp: Optional[float] = Field(None, description="Estimated grid connection cost")
    capacity_category: Optional[Literal["low", "medium", "high"]] = Field(None, description="Available capacity")
    grid_score: int = Field(..., description="Grid feasibility 0-100")
    connection_cost_category: Literal["LOW", "MEDIUM", "HIGH"] = Field(..., description="Cost category")
    assumptions: List[str] = Field(..., description="Key assumptions made")


class CapexBlock(BaseModel):
    """CAPEX breakdown"""
    charger_hardware: float
    installation_and_civils: float
    grid_connection: float
    other: float
    total_capex: float


class OpexBlock(BaseModel):
    """OPEX estimates"""
    energy_cost_per_year: float
    other_fixed_costs_per_year: float
    total_opex_per_year: float


class RevenueBlock(BaseModel):
    """Revenue projections"""
    sessions_per_day: float
    avg_kwh_per_session: float
    tariff_per_kwh: float
    energy_cost_per_kwh: float
    gross_margin_per_kwh: float
    monthly_revenue: float
    annual_revenue: float
    annual_gross_margin: float


class ROIBlock(BaseModel):
    """ROI summary"""
    payback_years: Optional[float] = Field(None, description="Years to break even")
    payback_months: Optional[int] = Field(None, description="Months to break even")
    simple_roi_percent: Optional[float] = Field(None, description="Annual ROI %")
    roi_classification: Literal["EXCELLENT", "GOOD", "MODERATE", "WEAK", "POOR"] = Field(
        ..., description="ROI quality assessment"
    )


class FinancialsBlock(BaseModel):
    """Section 4 - Financial Projection"""
    capex: CapexBlock
    opex: OpexBlock
    revenue: RevenueBlock
    roi: ROIBlock
    financial_summary: str = Field(..., description="One-line financial assessment")


class ConfigurationOption(BaseModel):
    """Installation configuration"""
    plugs: int
    power_per_plug_kw: float
    total_power_kw: float
    charger_type: str
    rationale: str


class RecommendedConfiguration(BaseModel):
    """Installation recommendations"""
    primary: ConfigurationOption = Field(..., description="Best recommended setup")
    alternatives: List[ConfigurationOption] = Field(default_factory=list, description="Alternative options")


class DataSourceInfo(BaseModel):
    """Individual data source status"""
    name: str
    status: Literal["ok", "partial", "error", "unavailable"]
    used: bool
    quality_percent: Optional[int] = None


class DataSourcesBlock(BaseModel):
    """Data sources - hidden by default"""
    quality_score: int = Field(..., description="Overall data quality 0-100")
    sources_used: int = Field(..., description="Number of sources successfully used")
    sources_total: int = Field(..., description="Total sources attempted")
    sources: List[DataSourceInfo] = Field(..., description="Detailed source info")


class AnalyzeLocationResponseV2(BaseModel):
    """
    V2 API Response - Business-Focused
    ===================================
    
    Simplified output designed for decision-making.
    Technical details hidden unless requested.
    """
    
    # Section 0: 5-Second Summary
    summary: SummaryBlock = Field(..., description="Quick verdict and recommendation")
    
    # Basic info
    location: dict = Field(..., description="Location details")
    
    # Scores (simple 0-100)
    scores: ScoresBlock = Field(..., description="All key scores")
    
    # Section 1: Market & Demand
    demand_block: DemandBlock = Field(..., description="EV demand analysis")
    
    # Section 2: Competition
    competition_block: CompetitionBlock = Field(..., description="Competition analysis")
    
    # Section 3: Grid & Technical
    grid_block: GridBlock = Field(..., description="Grid feasibility")
    
    # Section 4: Financials
    financials: FinancialsBlock = Field(..., description="ROI and financial projections")
    
    # Section 5: Recommendation
    recommended_configuration: RecommendedConfiguration = Field(..., description="What to install")
    next_steps: List[str] = Field(..., description="Suggested actions")
    risks: List[str] = Field(..., description="Key risks to consider")
    
    # Advanced (hidden by default)
    data_sources: Optional[DataSourcesBlock] = Field(None, description="Data source details (advanced)")


# ==================== HELPER MODELS ====================

class ScoreInterpretation(BaseModel):
    """Human-readable score interpretation"""
    score: int
    category: Literal["EXCELLENT", "GOOD", "MODERATE", "WEAK", "VERY_WEAK"]
    color: Literal["green", "lime", "yellow", "orange", "red"]
    description: str
class AnalyzeLocationResponseV2(BaseModel):
    """
    V2.2 API Response - Enhanced with gap analysis and confidence scoring
    """
    
    # ========== EXISTING FIELDS (keep all of these) ==========
    summary: SummaryBlock
    location: dict
    scores: ScoresBlock
    demand_block: DemandBlock
    competition_block: CompetitionBlock
    grid_block: GridBlock
    financials: FinancialsBlock
    recommended_configuration: RecommendedConfiguration
    next_steps: List[str]
    risks: List[str]
    data_sources: Optional[DataSourcesBlock] = None
    
    # ========== NEW v2.2 FIELDS (add these) ==========
    competitive_gaps: CompetitiveGapsAnalysis = Field(
        ..., 
        description="Detailed competitive gap analysis by power level"
    )
    
    confidence_assessment: ConfidenceAssessment = Field(
        ..., 
        description="Confidence score and factors for this analysis"
    )
    
    enhanced_opportunities: EnhancedOpportunities = Field(
        ..., 
        description="Prioritized opportunities with impact assessment"
    )
    
