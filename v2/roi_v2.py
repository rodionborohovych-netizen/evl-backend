"""
EVL v2.0 - ROI Calculator
==========================

Financial projections and ROI calculations.
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class ROICalculatorInputs:
    """Inputs for ROI calculation"""
    # Installation
    plugs: int
    power_per_plug_kw: float
    
    # Usage projections
    sessions_per_day: float
    avg_kwh_per_session: float
    
    # Pricing
    tariff_per_kwh: float  # What you charge customers
    energy_cost_per_kwh: float  # What you pay for electricity
    
    # Costs
    fixed_costs_per_month: float  # Rent, maintenance, SIM, insurance, etc.
    capex_total: float  # Total upfront investment


@dataclass
class ROIResults:
    """ROI calculation results"""
    # Revenue
    daily_revenue: float
    monthly_revenue: float
    annual_revenue: float
    
    # Costs
    daily_energy_cost: float
    annual_energy_cost: float
    annual_fixed_costs: float
    annual_total_opex: float
    
    # Margins
    gross_margin_per_kwh: float
    daily_gross_margin: float
    monthly_gross_margin: float
    annual_gross_margin: float
    
    # Net profit
    annual_net_profit: float
    monthly_net_profit: float
    
    # ROI metrics
    payback_years: Optional[float]
    payback_months: Optional[int]
    simple_roi_percent: Optional[float]


def calculate_roi(inputs: ROICalculatorInputs) -> ROIResults:
    """
    Calculate complete ROI metrics
    
    Revenue formula:
    - Daily revenue = sessions/day × kWh/session × tariff
    - Monthly = daily × 30
    - Annual = monthly × 12
    
    Costs:
    - Energy cost = sessions × kWh × energy_cost
    - Fixed costs = monthly rent, maintenance, etc.
    
    Profit:
    - Gross margin = revenue - energy costs
    - Net profit = gross margin - fixed costs
    
    ROI:
    - Payback = CAPEX / annual_net_profit
    - Simple ROI% = (annual_net_profit / CAPEX) × 100
    """
    
    # Energy sold per day
    energy_per_day_kwh = inputs.sessions_per_day * inputs.avg_kwh_per_session
    
    # Revenue
    daily_revenue = energy_per_day_kwh * inputs.tariff_per_kwh
    monthly_revenue = daily_revenue * 30
    annual_revenue = monthly_revenue * 12
    
    # Energy costs
    daily_energy_cost = energy_per_day_kwh * inputs.energy_cost_per_kwh
    annual_energy_cost = daily_energy_cost * 365
    
    # Fixed costs
    annual_fixed_costs = inputs.fixed_costs_per_month * 12
    annual_total_opex = annual_energy_cost + annual_fixed_costs
    
    # Margins
    gross_margin_per_kwh = inputs.tariff_per_kwh - inputs.energy_cost_per_kwh
    daily_gross_margin = daily_revenue - daily_energy_cost
    monthly_gross_margin = daily_gross_margin * 30
    annual_gross_margin = monthly_gross_margin * 12
    
    # Net profit
    annual_net_profit = annual_gross_margin - annual_fixed_costs
    monthly_net_profit = annual_net_profit / 12
    
    # ROI metrics
    if annual_net_profit > 0:
        payback_years = inputs.capex_total / annual_net_profit
        payback_months = int(round(payback_years * 12))
        simple_roi_percent = (annual_net_profit / inputs.capex_total) * 100
    else:
        payback_years = None
        payback_months = None
        simple_roi_percent = None
    
    return ROIResults(
        daily_revenue=daily_revenue,
        monthly_revenue=monthly_revenue,
        annual_revenue=annual_revenue,
        daily_energy_cost=daily_energy_cost,
        annual_energy_cost=annual_energy_cost,
        annual_fixed_costs=annual_fixed_costs,
        annual_total_opex=annual_total_opex,
        gross_margin_per_kwh=gross_margin_per_kwh,
        daily_gross_margin=daily_gross_margin,
        monthly_gross_margin=monthly_gross_margin,
        annual_gross_margin=annual_gross_margin,
        annual_net_profit=annual_net_profit,
        monthly_net_profit=monthly_net_profit,
        payback_years=payback_years,
        payback_months=payback_months,
        simple_roi_percent=simple_roi_percent
    )


def estimate_capex(
    plugs: int,
    power_per_plug_kw: float,
    charger_type: str,
    grid_connection_cost: float = 10000.0
) -> dict:
    """
    Estimate CAPEX breakdown
    
    Hardware costs (rough estimates):
    - DC chargers: £30k-50k per 50 kW, £60k-100k per 150 kW
    - AC chargers: £500-2000 per 7-22 kW
    
    Installation:
    - Typically 15-25% of hardware cost
    
    Grid connection:
    - Varies widely: £2k-£100k+
    - Estimated separately
    """
    
    # Hardware cost estimation
    if charger_type == "DC":
        if power_per_plug_kw >= 150:
            hardware_per_plug = 80000  # £80k for 150 kW ultra-rapid
        elif power_per_plug_kw >= 100:
            hardware_per_plug = 50000  # £50k for 100 kW
        elif power_per_plug_kw >= 50:
            hardware_per_plug = 35000  # £35k for 50 kW
        else:
            hardware_per_plug = 25000  # £25k for lower-power DC
    else:  # AC
        if power_per_plug_kw >= 22:
            hardware_per_plug = 2000  # £2k for 22 kW AC
        elif power_per_plug_kw >= 11:
            hardware_per_plug = 1500  # £1.5k for 11 kW
        else:
            hardware_per_plug = 1000  # £1k for 7 kW
    
    charger_hardware = hardware_per_plug * plugs
    
    # Installation & civil works (20% of hardware)
    installation_and_civils = charger_hardware * 0.20
    
    # Grid connection (provided)
    grid_connection = grid_connection_cost
    
    # Other (5% contingency)
    other = (charger_hardware + installation_and_civils + grid_connection) * 0.05
    
    # Total
    total_capex = charger_hardware + installation_and_civils + grid_connection + other
    
    return {
        "charger_hardware": charger_hardware,
        "installation_and_civils": installation_and_civils,
        "grid_connection": grid_connection,
        "other": other,
        "total_capex": total_capex
    }


def estimate_sessions_per_day(
    demand_score: int,
    competition_score: int,
    power_per_plug_kw: float,
    plugs: int,
    site_type: Optional[str] = None
) -> dict:
    """
    Estimate charging sessions per day
    
    Factors:
    - Demand score (higher = more sessions)
    - Competition score (higher = fewer competitors)
    - Charger type (DC fast = shorter sessions, more turnover)
    - Site type (retail vs roadside vs logistics)
    
    Returns: {"low": X, "central": Y, "high": Z}
    """
    
    # Base sessions from demand score
    # 80+ demand = 15 sessions/day, 50 demand = 8 sessions, 20 demand = 3 sessions
    base_sessions = (demand_score / 100) * 15
    
    # Competition adjustment
    # High competition (low score) = fewer sessions
    competition_factor = 0.5 + (competition_score / 100) * 0.5  # 0.5 to 1.0
    
    # Charger type adjustment
    # DC fast chargers can serve more vehicles per day (shorter dwell time)
    if power_per_plug_kw >= 100:
        charger_factor = 1.3  # 30% more due to faster turnover
    elif power_per_plug_kw >= 50:
        charger_factor = 1.15
    else:
        charger_factor = 1.0
    
    # Site type adjustment
    site_factor = 1.0
    if site_type:
        if site_type in ["retail_park", "shopping_mall"]:
            site_factor = 1.2  # 20% more due to natural dwell time
        elif site_type in ["roadside", "motorway"]:
            site_factor = 1.3  # 30% more due to high through-traffic
        elif site_type == "logistics":
            site_factor = 1.1  # 10% more for fleet usage
    
    # Calculate central estimate
    central = base_sessions * competition_factor * charger_factor * site_factor
    
    # Adjust for number of plugs (diminishing returns)
    if plugs > 1:
        utilization_factor = 1 + (plugs - 1) * 0.3  # 30% additional per plug
        central = central * utilization_factor
    
    # Conservative and optimistic ranges
    low = central * 0.7  # 70% of central
    high = central * 1.4  # 140% of central
    
    return {
        "low": round(low, 1),
        "central": round(central, 1),
        "high": round(high, 1)
    }


def generate_financial_summary(
    payback_years: Optional[float],
    monthly_revenue: float,
    roi_percent: Optional[float]
) -> str:
    """Generate one-line financial summary"""
    if payback_years is None:
        return "⚠️ Project unlikely to be profitable under current assumptions"
    elif payback_years < 3:
        return f"💰 Excellent financials: {payback_years:.1f} year payback, £{monthly_revenue:,.0f}/month revenue"
    elif payback_years < 5:
        return f"✅ Good financials: {payback_years:.1f} year payback, £{monthly_revenue:,.0f}/month revenue"
    elif payback_years < 7:
        return f"📊 Moderate financials: {payback_years:.1f} year payback, £{monthly_revenue:,.0f}/month revenue"
    else:
        return f"⚠️ Long payback: {payback_years:.1f} years, £{monthly_revenue:,.0f}/month revenue"
