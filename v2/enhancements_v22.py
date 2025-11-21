"""
EVL v2.2 - Enhanced Features Extension
=======================================

Adds v11-style features to existing v2 API:
- Competitive gap analysis (power level breakdown)
- Confidence scoring (meta-score on data quality)
- Location comparison endpoint
- Opportunity highlighting

Works with existing v2 models and doesn't break backward compatibility.
"""

from typing import List, Dict, Any, Literal, Optional
from pydantic import BaseModel, Field


# ==================== NEW MODELS FOR v2.2 ====================

class PowerLevelGap(BaseModel):
    """Gap analysis for a specific power category"""
    category: Literal["AC_Slow", "AC_Fast", "DC_Rapid", "DC_Ultra"] = Field(
        ..., description="Power category"
    )
    power_range: str = Field(..., description="Power range (e.g., '0-7 kW')")
    count: int = Field(..., description="Number of chargers in this category")
    percentage: float = Field(..., description="% of total chargers")
    market_status: Literal["Blue Ocean", "Opportunity", "Competitive", "Saturated"] = Field(
        ..., description="Market saturation level"
    )
    recommendation: str = Field(..., description="Actionable insight")


class CompetitiveGapsAnalysis(BaseModel):
    """Detailed competitive gap analysis"""
    power_gaps: List[PowerLevelGap] = Field(..., description="Breakdown by power level")
    best_opportunity: str = Field(..., description="Top opportunity identified")
    market_positioning: str = Field(..., description="Overall market positioning advice")


class ConfidenceFactors(BaseModel):
    """Factors contributing to confidence score"""
    data_completeness: int = Field(..., description="Score 0-100 for data availability")
    data_quality: int = Field(..., description="Score 0-100 for data quality")
    source_reliability: int = Field(..., description="Score 0-100 for source health")
    market_clarity: int = Field(..., description="Score 0-100 for market understanding")


class ConfidenceAssessment(BaseModel):
    """Overall confidence in recommendations"""
    level: Literal["Very High", "High", "Medium", "Low"] = Field(
        ..., description="Confidence level"
    )
    score: int = Field(..., description="Overall confidence 0-100")
    factors: ConfidenceFactors = Field(..., description="Contributing factors")
    reasoning: List[str] = Field(..., description="Why this confidence level")
    caveats: List[str] = Field(..., description="Important caveats to consider")


class OpportunityHighlight(BaseModel):
    """Individual opportunity highlight"""
    type: Literal["market_gap", "low_competition", "strategic_location", "partnership", "other"]
    priority: Literal["critical", "high", "medium", "low"]
    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed explanation")
    potential_impact: str = Field(..., description="Expected impact if pursued")


class EnhancedOpportunities(BaseModel):
    """Enhanced opportunity analysis"""
    highlights: List[OpportunityHighlight] = Field(..., description="Top opportunities")
    total_opportunities: int = Field(..., description="Total opportunities identified")
    critical_count: int = Field(..., description="Number of critical opportunities")


# ==================== ENHANCEMENT FUNCTIONS ====================

