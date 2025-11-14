"""
EVL v2.0 - Main API Endpoint
=============================

Simplified, business-focused EV location analysis API.
"""

from fastapi import APIRouter, HTTPException
from models_v2 import (
    AnalyzeLocationRequestV2,
    AnalyzeLocationResponseV2,
    SummaryBlock,
    ScoresBlock,
    DemandBlock,
    SessionsRange,
    CompetitionBlock,
    GridBlock,
    FinancialsBlock,
    CapexBlock,
    OpexBlock,
    RevenueBlock,
    ROIBlock,
    RecommendedConfiguration,
    ConfigurationOption,
    DataSourcesBlock,
    DataSourceInfo
)
from scoring_v2 import (
    DemandInputs,
    CompetitionInputs,
    GridInputs,
    ParkingFacilitiesInputs,
    calc_demand_score,
    calc_competition_score,
    calc_grid_score,
    calc_parking_facilities_score,
    calc_overall_score,
    verdict_from_score,
    interpret_demand,
    interpret_competition,
    interpret_grid,
    connection_cost_category,
    roi_classification,
    generate_key_reasons,
    generate_headline_recommendation,
    generate_gap_analysis,
    generate_next_steps,
    generate_risks
)
from roi_v2 import (
    ROICalculatorInputs,
    calculate_roi,
    estimate_capex,
    estimate_sessions_per_day,
    generate_financial_summary
)

# Create router for v2 endpoints
router_v2 = APIRouter(prefix="/api/v2", tags=["v2"])


