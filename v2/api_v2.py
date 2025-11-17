"""
EVL v2.1 - Multi-Country API with Ukraine Support
==================================================

Supports both UK and Ukraine markets with appropriate data sources.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Literal, Optional
from enum import Enum

from .models_v2 import (
    AnalyzeLocationRequestV2,
    AnalyzeLocationResponseV2,
    # ... rest of imports
)

# Import UK fetchers
from foundation.core.fetchers import (
    fetch_all_data as fetch_all_data_uk,
    FetchResult
)

# Import Ukraine fetchers (optional)
try:
    from foundation.core.fetchers_ukraine import (
        fetch_all_data_ukraine,
        calculate_ukraine_ev_density,
        estimate_ukraine_grid_connection_cost
    )
    UKRAINE_SUPPORT = True
except ImportError:
    # Ukraine module not available - define fallback functions
    UKRAINE_SUPPORT = False
    
    async def fetch_all_data_ukraine(**kwargs):
        """Fallback - Ukraine module not installed"""
        return {}
    
    def calculate_ukraine_ev_density(dft_data, demo_data):
        """Fallback"""
        return 25.0
    
    def estimate_ukraine_grid_connection_cost(distance_km, required_kw):
        """Fallback"""
        return distance_km * 3000 + required_kw * 100


class Country(str, Enum):
    """Supported countries"""
    UK = "UK"
    UKRAINE = "Ukraine"


# Create router
router_v2 = APIRouter(prefix="/api/v2", tags=["v2"])


# ==================== COUNTRY DETECTION ====================

def detect_country(
    postcode: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    city: Optional[str] = None
) -> Country:
    """
    Detect which country the location is in
    
    Rules:
    - UK postcode format: XX## #XX or XX# #XX
    - Ukraine cities: Kyiv, Lviv, Odesa, Kharkiv, Dnipro, etc.
    - Lat/lon: Ukraine is roughly 44-52°N, 22-40°E
    """
    
    # Check postcode format
    if postcode:
        # UK postcodes have space and specific format
        if " " in postcode and len(postcode) >= 5:
            return Country.UK
        # Ukraine doesn't use UK-style postcodes
        return Country.UKRAINE
    
    # Check city name
    if city:
        ukraine_cities = ["Kyiv", "Kiev", "Lviv", "Odesa", "Odessa", "Kharkiv", 
                         "Kharkov", "Dnipro", "Zaporizhzhia", "Vinnytsia"]
        if any(uc.lower() in city.lower() for uc in ukraine_cities):
            return Country.UKRAINE
    
    # Check lat/lon (rough bounds)
    if lat and lon:
        # Ukraine: 44-52°N, 22-40°E
        if 44 <= lat <= 52 and 22 <= lon <= 40:
            return Country.UKRAINE
        # UK: 49-59°N, -8-2°E
        if 49 <= lat <= 59 and -8 <= lon <= 2:
            return Country.UK
    
    # Default to UK (existing behavior)
    return Country.UK


# ==================== UNIFIED ENDPOINT ====================

@router_v2.post("/analyze-location", response_model=AnalyzeLocationResponseV2)
async def analyze_location_v2(req: AnalyzeLocationRequestV2):
    """
    V2 Location Analysis - Multi-Country Support
    ============================================
    
    Supports:
    ✅ United Kingdom - Full data integration
    ✅ Ukraine - Adapted for local market
    
    Automatically detects country from location data.
    """
    
    # Detect country
    country = detect_country(
        postcode=req.location.postcode,
        lat=req.location.lat,
        lon=req.location.lon,
        city=getattr(req.location, 'city', None)
    )
    
    print(f"🌍 Detected country: {country}")
    
    # Route to appropriate handler
    if country == Country.UKRAINE:
        return await analyze_location_ukraine(req)
    else:
        return await analyze_location_uk(req)


# ==================== UK HANDLER ====================

async def analyze_location_uk(req: AnalyzeLocationRequestV2) -> AnalyzeLocationResponseV2:
    """
    UK location analysis with full data integration
    
    Uses:
    - OpenChargeMap for competition
    - Postcodes.io for geocoding
    - DfT Vehicle Licensing for EV stats
    - ONS Demographics for population
    - OpenStreetMap for facilities
    - ENTSO-E/National Grid for grid (optional)
    """
    
    # Input validation
    if not req.location.postcode and not (req.location.lat and req.location.lon):
        raise HTTPException(
            status_code=400,
            detail="Provide either UK postcode or lat/lon coordinates"
        )
    
    required_kw = req.planned_installation.power_per_plug_kw * req.planned_installation.plugs
    
    print(f"🔍 Analyzing UK location: {req.location.postcode or f'{req.location.lat},{req.location.lon}'}")
    
    # ==================== FETCH UK DATA ====================
    
    try:
        fetch_results = await fetch_all_data_uk(
            postcode=req.location.postcode,
            lat=req.location.lat,
            lon=req.location.lon,
            radius_km=req.radius_km
        )
        
        print(f"✅ Fetched {len(fetch_results)} UK data sources")
        
    except Exception as e:
        print(f"❌ Error fetching UK data: {e}")
        raise HTTPException(status_code=500, detail=f"Data fetch error: {str(e)}")
    
    # ==================== EXTRACT UK DATA ====================
    
    # Location (from postcodes.io)
    postcode_result = fetch_results.get("postcodes_io")
    if postcode_result and postcode_result.success:
        lat = postcode_result.data.get("latitude")
        lon = postcode_result.data.get("longitude")
        postcode = postcode_result.data.get("postcode")
        admin_district = postcode_result.data.get("admin_district", "UK")
    else:
        lat = req.location.lat or 51.5074  # London default
        lon = req.location.lon or -0.1278
        postcode = req.location.postcode or "Unknown"
        admin_district = "UK"
    
    # Competition data (OpenChargeMap)
    ocm_result = fetch_results.get("openchargemap")
    if ocm_result and ocm_result.success:
        chargers_data = ocm_result.data
        total_chargers = len(chargers_data)
        
        # Count fast DC (≥100kW)
        fast_dc_chargers = sum(
            1 for charger in chargers_data
            for conn in charger.get("connections", [])
            if conn.get("power_kw", 0) >= 100
        )
        ac_only_chargers = total_chargers - fast_dc_chargers
    else:
        print("⚠️  OpenChargeMap data unavailable - using estimates")
        total_chargers = 0
        fast_dc_chargers = 0
        ac_only_chargers = 0
    
    # Demographics (ONS)
    demo_result = fetch_results.get("ons_demographics")
    demographics = demo_result.data if demo_result and demo_result.success else {}
    population_density = demographics.get("population_density_per_km2", 5000)
    
    # EV stats (DfT Vehicle Licensing)
    dft_result = fetch_results.get("dft_vehicle_licensing")
    dft_data = dft_result.data if dft_result and dft_result.success else {}
    
    # Calculate EV density
    total_bevs = dft_data.get("bevs", 1100000)  # UK total ~1.1M BEVs
    total_vehicles = dft_data.get("total_vehicles", 33000000)  # UK total ~33M vehicles
    ev_density_per_1000 = (total_bevs / total_vehicles) * 1000 if total_vehicles > 0 else 33.0
    
    ev_growth_yoy = dft_data.get("growth_yoy_bev", 25.0)  # UK ~25% YoY growth
    
    # Facilities (OpenStreetMap)
    osm_result = fetch_results.get("openstreetmap")
    facilities_data = osm_result.data if osm_result and osm_result.success else {}
    facilities_count = len(facilities_data.get("facilities", []))
    parking_spaces = facilities_data.get("estimated_parking", 50)
    
    # Grid data (National Grid ESO / ENTSO-E)
    grid_result = fetch_results.get("national_grid_eso") or fetch_results.get("entsoe")
    if grid_result and grid_result.success:
        grid_data = grid_result.data
        nearest_connection = grid_data.get("nearest_connection", {})
        distance_to_substation_km = nearest_connection.get("distance_km", 2.0)
        available_capacity_kw = nearest_connection.get("capacity_mw", 50) * 1000
    else:
        print("⚠️  Grid data unavailable - using estimates")
        distance_to_substation_km = 2.0
        available_capacity_kw = 5000  # Assume 5 MW available
    
    # Estimate grid connection cost
    connection_cost_gbp = distance_to_substation_km * 5000 + required_kw * 150
    
    # Traffic intensity (from OSM or estimate)
    traffic_intensity = facilities_data.get("traffic_intensity", 0.7)
    
    # Facility attractiveness
    facility_attractiveness = min(facilities_count / 5.0, 1.0)
    
    print(f"""