def analyze_competitive_gaps(
    chargers_data: List[Dict],
    total_chargers: int,
    fast_dc_count: int
) -> CompetitiveGapsAnalysis:
    """
    Analyze competitive gaps by power level
    
    Categories:
    - AC_Slow: 0-7 kW
    - AC_Fast: 7-22 kW
    - DC_Rapid: 50-150 kW
    - DC_Ultra: 150+ kW
    """
    
    # Count by category
    categories = {
        "AC_Slow": {"count": 0, "range": "0-7 kW"},
        "AC_Fast": {"count": 0, "range": "7-22 kW"},
        "DC_Rapid": {"count": 0, "range": "50-150 kW"},
        "DC_Ultra": {"count": 0, "range": "150+ kW"}
    }
    
    # Categorize existing chargers (if detailed data available)
    for charger in chargers_data:
        power_kw = charger.get('power_kw', 0)
        if power_kw < 7:
            categories["AC_Slow"]["count"] += 1
        elif power_kw < 22:
            categories["AC_Fast"]["count"] += 1
        elif power_kw < 150:
            categories["DC_Rapid"]["count"] += 1
        else:
            categories["DC_Ultra"]["count"] += 1
    
    # Calculate market status
    power_gaps = []
    blue_oceans = []
    opportunities = []
    
    for cat_name, cat_data in categories.items():
        count = cat_data["count"]
        percentage = (count / total_chargers * 100) if total_chargers > 0 else 0
        
        # Determine market status
        if count == 0:
            status = "Blue Ocean"
            blue_oceans.append(cat_name)
            recommendation = f"⭐⭐ First-mover advantage - no {cat_name.replace('_', ' ')} chargers in area"
        elif count <= 2:
            status = "Opportunity"
            opportunities.append(cat_name)
            recommendation = f"⭐ Good opportunity - only {count} {cat_name.replace('_', ' ')} chargers"
        elif count <= 5:
            status = "Competitive"
            recommendation = f"Viable but competitive - {count} existing {cat_name.replace('_', ' ')} chargers"
        else:
            status = "Saturated"
            recommendation = f"⚠️ High competition - {count} {cat_name.replace('_', ' ')} chargers already present"
        
        power_gaps.append(PowerLevelGap(
            category=cat_name,
            power_range=cat_data["range"],
            count=count,
            percentage=round(percentage, 1),
            market_status=status,
            recommendation=recommendation
        ))
    
    # Determine best opportunity
    if blue_oceans:
        best_opportunity = f"Blue Ocean in {', '.join(blue_oceans)} - strong first-mover advantage"
    elif opportunities:
        best_opportunity = f"Opportunity in {', '.join(opportunities)} - limited competition"
    else:
        best_opportunity = "Saturated market - differentiation through service quality recommended"
    
    # Market positioning advice
    if blue_oceans:
        positioning = "Focus on blue ocean categories to establish market presence without direct competition"
    elif opportunities:
        positioning = "Target opportunity categories with strategic pricing and superior service"
    else:
        positioning = "Highly competitive market - differentiate through location, reliability, and customer service"
    
    return CompetitiveGapsAnalysis(
        power_gaps=power_gaps,
        best_opportunity=best_opportunity,
        market_positioning=positioning
    )


def assess_confidence(
    data_sources: Dict[str, Any],
    scores: Dict[str, int],
    total_chargers: int,
    has_grid_data: bool
) -> ConfidenceAssessment:
    """
    Assess confidence in recommendations based on data quality
    
    Factors:
    1. Data completeness (25 points) - how many sources succeeded
    2. Data quality (35 points) - quality scores from sources
    3. Source reliability (20 points) - response times and consistency
    4. Market clarity (20 points) - how clear the competitive landscape is
    """
    
    # 1. Data completeness
    sources_used = data_sources.get('sources_used', 0)
    sources_total = data_sources.get('sources_total', 1)
    completeness_score = int((sources_used / sources_total) * 25)
    
    # 2. Data quality
    quality_percent = data_sources.get('quality_score', 0)
    quality_score = int((quality_percent / 100) * 35)
    
    # 3. Source reliability (based on response times and errors)
    sources = data_sources.get('sources', [])
    ok_sources = sum(1 for s in sources if s.get('status') == 'ok')
    reliability_score = int((ok_sources / len(sources) * 20)) if sources else 10
    
    # 4. Market clarity
    # More chargers = better understanding of competition
    if total_chargers >= 10:
        market_clarity_score = 20
    elif total_chargers >= 5:
        market_clarity_score = 15
    elif total_chargers >= 1:
        market_clarity_score = 10
    else:
        market_clarity_score = 5
    
    # Grid data adds confidence
    if has_grid_data:
        market_clarity_score = min(20, market_clarity_score + 5)
    
    # Total confidence score
    total_score = (
        completeness_score +
        quality_score +
        reliability_score +
        market_clarity_score
    )
    
    # Determine level
    if total_score >= 80:
        level = "Very High"
    elif total_score >= 65:
        level = "High"
    elif total_score >= 45:
        level = "Medium"
    else:
        level = "Low"
    
    # Generate reasoning
    reasoning = []
    if completeness_score >= 20:
        reasoning.append(f"Excellent data completeness ({sources_used}/{sources_total} sources)")
    elif completeness_score >= 15:
        reasoning.append(f"Good data coverage ({sources_used}/{sources_total} sources)")
    else:
        reasoning.append(f"⚠️ Limited data coverage ({sources_used}/{sources_total} sources)")
    
    if quality_score >= 28:
        reasoning.append(f"High quality data ({quality_percent}% quality score)")
    elif quality_score < 20:
        reasoning.append(f"⚠️ Data quality could be better ({quality_percent}%)")
    
    if market_clarity_score >= 15:
        reasoning.append(f"Clear competitive landscape ({total_chargers} chargers analyzed)")
    else:
        reasoning.append(f"⚠️ Limited competitive intelligence (only {total_chargers} chargers found)")
    
    # Generate caveats
    caveats = []
    if level in ["Low", "Medium"]:
        caveats.append("Additional on-site verification recommended")
    
    if not has_grid_data:
        caveats.append("Grid capacity should be confirmed with DNO/DSO")
    
    if total_chargers == 0:
        caveats.append("No existing chargers found - market demand uncertain")
    
    caveats.append("Market conditions can change - monitor competition regularly")
    
    if sources_used < sources_total:
        caveats.append(f"{sources_total - sources_used} data source(s) unavailable - some insights may be incomplete")
    
    return ConfidenceAssessment(
        level=level,
        score=total_score,
        factors=ConfidenceFactors(
            data_completeness=completeness_score,
            data_quality=quality_score,
            source_reliability=reliability_score,
            market_clarity=market_clarity_score
        ),
        reasoning=reasoning,
        caveats=caveats
    )