@router_v2.post("/analyze-location", response_model=AnalyzeLocationResponseV2)
async def analyze_location_v2(req: AnalyzeLocationRequestV2):
    """
    V2 Location Analysis - Business-Focused Output
    ==============================================
    
    Simplified API that provides:
    - Clear verdict (EXCELLENT → NOT_RECOMMENDED)
    - Simple 0-100 scores with interpretations
    - ROI and payback calculations
    - Actionable recommendations
    - Technical details hidden unless requested
    
    This endpoint uses the same data sources as v1 but presents
    results in a business-friendly format designed for decision-making.
    """
    
    # ==================== INPUT VALIDATION ====================
    
    # Require at least postcode or lat/lon
    if not req.location.postcode and (not req.location.lat or not req.location.lon):
        raise HTTPException(status_code=400, detail="Must provide either postcode or lat/lon")
    
    # Calculate total power required
    required_kw = req.planned_installation.power_per_plug_kw * req.planned_installation.plugs
    
    # ==================== DATA FETCHING ====================
    # TODO: Replace with real API calls
    # For now, using demo data
    
    # These would come from your existing data fetchers:
    # - OpenChargeMap for competition
    # - ENTSO-E for grid
    # - ONS for demographics
    # - DfT for EV stats
    # - etc.
    
    # Demo data (replace with real fetches)
    ev_density_per_1000 = 45.0  # From DfT / ONS
    traffic_intensity = 0.8  # From Overpass / TomTom
    ev_growth_yoy = 38.0  # From DfT vehicle licensing stats
    facility_attractiveness = 0.7  # From OSM facility analysis
    
    total_chargers = 100  # From OpenChargeMap
    fast_dc_chargers = 0  # Fast DC ≥100 kW
    
    distance_to_substation_km = 0.2  # From National Grid / ENTSO-E
    connection_cost_gbp = 2200.0  # Estimated from distance & capacity
    available_capacity_kw = required_kw * 1.5  # Assume 150% available
    
    parking_spaces = req.site_context.parking_spaces if req.site_context else 40
    facilities_count = 3  # Coffee shop, restaurant, WC
    
    # ==================== SCORING ====================
    
    # Calculate individual scores
    demand_inputs = DemandInputs(
        ev_density_per_1000_cars=ev_density_per_1000,
        traffic_intensity_index=traffic_intensity,
        ev_growth_yoy_percent=ev_growth_yoy,
        facility_attractiveness_index=facility_attractiveness
    )
    demand_score = calc_demand_score(demand_inputs)
    
    competition_inputs = CompetitionInputs(
        total_chargers=total_chargers,
        fast_dc_chargers=fast_dc_chargers,
        radius_km=req.radius_km
    )
    competition_score = calc_competition_score(competition_inputs)
    
    grid_inputs = GridInputs(
        distance_km=distance_to_substation_km,
        connection_cost_gbp=connection_cost_gbp,
        available_capacity_kw=available_capacity_kw,
        required_kw=required_kw
    )
    grid_score = calc_grid_score(grid_inputs)
    
    parking_inputs = ParkingFacilitiesInputs(
        parking_spaces=parking_spaces,
        facilities_count=facilities_count,
        site_type=req.site_context.site_type if req.site_context else None
    )
    parking_score = calc_parking_facilities_score(parking_inputs)
    
    # Calculate overall score and verdict
    overall_score = calc_overall_score(
        demand=demand_score,
        competition=competition_score,
        grid=grid_score,
        parking_facilities=parking_score
    )
    verdict = verdict_from_score(overall_score)
    
    # ==================== FINANCIAL CALCULATIONS ====================
    
    # Estimate CAPEX
    capex_breakdown = estimate_capex(
        plugs=req.planned_installation.plugs,
        power_per_plug_kw=req.planned_installation.power_per_plug_kw,
        charger_type=req.planned_installation.charger_type,
        grid_connection_cost=connection_cost_gbp
    )
    
    if req.financial_params.capex_overrides:
        capex_breakdown["total_capex"] = req.financial_params.capex_overrides
    
    # Estimate sessions per day
    sessions_estimate = estimate_sessions_per_day(
        demand_score=demand_score,
        competition_score=competition_score,
        power_per_plug_kw=req.planned_installation.power_per_plug_kw,
        plugs=req.planned_installation.plugs,
        site_type=req.site_context.site_type if req.site_context else None
    )
    
    # Calculate ROI using central estimate
    roi_inputs = ROICalculatorInputs(
        plugs=req.planned_installation.plugs,
        power_per_plug_kw=req.planned_installation.power_per_plug_kw,
        sessions_per_day=sessions_estimate["central"],
        avg_kwh_per_session=30.0,  # Typical for DC fast charging
        tariff_per_kwh=req.financial_params.tariff_per_kwh,
        energy_cost_per_kwh=req.financial_params.energy_cost_per_kwh,
        fixed_costs_per_month=req.financial_params.fixed_costs_per_month,
        capex_total=capex_breakdown["total_capex"]
    )
    
    roi_results = calculate_roi(roi_inputs)
    
    # ==================== BUILD RESPONSE ====================
    
    # Section 0: Summary
    key_reasons = generate_key_reasons(
        demand_score=demand_score,
        competition_score=competition_score,
        grid_score=grid_score,
        parking_score=parking_score,
        fast_dc_count=fast_dc_chargers,
        connection_cost=connection_cost_gbp
    )
    
    headline = generate_headline_recommendation(
        plugs=req.planned_installation.plugs,
        power_per_plug_kw=req.planned_installation.power_per_plug_kw,
        charger_type=req.planned_installation.charger_type,
        verdict=verdict
    )
    
    summary = SummaryBlock(
        verdict=verdict,
        overall_score=overall_score,
        headline_recommendation=headline,
        key_reasons=key_reasons
    )
    
    # Scores
    scores = ScoresBlock(
        demand=demand_score,
        competition=competition_score,
        grid_feasibility=grid_score,
        parking_facilities=parking_score,
        overall=overall_score
    )
    
    # Section 1: Demand
    demand_block = DemandBlock(
        ev_density_per_1000_cars=ev_density_per_1000,
        population_density_per_km2=8200.0,  # From ONS
        estimated_sessions_per_day=SessionsRange(**sessions_estimate),
        ev_growth_yoy_percent=ev_growth_yoy,
        demand_interpretation=interpret_demand(demand_score)
    )
    
    # Section 2: Competition
    gap_analysis = generate_gap_analysis(fast_dc_chargers, total_chargers, req.radius_km)
    
    competition_block = CompetitionBlock(
        total_stations=total_chargers,
        fast_dc_stations=fast_dc_chargers,
        ac_only_stations=total_chargers - fast_dc_chargers,
        competition_index=competition_score / 100,
        gap_analysis=gap_analysis,
        notes=[
            "All existing chargers are low-power AC (4-22 kW)",
            "No DC fast charging infrastructure in area",
            "Strong opportunity for premium fast charging service"
        ]
    )
    
    # Section 3: Grid
    cost_category = connection_cost_category(connection_cost_gbp)
    
    grid_block = GridBlock(
        nearest_substation_distance_km=distance_to_substation_km,
        estimated_connection_cost_gbp=connection_cost_gbp,
        capacity_category="medium",
        grid_score=grid_score,
        connection_cost_category=cost_category,
        assumptions=[
            "Capacity estimated from DNO public data and ENTSO-E statistics",
            "Final grid connection cost must be confirmed with DNO",
            "Actual capacity dependent on current grid loading"
        ]
    )
    
    # Section 4: Financials
    roi_class = roi_classification(roi_results.payback_years)
    financial_summary = generate_financial_summary(
        roi_results.payback_years,
        roi_results.monthly_revenue,
        roi_results.simple_roi_percent
    )
    
    financials = FinancialsBlock(
        capex=CapexBlock(**capex_breakdown),
        opex=OpexBlock(
            energy_cost_per_year=roi_results.annual_energy_cost,
            other_fixed_costs_per_year=roi_results.annual_fixed_costs,
            total_opex_per_year=roi_results.annual_total_opex
        ),
        revenue=RevenueBlock(
            sessions_per_day=sessions_estimate["central"],
            avg_kwh_per_session=30.0,
            tariff_per_kwh=req.financial_params.tariff_per_kwh,
            energy_cost_per_kwh=req.financial_params.energy_cost_per_kwh,
            gross_margin_per_kwh=roi_results.gross_margin_per_kwh,
            monthly_revenue=roi_results.monthly_revenue,
            annual_revenue=roi_results.annual_revenue,
            annual_gross_margin=roi_results.annual_gross_margin
        ),
        roi=ROIBlock(
            payback_years=roi_results.payback_years,
            payback_months=roi_results.payback_months,
            simple_roi_percent=roi_results.simple_roi_percent,
            roi_classification=roi_class
        ),
        financial_summary=financial_summary
    )
    
    # Section 5: Recommendations
    primary_config = ConfigurationOption(
        plugs=req.planned_installation.plugs,
        power_per_plug_kw=req.planned_installation.power_per_plug_kw,
        total_power_kw=required_kw,
        charger_type=req.planned_installation.charger_type,
        rationale="Optimal configuration for demand level and grid capacity. Fills market gap for fast charging."
    )
    
    # Alternative configuration (lower power if grid constrained)
    alt_power = req.planned_installation.power_per_plug_kw / 2
    alternative_config = ConfigurationOption(
        plugs=req.planned_installation.plugs,
        power_per_plug_kw=alt_power,
        total_power_kw=alt_power * req.planned_installation.plugs,
        charger_type=req.planned_installation.charger_type,
        rationale="Alternative for constrained grid scenarios or lower CAPEX budget."
    )
    
    recommended_configuration = RecommendedConfiguration(
        primary=primary_config,
        alternatives=[alternative_config]
    )
    
    next_steps = generate_next_steps(verdict, grid_score)
    risks = generate_risks(verdict, competition_score, grid_score, demand_score)
    
    # Data sources (optional, hidden by default)
    data_sources = None
    if req.options and req.options.include_raw_sources:
        data_sources = DataSourcesBlock(
            quality_score=47,  # Would calculate from actual sources
            sources_used=7,
            sources_total=15,
            sources=[
                DataSourceInfo(name="OpenChargeMap", status="ok", used=True, quality_percent=100),
                DataSourceInfo(name="ENTSO-E Grid", status="partial", used=True, quality_percent=60),
                DataSourceInfo(name="National Grid ESO", status="error", used=False, quality_percent=0),
                DataSourceInfo(name="ONS Demographics", status="ok", used=True, quality_percent=100),
                DataSourceInfo(name="DfT Vehicle Licensing", status="error", used=False, quality_percent=0),
                DataSourceInfo(name="OpenStreetMap", status="ok", used=True, quality_percent=100),
                DataSourceInfo(name="Postcodes.io", status="ok", used=True, quality_percent=100),
            ]
        )
    
    # ==================== RETURN RESPONSE ====================
    
    return AnalyzeLocationResponseV2(
        summary=summary,
        location={
            "postcode": req.location.postcode or f"{req.location.lat},{req.location.lon}",
            "lat": req.location.lat or 51.539,  # Would geocode postcode
            "lon": req.location.lon or -0.191,
            "radius_km": req.radius_km,
            "country": "United Kingdom"
        },
        scores=scores,
        demand_block=demand_block,
        competition_block=competition_block,
        grid_block=grid_block,
        financials=financials,
        recommended_configuration=recommended_configuration,
        next_steps=next_steps,
        risks=risks,
        data_sources=data_sources
    )


@router_v2.get("/health")
async def health_check_v2():
    """V2 API health check"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "api": "EVL Location Analyzer - Business-Focused",
        "features": [
            "Simplified scoring (0-100)",
            "Clear verdicts (EXCELLENT → NOT_RECOMMENDED)",
            "ROI & payback calculations",
            "Actionable recommendations",
            "Hidden technical details"
        ]
    }