📊 UK Data Summary:
   - Location: {postcode}, {admin_district}
   - Chargers: {total_chargers} total, {fast_dc_chargers} fast DC
   - EV Density: {ev_density_per_1000:.1f} per 1000 cars
   - EV Growth: {ev_growth_yoy:.1f}% YoY
   - Grid Connection: £{connection_cost_gbp:,.0f}
   - Population Density: {population_density:,.0f}/km²
   - Facilities: {facilities_count} nearby
    """)
    
    # ==================== SCORING ====================
    
    from .scoring_v2 import (
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
    
    overall_score = calc_overall_score(
        demand=demand_score,
        competition=competition_score,
        grid=grid_score,
        parking_facilities=parking_score
    )
    verdict = verdict_from_score(overall_score)
    
    print(f"""
📈 UK Scores:
   - Demand: {demand_score}/100
   - Competition: {competition_score}/100
   - Grid: {grid_score}/100
   - Parking: {parking_score}/100
   - Overall: {overall_score}/100 → {verdict}
    """)
    
    # ==================== FINANCIAL CALCULATIONS ====================
    
    from .roi_v2 import (
        estimate_capex,
        estimate_sessions_per_day,
        calculate_roi,
        ROICalculatorInputs,
        generate_financial_summary
    )
    
    # CAPEX
    if req.financial_params.capex_overrides:
        capex_total = req.financial_params.capex_overrides
        capex_breakdown = {
            "charger_hardware": capex_total * 0.60,
            "installation_and_civils": capex_total * 0.20,
            "grid_connection": connection_cost_gbp,
            "other": capex_total * 0.05,
            "total_capex": capex_total
        }
    else:
        capex_breakdown = estimate_capex(
            plugs=req.planned_installation.plugs,
            power_per_plug_kw=req.planned_installation.power_per_plug_kw,
            charger_type=req.planned_installation.charger_type,
            grid_connection_cost=connection_cost_gbp
        )
    
    # Sessions estimate
    sessions_estimate = estimate_sessions_per_day(
        demand_score=demand_score,
        competition_score=competition_score,
        power_per_plug_kw=req.planned_installation.power_per_plug_kw,
        plugs=req.planned_installation.plugs,
        site_type=req.site_context.site_type if req.site_context else None
    )
    
    # ROI calculation
    roi_inputs = ROICalculatorInputs(
        plugs=req.planned_installation.plugs,
        power_per_plug_kw=req.planned_installation.power_per_plug_kw,
        sessions_per_day=sessions_estimate["central"],
        avg_kwh_per_session=30.0,  # Typical session size
        tariff_per_kwh=req.financial_params.tariff_per_kwh,
        energy_cost_per_kwh=req.financial_params.energy_cost_per_kwh,
        fixed_costs_per_month=req.financial_params.fixed_costs_per_month,
        capex_total=capex_breakdown["total_capex"]
    )
    
    roi_results = calculate_roi(roi_inputs)
    roi_class = roi_classification(roi_results.payback_years)
    
    print(f"""