def identify_enhanced_opportunities(
    competitive_gaps: CompetitiveGapsAnalysis,
    scores: Dict[str, int],
    competition_block: Dict[str, Any],
    grid_block: Dict[str, Any],
    demand_block: Dict[str, Any]
) -> EnhancedOpportunities:
    """
    Identify and prioritize opportunities
    
    Types:
    - Market gaps (blue ocean categories)
    - Low competition
    - Strategic location (high traffic, good grid)
    - Partnership potential (nearby facilities)
    """
    
    highlights = []
    
    # 1. Check for blue ocean opportunities
    blue_oceans = [g for g in competitive_gaps.power_gaps if g.market_status == "Blue Ocean"]
    for gap in blue_oceans:
        highlights.append(OpportunityHighlight(
            type="market_gap",
            priority="critical",
            title=f"Blue Ocean: {gap.category.replace('_', ' ')}",
            description=f"No existing {gap.category.replace('_', ' ')} chargers in area. Strong first-mover advantage.",
            potential_impact="High - establish market presence without direct competition"
        ))
    
    # 2. Low competition opportunities
    total_stations = competition_block.get('total_stations', 0)
    if total_stations < 5 and scores.get('demand', 0) >= 60:
        highlights.append(OpportunityHighlight(
            type="low_competition",
            priority="high" if total_stations < 3 else "medium",
            title=f"Low Competition ({total_stations} total chargers)",
            description="Few existing chargers despite good demand indicators. Room for market entry.",
            potential_impact="Medium-High - capture early market share"
        ))
    
    # 3. Strategic location
    if scores.get('grid_feasibility', 0) >= 70 and scores.get('demand', 0) >= 65:
        highlights.append(OpportunityHighlight(
            type="strategic_location",
            priority="high",
            title="Strategic Location",
            description="Excellent combination of grid access and market demand.",
            potential_impact="High - favorable conditions for rapid deployment"
        ))
    
    # 4. Partnership opportunities
    sessions_per_day = demand_block.get('estimated_sessions_per_day', {})
    if sessions_per_day.get('central', 0) >= 10:
        highlights.append(OpportunityHighlight(
            type="partnership",
            priority="medium",
            title="Partnership Potential",
            description=f"High projected demand ({sessions_per_day.get('central')} sessions/day) suitable for facility partnerships.",
            potential_impact="Medium - shared investment and cross-promotion opportunities"
        ))
    
    # 5. Growth market
    ev_growth = demand_block.get('ev_growth_yoy_percent', 0)
    if ev_growth and ev_growth >= 30:
        highlights.append(OpportunityHighlight(
            type="other",
            priority="medium",
            title="Rapid Market Growth",
            description=f"EV growth at {ev_growth:.0f}% YoY - expanding market opportunity.",
            potential_impact="Medium-High - early mover advantage in growing market"
        ))
    
    # Count by priority
    critical_count = sum(1 for h in highlights if h.priority == "critical")
    
    return EnhancedOpportunities(
        highlights=highlights,
        total_opportunities=len(highlights),
        critical_count=critical_count
    )


# ==================== COMPARISON LOGIC ====================