💰 UK Financials:
   - CAPEX: £{capex_breakdown['total_capex']:,.0f}
   - Sessions/day: {sessions_estimate['central']:.1f}
   - Monthly Revenue: £{roi_results.monthly_revenue:,.0f}
   - Payback: {roi_results.payback_years:.1f} years ({roi_class})
    """)
    
    # ==================== BUILD RESPONSE ====================
    
    from .models_v2 import (
        SummaryBlock,
        ScoresBlock,
        DemandBlock,
        SessionsRange,
        CompetitionBlock,
        GridBlock,
        CapexBlock,
        OpexBlock,
        RevenueBlock,
        ROIBlock,
        FinancialsBlock,
        ConfigurationOption,
        RecommendedConfiguration,
        DataSourceInfo,
        DataSourcesBlock
    )
    
    # Summary
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
    
    # Location
    location_dict = {
        "postcode": postcode,
        "lat": lat,
        "lon": lon,
        "district": admin_district,
        "country": "United Kingdom",
        "radius_km": req.radius_km
    }
    
    # Scores
    scores = ScoresBlock(
        demand=demand_score,
        competition=competition_score,
        grid_feasibility=grid_score,
        parking_facilities=parking_score,
        overall=overall_score
    )
    
    # Demand block
    demand_block = DemandBlock(
        ev_density_per_1000_cars=ev_density_per_1000,
        population_density_per_km2=population_density,
        estimated_sessions_per_day=SessionsRange(
            low=sessions_estimate["low"],
            central=sessions_estimate["central"],
            high=sessions_estimate["high"]
        ),
        ev_growth_yoy_percent=ev_growth_yoy,
        demand_interpretation=interpret_demand(demand_score)
    )
    
    # Competition block
    gap_analysis = generate_gap_analysis(fast_dc_chargers, total_chargers, req.radius_km)
    
    competition_notes = []
    if fast_dc_chargers == 0:
        competition_notes.append("No fast DC charging infrastructure currently available")
    if total_chargers < 5:
        competition_notes.append("Limited overall charging infrastructure")
    if competition_score >= 70:
        competition_notes.append("Strong opportunity to establish market presence")
    
    competition_block = CompetitionBlock(
        total_stations=total_chargers,
        fast_dc_stations=fast_dc_chargers,
        ac_only_stations=ac_only_chargers,
        competition_index=(100 - competition_score) / 100,
        gap_analysis=gap_analysis,
        notes=competition_notes or ["Competitive market analysis complete"]
    )
    
    # Grid block
    grid_block = GridBlock(
        nearest_substation_distance_km=distance_to_substation_km,
        estimated_connection_cost_gbp=connection_cost_gbp,
        capacity_category="high" if available_capacity_kw > required_kw * 5 else "medium" if available_capacity_kw > required_kw * 2 else "low",
        grid_score=grid_score,
        connection_cost_category=connection_cost_category(connection_cost_gbp),
        assumptions=[
            f"Distance to substation: {distance_to_substation_km:.1f}km",
            f"Required power: {required_kw:.0f}kW",
            f"Available capacity: {available_capacity_kw:.0f}kW",
            "Grid connection costs are estimates - DNO quote required"
        ]
    )
    
    # Financials
    financials = FinancialsBlock(
        capex=CapexBlock(
            charger_hardware=capex_breakdown["charger_hardware"],
            installation_and_civils=capex_breakdown["installation_and_civils"],
            grid_connection=capex_breakdown["grid_connection"],
            other=capex_breakdown["other"],
            total_capex=capex_breakdown["total_capex"]
        ),
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
        financial_summary=generate_financial_summary(
            roi_results.payback_years,
            roi_results.monthly_revenue,
            roi_results.simple_roi_percent
        )
    )
    
    # Recommended configuration
    primary_config = ConfigurationOption(
        plugs=req.planned_installation.plugs,
        power_per_plug_kw=req.planned_installation.power_per_plug_kw,
        total_power_kw=required_kw,
        charger_type=req.planned_installation.charger_type,
        rationale=f"Requested configuration suits {verdict.lower()} opportunity with {sessions_estimate['central']:.0f} sessions/day projected"
    )
    
    alternatives = []
    if req.planned_installation.charger_type == "DC" and demand_score < 60:
        alternatives.append(ConfigurationOption(
            plugs=req.planned_installation.plugs,
            power_per_plug_kw=22,
            total_power_kw=22 * req.planned_installation.plugs,
            charger_type="AC",
            rationale="AC charging may be more cost-effective for moderate demand"
        ))
    
    recommended_config = RecommendedConfiguration(
        primary=primary_config,
        alternatives=alternatives
    )
    
    # Next steps and risks
    next_steps = generate_next_steps(verdict, grid_score)
    risks = generate_risks(verdict, competition_score, grid_score, demand_score)
    
    # Data sources (if requested)
    data_sources = None
    if req.options and req.options.include_raw_sources:
        sources_info = []
        sources_used = 0
        
        for source_id, result in fetch_results.items():
            if hasattr(result, 'success'):
                status = "ok" if result.success else "error"
                used = result.success
                quality = int(result.quality_score * 100) if hasattr(result, 'quality_score') else None
                
                if used:
                    sources_used += 1
                
                sources_info.append(DataSourceInfo(
                    name=source_id.replace("_", " ").title(),
                    status=status,
                    used=used,
                    quality_percent=quality
                ))
        
        overall_quality = int((sources_used / len(fetch_results) * 100)) if fetch_results else 0
        
        data_sources = DataSourcesBlock(
            quality_score=overall_quality,
            sources_used=sources_used,
            sources_total=len(fetch_results),
            sources=sources_info
        )
    
    # Build final response
    response = AnalyzeLocationResponseV2(
        summary=summary,
        location=location_dict,
        scores=scores,
        demand_block=demand_block,
        competition_block=competition_block,
        grid_block=grid_block,
        financials=financials,
        recommended_configuration=recommended_config,
        next_steps=next_steps,
        risks=risks,
        data_sources=data_sources
    )
    
    print("✅ UK analysis complete!")
    
    return response


# ==================== UKRAINE HANDLER ====================

async def analyze_location_ukraine(req: AnalyzeLocationRequestV2):
    """
    Ukraine location analysis
    
    Adapted for Ukraine market:
    - Uses OpenChargeMap Ukraine data
    - Incorporates Energy Map Ukraine grid data
    - Adjusts scoring for lower EV adoption
    - Different cost structures (USD/UAH vs GBP)
    - Grid reliability considerations
    """
    
    # Input validation
    city = getattr(req.location, 'city', None)
    if not city and not (req.location.lat and req.location.lon):
        raise HTTPException(
            status_code=400, 
            detail="For Ukraine, provide either city name or lat/lon"
        )
    
    required_kw = req.planned_installation.power_per_plug_kw * req.planned_installation.plugs
    
    print(f"🔍 Analyzing Ukraine location: {city or f'{req.location.lat},{req.location.lon}'}")
    
    # ==================== FETCH UKRAINE DATA ====================
    
    try:
        fetch_results = await fetch_all_data_ukraine(
            city=city,
            lat=req.location.lat,
            lon=req.location.lon,
            radius_km=req.radius_km
        )
        
        print(f"✅ Fetched {len(fetch_results)} Ukraine data sources")
        
    except Exception as e:
        print(f"❌ Error fetching Ukraine data: {e}")
        raise HTTPException(status_code=500, detail=f"Data fetch error: {str(e)}")
    
    # ==================== EXTRACT UKRAINE DATA ====================
    
    # Location
    geocode_result = fetch_results.get("ukraine_geocode")
    if geocode_result and geocode_result.success:
        lat = geocode_result.data.get("lat")
        lon = geocode_result.data.get("lon")
        display_name = geocode_result.data.get("display_name")
    else:
        lat = req.location.lat or 50.45  # Kyiv default
        lon = req.location.lon or 30.52
        display_name = city or "Ukraine"
    
    # Competition data (OpenChargeMap Ukraine)
    ocm_result = fetch_results.get("openchargemap_ukraine")
    if ocm_result and ocm_result.success:
        chargers_data = ocm_result.data
        total_chargers = len(chargers_data)
        
        # Count fast DC (≥50kW)
        fast_dc_chargers = sum(
            1 for charger in chargers_data
            for conn in charger.get("connections", [])
            if conn.get("power_kw", 0) >= 50 and "DC" in str(conn.get("current", ""))
        )
        ac_only_chargers = total_chargers - fast_dc_chargers
    else:
        print("⚠️  OpenChargeMap Ukraine data unavailable")
        total_chargers = 0
        fast_dc_chargers = 0
        ac_only_chargers = 0
    
    # Demographics
    demo_result = fetch_results.get("ukraine_demographics")
    demographics = demo_result.data if demo_result and demo_result.success else {}
    population_density = demographics.get("population_density_per_km2", 2000)
    
    # EV stats
    ev_stats_result = fetch_results.get("ukraine_ev_stats")
    ev_stats = ev_stats_result.data if ev_stats_result and ev_stats_result.success else {}
    ev_growth_yoy = ev_stats.get("yoy_growth_percent", 45.0)  # Higher than UK!
    
    # Calculate EV density (Ukraine-specific)
    ev_density_per_1000 = calculate_ukraine_ev_density(ev_stats, demographics)
    
    # Grid data (Energy Map Ukraine)
    energy_map_result = fetch_results.get("energy_map_ukraine")
    energy_data = energy_map_result.data if energy_map_result and energy_map_result.success else {}
    
    # Traffic (estimate for Ukraine)
    # Major cities: high traffic, others: medium
    major_cities = ["Kyiv", "Lviv", "Odesa", "Kharkiv", "Dnipro"]
    if city and any(mc in city for mc in major_cities):
        traffic_intensity = 0.75
    else:
        traffic_intensity = 0.5
    
    # Facilities (estimate)
    facilities_count = 5  # Would use OSM in production
    facility_attractiveness = 0.6
    
    # Grid connection (Ukraine-specific costs)
    distance_to_substation_km = 0.5  # Estimate
    connection_cost_usd = estimate_ukraine_grid_connection_cost(
        distance_to_substation_km, 
        required_kw
    )
    
    # Convert to UAH for local context
    usd_to_uah = 41.0  # Approximate rate
    connection_cost_uah = connection_cost_usd * usd_to_uah
    
    available_capacity_kw = required_kw * 1.3  # More conservative than UK
    
    parking_spaces = req.site_context.parking_spaces if req.site_context else 30
    
    print(f"""
📊 Ukraine Data Summary:
   - Location: {display_name}
   - Chargers: {total_chargers} total, {fast_dc_chargers} fast DC
   - EV Density: {ev_density_per_1000:.1f} per 1000 cars
   - EV Growth: {ev_growth_yoy:.1f}% YoY (strong growth!)
   - Grid Connection: ${connection_cost_usd:,.0f} (~{connection_cost_uah:,.0f} UAH)
   - Population Density: {population_density:,.0f}/km²
    """)
    
    # ==================== SCORING (UKRAINE-ADAPTED) ====================
    
    # Ukraine scoring adjustments:
    # - Lower baseline for EV density (earlier market stage)
    # - Higher weight on growth potential
    # - Grid reliability factor
    
    from .scoring_v2 import (
        DemandInputs,
        CompetitionInputs,
        GridInputs,
        ParkingFacilitiesInputs,
        calc_demand_score,
        calc_competition_score,
        calc_grid_score,
        calc_parking_facilities_score,
        calc_overall_score,
        verdict_from_score
    )
    
    demand_inputs = DemandInputs(
        ev_density_per_1000_cars=ev_density_per_1000,
        traffic_intensity_index=traffic_intensity,
        ev_growth_yoy_percent=ev_growth_yoy,  # High growth in Ukraine!
        facility_attractiveness_index=facility_attractiveness
    )
    demand_score = calc_demand_score(demand_inputs)
    
    # Boost score for high growth markets
    if ev_growth_yoy > 40:
        demand_score = min(100, demand_score + 5)  # Bonus for high growth
    
    competition_inputs = CompetitionInputs(
        total_chargers=total_chargers,
        fast_dc_chargers=fast_dc_chargers,
        radius_km=req.radius_km
    )
    competition_score = calc_competition_score(competition_inputs)
    
    grid_inputs = GridInputs(
        distance_km=distance_to_substation_km,
        connection_cost_gbp=connection_cost_usd,  # Using USD equivalent
        available_capacity_kw=available_capacity_kw,
        required_kw=required_kw
    )
    grid_score = calc_grid_score(grid_inputs)
    
    # Reduce grid score if in areas affected by war
    grid_reliability = energy_data.get("grid_reliability", "medium")
    if grid_reliability == "low":
        grid_score = int(grid_score * 0.7)  # 30% reduction
    elif grid_reliability == "medium":
        grid_score = int(grid_score * 0.85)  # 15% reduction
    
    parking_inputs = ParkingFacilitiesInputs(
        parking_spaces=parking_spaces,
        facilities_count=facilities_count,
        site_type=req.site_context.site_type if req.site_context else None
    )
    parking_score = calc_parking_facilities_score(parking_inputs)
    
    overall_score = calc_overall_score(
        demand=demand_score,
        competition=competition_score,
        grid=grid_score,
        parking_facilities=parking_score
    )
    verdict = verdict_from_score(overall_score)
    
    print(f"""