def compare_locations(
    analysis1: Dict[str, Any],
    analysis2: Dict[str, Any],
    location1_name: str,
    location2_name: str
) -> Dict[str, Any]:
    """
    Compare two location analyses side by side
    
    Returns comparison with winner and detailed breakdown
    """
    
    # Extract key metrics
    score1 = analysis1['scores']['overall']
    score2 = analysis2['scores']['overall']
    
    confidence1 = analysis1.get('confidence_assessment', {}).get('score', 50)
    confidence2 = analysis2.get('confidence_assessment', {}).get('score', 50)
    
    competition1 = analysis1['competition_block']['total_stations']
    competition2 = analysis2['competition_block']['total_stations']
    
    opportunities1 = analysis1.get('enhanced_opportunities', {}).get('total_opportunities', 0)
    opportunities2 = analysis2.get('enhanced_opportunities', {}).get('total_opportunities', 0)
    
    roi1 = analysis1['financials']['roi'].get('payback_years')
    roi2 = analysis2['financials']['roi'].get('payback_years')
    
    # Determine winner
    # Weighted scoring: 40% overall score, 30% confidence, 20% opportunities, 10% competition
    weighted1 = (
        score1 * 0.4 +
        confidence1 * 0.3 +
        opportunities1 * 2 +  # Scale to 0-100 range
        (100 - min(competition1 * 5, 100)) * 0.1  # Lower competition = higher score
    )
    
    weighted2 = (
        score2 * 0.4 +
        confidence2 * 0.3 +
        opportunities2 * 2 +
        (100 - min(competition2 * 5, 100)) * 0.1
    )
    
    winner = location1_name if weighted1 > weighted2 else location2_name
    score_difference = abs(weighted1 - weighted2)
    
    # Generate reasoning
    reasoning = []
    
    # Score comparison
    if abs(score1 - score2) >= 10:
        better_score = location1_name if score1 > score2 else location2_name
        reasoning.append(f"{better_score}: Higher overall score ({max(score1, score2)} vs {min(score1, score2)})")
    
    # Confidence comparison
    if abs(confidence1 - confidence2) >= 15:
        better_conf = location1_name if confidence1 > confidence2 else location2_name
        reasoning.append(f"{better_conf}: Higher confidence in data ({max(confidence1, confidence2)} vs {min(confidence1, confidence2)})")
    
    # Competition comparison
    if abs(competition1 - competition2) >= 3:
        less_comp = location1_name if competition1 < competition2 else location2_name
        reasoning.append(f"{less_comp}: Lower competition ({min(competition1, competition2)} vs {max(competition1, competition2)} chargers)")
    
    # Opportunities comparison
    if abs(opportunities1 - opportunities2) >= 2:
        more_opp = location1_name if opportunities1 > opportunities2 else location2_name
        reasoning.append(f"{more_opp}: More opportunities identified ({max(opportunities1, opportunities2)} vs {min(opportunities1, opportunities2)})")
    
    # ROI comparison (if both available)
    if roi1 and roi2 and abs(roi1 - roi2) >= 1:
        better_roi = location1_name if roi1 < roi2 else location2_name
        reasoning.append(f"{better_roi}: Faster payback ({min(roi1, roi2):.1f} vs {max(roi1, roi2):.1f} years)")
    
    # Build comparison matrix
    matrix = {
        "overall_score": {
            location1_name: score1,
            location2_name: score2,
            "winner": location1_name if score1 > score2 else location2_name,
            "difference": abs(score1 - score2)
        },
        "confidence": {
            location1_name: confidence1,
            location2_name: confidence2,
            "winner": location1_name if confidence1 > confidence2 else location2_name
        },
        "competition": {
            location1_name: competition1,
            location2_name: competition2,
            "winner": location1_name if competition1 < competition2 else location2_name  # Lower is better
        },
        "opportunities": {
            location1_name: opportunities1,
            location2_name: opportunities2,
            "winner": location1_name if opportunities1 > opportunities2 else location2_name
        }
    }
    
    if roi1 and roi2:
        matrix["payback_years"] = {
            location1_name: roi1,
            location2_name: roi2,
            "winner": location1_name if roi1 < roi2 else location2_name  # Lower is better
        }
    
    return {
        "winner": {
            "location": winner,
            "weighted_score": max(weighted1, weighted2),
            "score_difference": score_difference,
            "reasoning": reasoning
        },
        "comparison_matrix": matrix,
        "recommendation": (
            f"**{winner}** is the recommended location with {score_difference:.1f} point advantage. "
            f"{'Strong' if score_difference >= 15 else 'Moderate' if score_difference >= 8 else 'Marginal'} preference."
        )
    }


__all__ = [
    "PowerLevelGap",
    "CompetitiveGapsAnalysis",
    "ConfidenceFactors",
    "ConfidenceAssessment",
    "OpportunityHighlight",
    "EnhancedOpportunities",
    "analyze_competitive_gaps",
    "assess_confidence",
    "identify_enhanced_opportunities",
    "compare_locations",
]