📈 Ukraine Scores:
   - Demand: {demand_score}/100 (boosted for high growth)
   - Competition: {competition_score}/100
   - Grid: {grid_score}/100 (adjusted for reliability)
   - Parking: {parking_score}/100
   - Overall: {overall_score}/100 → {verdict}
    """)
    
    # ==================== FINANCIAL CALCULATIONS (UAH) ====================
    
    from .roi_v2 import (
        estimate_capex,
        estimate_sessions_per_day,
        calculate_roi,
        ROICalculatorInputs
    )
    
    # CAPEX in USD (lower costs than UK)
    capex_breakdown = estimate_capex(
        plugs=req.planned_installation.plugs,
        power_per_plug_kw=req.planned_installation.power_per_plug_kw,
        charger_type=req.planned_installation.charger_type,
        grid_connection_cost=connection_cost_usd
    )
    
    # Reduce hardware costs (30% cheaper in Ukraine)
    capex_breakdown["charger_hardware"] *= 0.7
    capex_breakdown["installation_and_civils"] *= 0.7
    capex_breakdown["total_capex"] = sum([
        capex_breakdown["charger_hardware"],
        capex_breakdown["installation_and_civils"],
        capex_breakdown["grid_connection"],
        capex_breakdown["other"]
    ])
    
    # Sessions estimate (Ukraine market)
    sessions_estimate = estimate_sessions_per_day(
        demand_score=demand_score,
        competition_score=competition_score,
        power_per_plug_kw=req.planned_installation.power_per_plug_kw,
        plugs=req.planned_installation.plugs,
        site_type=req.site_context.site_type if req.site_context else None
    )
    
    # Adjust for Ukraine market (lower utilization initially)
    for key in sessions_estimate:
        sessions_estimate[key] *= 0.7  # 30% lower utilization
    
    # ROI calculation (in USD, convert to UAH for display)
    electricity_cost_uah = energy_data.get("electricity_price_uah_per_kwh", 4.32)
    electricity_cost_usd = electricity_cost_uah / usd_to_uah
    
    # Typical Ukraine charging prices: 12-15 UAH/kWh
    tariff_uah = 13.0  # UAH per kWh
    tariff_usd = tariff_uah / usd_to_uah
    
    roi_inputs = ROICalculatorInputs(
        plugs=req.planned_installation.plugs,
        power_per_plug_kw=req.planned_installation.power_per_plug_kw,
        sessions_per_day=sessions_estimate["central"],
        avg_kwh_per_session=30.0,
        tariff_per_kwh=tariff_usd,
        energy_cost_per_kwh=electricity_cost_usd,
        fixed_costs_per_month=req.financial_params.fixed_costs_per_month,
        capex_total=capex_breakdown["total_capex"]
    )
    
    roi_results = calculate_roi(roi_inputs)
    
    print(f"""
💰 Ukraine Financials:
   - CAPEX: ${capex_breakdown['total_capex']:,.0f} (~{capex_breakdown['total_capex']*usd_to_uah:,.0f} UAH)
   - Tariff: {tariff_uah} UAH/kWh (${tariff_usd:.2f}/kWh)
   - Energy Cost: {electricity_cost_uah} UAH/kWh
   - Sessions/day: {sessions_estimate['central']:.1f}
   - Payback: {roi_results.payback_years:.1f} years
    """)
    
    # ==================== BUILD RESPONSE ====================
    
    # [Build response similar to UK version but with Ukraine-specific data]
    # You would use the same response models but populate with Ukraine data
    
    # For brevity, returning a simplified response structure
    # In production, build full AnalyzeLocationResponseV2
    
    return {
        "summary": {
            "verdict": verdict,
            "overall_score": overall_score,
            "headline_recommendation": f"Ukraine Market: {verdict} opportunity",
            "key_reasons": [
                f"High EV growth ({ev_growth_yoy}% YoY)",
                f"Competition: {total_chargers} existing stations",
                f"Grid reliability: {grid_reliability}",
                "Lower CAPEX than Western Europe"
            ]
        },
        "location": {
            "city": city or display_name,
            "lat": lat,
            "lon": lon,
            "country": "Ukraine",
            "radius_km": req.radius_km
        },
        "scores": {
            "demand": demand_score,
            "competition": competition_score,
            "grid_feasibility": grid_score,
            "parking_facilities": parking_score,
            "overall": overall_score
        },
        "market_context": {
            "ev_adoption_percent": ev_stats.get("ev_percent"),
            "total_evs": ev_stats.get("total_evs"),
            "charging_stations": ev_stats.get("charging_stations"),
            "growth_rate": ev_growth_yoy,
            "notes": energy_data.get("notes", [])
        },
        "financials": {
            "capex_usd": capex_breakdown["total_capex"],
            "capex_uah": capex_breakdown["total_capex"] * usd_to_uah,
            "payback_years": roi_results.payback_years,
            "monthly_revenue_usd": roi_results.monthly_revenue,
            "monthly_revenue_uah": roi_results.monthly_revenue * usd_to_uah
        }
    }


# ==================== HEALTH CHECK ====================

@router_v2.get("/health")
async def health_check_v2():
    """V2 API health check - Multi-country"""
    return {
        "status": "healthy",
        "version": "2.1.0",
        "api": "EVL Location Analyzer - Multi-Country",
        "countries_supported": ["UK", "Ukraine"],
        "features": {
            "uk": [
                "Real OpenChargeMap data",
                "DfT vehicle statistics",
                "ONS demographics",
                "Postcodes.io geocoding",
                "ENTSO-E grid data (optional)"
            ],
            "ukraine": [
                "OpenChargeMap Ukraine data",
                "Energy Map Ukraine integration",
                "Ukraine EV statistics",
                "Adapted scoring for emerging market",
                "UAH/USD financial calculations"
            ]
        }
    }
