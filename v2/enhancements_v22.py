"""
EVL v2.2 Enhancements Module
============================

This module provides three major enhancements to the EVL system:
1. Competitive Gap Analysis - Identifies power level gaps and Blue Ocean opportunities
2. Confidence Assessment - Meta-evaluation of data quality and recommendation reliability
3. Enhanced Opportunities - Prioritized, actionable opportunities with risk assessments

Author: EVL Team
Version: 2.2.0
Date: November 2025
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class PowerLevel(str, Enum):
    """Standard EV charger power levels"""
    POWER_7KW = "7kW"
    POWER_22KW = "22kW"
    POWER_50KW = "50kW"
    POWER_150KW = "150kW+"


class OpportunityPriority(str, Enum):
    """Priority levels for opportunities"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CompetitivePowerBreakdown:
    """Breakdown of existing chargers by power level"""
    power_7kw: int
    power_22kw: int
    power_50kw: int
    power_150kw: int
    total_chargers: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "power_7kw": self.power_7kw,
            "power_22kw": self.power_22kw,
            "power_50kw": self.power_50kw,
            "power_150kw": self.power_150kw,
            "total_chargers": self.total_chargers
        }


@dataclass
class PowerLevelGap:
    """Represents a gap in charger power levels"""
    power_level: str
    current_count: int
    market_average: int
    gap_size: int
    gap_percentage: float
    opportunity_score: float  # 0-10
    reasoning: str
    is_blue_ocean: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "power_level": self.power_level,
            "current_count": self.current_count,
            "market_average": self.market_average,
            "gap_size": self.gap_size,
            "gap_percentage": round(self.gap_percentage, 2),
            "opportunity_score": round(self.opportunity_score, 2),
            "reasoning": self.reasoning,
            "is_blue_ocean": self.is_blue_ocean
        }


@dataclass
class ConfidenceAssessment:
    """Comprehensive confidence assessment"""
    overall_confidence: float  # 0-1
    data_quality_score: float  # 0-1
    sample_size_score: float  # 0-1
    source_reliability_score: float  # 0-1
    consistency_score: float  # 0-1
    reasoning: str
    caveats: List[str]
    strengths: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_confidence": round(self.overall_confidence, 2),
            "data_quality_score": round(self.data_quality_score, 2),
            "sample_size_score": round(self.sample_size_score, 2),
            "source_reliability_score": round(self.source_reliability_score, 2),
            "consistency_score": round(self.consistency_score, 2),
            "reasoning": self.reasoning,
            "caveats": self.caveats,
            "strengths": self.strengths
        }


@dataclass
class EnhancedOpportunity:
    """Enhanced opportunity with detailed actionability"""
    title: str
    description: str
    priority: str
    impact_score: float  # 0-10
    effort_score: float  # 0-10, higher = more effort
    roi_multiplier: float
    timeframe: str
    risk_level: str
    risk_factors: List[str]
    mitigation_strategies: List[str]
    success_metrics: List[str]
    next_steps: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "impact_score": round(self.impact_score, 2),
            "effort_score": round(self.effort_score, 2),
            "roi_multiplier": round(self.roi_multiplier, 2),
            "timeframe": self.timeframe,
            "risk_level": self.risk_level,
            "risk_factors": self.risk_factors,
            "mitigation_strategies": self.mitigation_strategies,
            "success_metrics": self.success_metrics,
            "next_steps": self.next_steps
        }


class CompetitiveGapAnalyzer:
    """Analyzes competitive gaps in charger power levels"""
    
    def __init__(self):
        # Market averages for different location types (chargers per 5km radius)
        self.market_averages = {
            "urban_high_density": {
                "7kW": 12,
                "22kW": 8,
                "50kW": 5,
                "150kW+": 3
            },
            "urban_medium_density": {
                "7kW": 8,
                "22kW": 5,
                "50kW": 3,
                "150kW+": 2
            },
            "suburban": {
                "7kW": 5,
                "22kW": 3,
                "50kW": 2,
                "150kW+": 1
            },
            "rural": {
                "7kW": 2,
                "22kW": 1,
                "50kW": 1,
                "150kW+": 0
            }
        }
    
    def analyze_gaps(
        self,
        power_breakdown: Dict[str, int],
        location_type: str = "urban_medium_density",
        ev_density: float = 0.0
    ) -> Dict[str, Any]:
        """
        Analyze gaps in charger power levels
        
        Args:
            power_breakdown: Dict with keys "7kW", "22kW", "50kW", "150kW+"
            location_type: Type of location for market comparison
            ev_density: EV adoption rate (0-1)
        
        Returns:
            Dict with gaps, blue ocean opportunities, and recommendations
        """
        # Get market averages for this location type
        averages = self.market_averages.get(
            location_type,
            self.market_averages["urban_medium_density"]
        )
        
        gaps = []
        blue_ocean_opportunities = []
        
        # Analyze each power level
        for power_level in ["7kW", "22kW", "50kW", "150kW+"]:
            current = power_breakdown.get(power_level, 0)
            market_avg = averages[power_level]
            
            # Calculate gap
            gap_size = market_avg - current
            gap_percentage = (gap_size / market_avg * 100) if market_avg > 0 else 0
            
            # Calculate opportunity score (0-10)
            # Higher score = bigger opportunity
            if gap_size <= 0:
                opportunity_score = 0
                reasoning = f"Market saturated at {power_level}. {current} chargers vs {market_avg} average."
            else:
                # Score based on gap size and EV density
                base_score = min(10, (gap_size / market_avg) * 10)
                ev_multiplier = 1 + (ev_density * 0.5)  # Up to 1.5x multiplier
                opportunity_score = min(10, base_score * ev_multiplier)
                
                reasoning = f"Gap of {gap_size} chargers at {power_level} vs market average. "
                reasoning += f"High demand potential with {ev_density*100:.1f}% EV adoption."
            
            # Determine if Blue Ocean (gap > 50% and opportunity score > 7)
            is_blue_ocean = gap_percentage > 50 and opportunity_score > 7
            
            gap = PowerLevelGap(
                power_level=power_level,
                current_count=current,
                market_average=market_avg,
                gap_size=gap_size,
                gap_percentage=gap_percentage,
                opportunity_score=opportunity_score,
                reasoning=reasoning,
                is_blue_ocean=is_blue_ocean
            )
            
            gaps.append(gap.to_dict())
            
            if is_blue_ocean:
                blue_ocean_opportunities.append({
                    "power_level": power_level,
                    "opportunity_score": round(opportunity_score, 2),
                    "description": f"Blue Ocean: {power_level} chargers are severely underserved. "
                                 f"Only {current} vs market average of {market_avg}. "
                                 f"First-mover advantage available."
                })
        
        # Generate summary
        total_gap = sum(g["gap_size"] for g in gaps if g["gap_size"] > 0)
        avg_opportunity = sum(g["opportunity_score"] for g in gaps) / len(gaps) if gaps else 0
        
        return {
            "power_breakdown": power_breakdown,
            "gaps": gaps,
            "blue_ocean_opportunities": blue_ocean_opportunities,
            "summary": {
                "total_gap_chargers": total_gap,
                "average_opportunity_score": round(avg_opportunity, 2),
                "blue_ocean_count": len(blue_ocean_opportunities),
                "location_type": location_type
            }
        }


class ConfidenceAssessor:
    """Assesses confidence in recommendations and data quality"""
    
    def assess_confidence(
        self,
        data_sources: Dict[str, Any],
        sample_sizes: Dict[str, int],
        analysis_results: Dict[str, Any]
    ) -> ConfidenceAssessment:
        """
        Assess overall confidence in the analysis
        
        Args:
            data_sources: Dict of data source qualities
            sample_sizes: Dict of sample sizes for each data point
            analysis_results: The complete analysis results
        
        Returns:
            ConfidenceAssessment object
        """
        # Calculate component scores
        data_quality_score = self._assess_data_quality(data_sources)
        sample_size_score = self._assess_sample_sizes(sample_sizes)
        source_reliability_score = self._assess_source_reliability(data_sources)
        consistency_score = self._assess_consistency(analysis_results)
        
        # Calculate overall confidence (weighted average)
        overall_confidence = (
            data_quality_score * 0.3 +
            sample_size_score * 0.2 +
            source_reliability_score * 0.3 +
            consistency_score * 0.2
        )
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            overall_confidence,
            data_quality_score,
            sample_size_score,
            source_reliability_score,
            consistency_score
        )
        
        # Identify caveats and strengths
        caveats = self._identify_caveats(
            data_quality_score,
            sample_size_score,
            source_reliability_score,
            consistency_score
        )
        
        strengths = self._identify_strengths(
            data_quality_score,
            sample_size_score,
            source_reliability_score,
            consistency_score
        )
        
        return ConfidenceAssessment(
            overall_confidence=overall_confidence,
            data_quality_score=data_quality_score,
            sample_size_score=sample_size_score,
            source_reliability_score=source_reliability_score,
            consistency_score=consistency_score,
            reasoning=reasoning,
            caveats=caveats,
            strengths=strengths
        )
    
    def _assess_data_quality(self, data_sources: Dict[str, Any]) -> float:
        """Assess quality of data sources"""
        if not data_sources:
            return 0.3
        
        quality_scores = []
        for source, quality in data_sources.items():
            if isinstance(quality, dict) and "quality_score" in quality:
                quality_scores.append(quality["quality_score"])
            elif isinstance(quality, (int, float)):
                quality_scores.append(quality)
        
        return sum(quality_scores) / len(quality_scores) if quality_scores else 0.5
    
    def _assess_sample_sizes(self, sample_sizes: Dict[str, int]) -> float:
        """Assess adequacy of sample sizes"""
        if not sample_sizes:
            return 0.4
        
        # Thresholds for different data types
        thresholds = {
            "chargers": 10,
            "traffic": 100,
            "ev_registrations": 50,
            "facilities": 5
        }
        
        scores = []
        for data_type, size in sample_sizes.items():
            threshold = thresholds.get(data_type, 20)
            score = min(1.0, size / threshold)
            scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def _assess_source_reliability(self, data_sources: Dict[str, Any]) -> float:
        """Assess reliability of data sources"""
        # Known reliable sources
        reliable_sources = {
            "OpenChargeMap": 0.85,
            "OpenStreetMap": 0.80,
            "ENTSO-E": 0.95,
            "National Grid": 0.95,
            "DfT": 0.90,
            "ONS": 0.90,
            "Google Places": 0.75
        }
        
        if not data_sources:
            return 0.7
        
        scores = []
        for source in data_sources.keys():
            score = reliable_sources.get(source, 0.6)
            scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.7
    
    def _assess_consistency(self, analysis_results: Dict[str, Any]) -> float:
        """Assess internal consistency of results"""
        # Check if scores and recommendations align
        try:
            overall_score = analysis_results.get("scores", {}).get("overall", 50)
            verdict = analysis_results.get("summary", {}).get("verdict", "neutral")
            
            # Check alignment
            if overall_score >= 70 and verdict in ["excellent", "good"]:
                consistency = 0.9
            elif overall_score >= 50 and verdict in ["good", "moderate"]:
                consistency = 0.85
            elif overall_score < 50 and verdict in ["poor", "risky"]:
                consistency = 0.9
            else:
                consistency = 0.6
            
            return consistency
        except:
            return 0.7
    
    def _generate_reasoning(
        self,
        overall: float,
        data_quality: float,
        sample_size: float,
        source_reliability: float,
        consistency: float
    ) -> str:
        """Generate human-readable confidence reasoning"""
        if overall >= 0.8:
            base = "High confidence in recommendations. "
        elif overall >= 0.6:
            base = "Moderate confidence in recommendations. "
        else:
            base = "Limited confidence in recommendations. "
        
        factors = []
        if data_quality >= 0.8:
            factors.append("strong data quality")
        elif data_quality < 0.5:
            factors.append("data quality concerns")
        
        if sample_size >= 0.7:
            factors.append("sufficient sample sizes")
        elif sample_size < 0.5:
            factors.append("limited sample sizes")
        
        if source_reliability >= 0.8:
            factors.append("highly reliable sources")
        elif source_reliability < 0.6:
            factors.append("mixed source reliability")
        
        if factors:
            base += "Based on " + ", ".join(factors) + "."
        
        return base
    
    def _identify_caveats(
        self,
        data_quality: float,
        sample_size: float,
        source_reliability: float,
        consistency: float
    ) -> List[str]:
        """Identify caveats in the analysis"""
        caveats = []
        
        if data_quality < 0.6:
            caveats.append("Data quality is below optimal levels")
        
        if sample_size < 0.5:
            caveats.append("Sample sizes are limited - results may not be representative")
        
        if source_reliability < 0.7:
            caveats.append("Some data sources have uncertain reliability")
        
        if consistency < 0.7:
            caveats.append("Internal inconsistencies detected in analysis")
        
        if not caveats:
            caveats.append("No significant caveats identified")
        
        return caveats
    
    def _identify_strengths(
        self,
        data_quality: float,
        sample_size: float,
        source_reliability: float,
        consistency: float
    ) -> List[str]:
        """Identify strengths in the analysis"""
        strengths = []
        
        if data_quality >= 0.8:
            strengths.append("High-quality data from authoritative sources")
        
        if sample_size >= 0.7:
            strengths.append("Robust sample sizes for statistical confidence")
        
        if source_reliability >= 0.8:
            strengths.append("Data from highly reliable government and industry sources")
        
        if consistency >= 0.8:
            strengths.append("Internally consistent analysis across all metrics")
        
        if not strengths:
            strengths.append("Analysis completed with available data")
        
        return strengths


class OpportunityEnhancer:
    """Enhances basic opportunities with risk, ROI, and actionability details"""
    
    def enhance_opportunities(
        self,
        basic_opportunities: List[str],
        scores: Dict[str, float],
        competitive_data: Dict[str, Any],
        financial_data: Dict[str, Any]
    ) -> List[EnhancedOpportunity]:
        """
        Enhance basic opportunity strings into detailed, actionable opportunities
        
        Args:
            basic_opportunities: List of opportunity strings
            scores: Analysis scores
            competitive_data: Competitive analysis data
            financial_data: Financial projections
        
        Returns:
            List of EnhancedOpportunity objects
        """
        enhanced = []
        
        for opp_text in basic_opportunities:
            # Parse opportunity type
            opp_lower = opp_text.lower()
            
            if "blue ocean" in opp_lower or "underserved" in opp_lower:
                enhanced.append(self._create_blue_ocean_opportunity(
                    opp_text, scores, competitive_data, financial_data
                ))
            elif "demand" in opp_lower or "high traffic" in opp_lower:
                enhanced.append(self._create_demand_opportunity(
                    opp_text, scores, competitive_data, financial_data
                ))
            elif "upgrade" in opp_lower or "modernize" in opp_lower:
                enhanced.append(self._create_upgrade_opportunity(
                    opp_text, scores, competitive_data, financial_data
                ))
            else:
                enhanced.append(self._create_generic_opportunity(
                    opp_text, scores, competitive_data, financial_data
                ))
        
        # Sort by priority
        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3
        }
        enhanced.sort(key=lambda x: priority_order.get(x.priority, 4))
        
        return enhanced
    
    def _create_blue_ocean_opportunity(
        self,
        opp_text: str,
        scores: Dict[str, float],
        competitive_data: Dict[str, Any],
        financial_data: Dict[str, Any]
    ) -> EnhancedOpportunity:
        """Create enhanced Blue Ocean opportunity"""
        return EnhancedOpportunity(
            title="Blue Ocean Market Entry",
            description=opp_text,
            priority="high",
            impact_score=9.0,
            effort_score=7.0,
            roi_multiplier=2.5,
            timeframe="12-18 months",
            risk_level="medium",
            risk_factors=[
                "First-mover risk - market may be unproven",
                "Higher initial marketing costs to establish presence",
                "Potential for rapid competitive response"
            ],
            mitigation_strategies=[
                "Start with pilot phase (2-4 chargers) to test market",
                "Secure long-term site agreements before competitors",
                "Build strong local partnerships early"
            ],
            success_metrics=[
                "Market share >30% within 12 months",
                "Utilization rate >40% within 6 months",
                "Customer satisfaction >4.5/5 stars"
            ],
            next_steps=[
                "Conduct detailed site survey and feasibility study",
                "Secure grid connection approval",
                "Develop marketing and community engagement plan",
                "Negotiate site lease with property owner"
            ]
        )
    
    def _create_demand_opportunity(
        self,
        opp_text: str,
        scores: Dict[str, float],
        competitive_data: Dict[str, Any],
        financial_data: Dict[str, Any]
    ) -> EnhancedOpportunity:
        """Create enhanced demand-driven opportunity"""
        demand_score = scores.get("demand", 50)
        
        return EnhancedOpportunity(
            title="High-Demand Location Capture",
            description=opp_text,
            priority="high" if demand_score >= 70 else "medium",
            impact_score=8.5,
            effort_score=5.0,
            roi_multiplier=2.0,
            timeframe="6-12 months",
            risk_level="low",
            risk_factors=[
                "Competitive market may have thin margins",
                "High utilization may require maintenance capacity"
            ],
            mitigation_strategies=[
                "Deploy reliable, low-maintenance equipment",
                "Establish 24/7 monitoring and support",
                "Competitive pricing strategy to capture market share"
            ],
            success_metrics=[
                "Utilization rate >60% within 3 months",
                "Revenue per charger >£1,500/month",
                "Equipment uptime >95%"
            ],
            next_steps=[
                "Fast-track grid connection application",
                "Select high-reliability charger models",
                "Develop aggressive launch promotion",
                "Establish maintenance partnership"
            ]
        )
    
    def _create_upgrade_opportunity(
        self,
        opp_text: str,
        scores: Dict[str, float],
        competitive_data: Dict[str, Any],
        financial_data: Dict[str, Any]
    ) -> EnhancedOpportunity:
        """Create enhanced infrastructure upgrade opportunity"""
        return EnhancedOpportunity(
            title="Infrastructure Modernization",
            description=opp_text,
            priority="medium",
            impact_score=7.0,
            effort_score=6.0,
            roi_multiplier=1.5,
            timeframe="9-15 months",
            risk_level="medium",
            risk_factors=[
                "Disruption during upgrade period",
                "Higher upfront capital requirement",
                "Technology obsolescence risk"
            ],
            mitigation_strategies=[
                "Phase upgrades to minimize downtime",
                "Choose modular, upgradeable systems",
                "Negotiate favorable financing terms"
            ],
            success_metrics=[
                "Reduced cost per kWh by 15%",
                "Increased utilization by 25%",
                "Customer satisfaction improvement"
            ],
            next_steps=[
                "Audit existing infrastructure",
                "Obtain upgrade quotes from suppliers",
                "Model ROI vs. new site development",
                "Plan phased implementation"
            ]
        )
    
    def _create_generic_opportunity(
        self,
        opp_text: str,
        scores: Dict[str, float],
        competitive_data: Dict[str, Any],
        financial_data: Dict[str, Any]
    ) -> EnhancedOpportunity:
        """Create generic enhanced opportunity"""
        overall_score = scores.get("overall", 50)
        
        return EnhancedOpportunity(
            title="Market Opportunity",
            description=opp_text,
            priority="medium" if overall_score >= 60 else "low",
            impact_score=6.0,
            effort_score=5.0,
            roi_multiplier=1.3,
            timeframe="12-24 months",
            risk_level="medium",
            risk_factors=[
                "Market conditions may change",
                "Competitive landscape uncertain"
            ],
            mitigation_strategies=[
                "Conduct thorough market research",
                "Develop flexible deployment strategy",
                "Monitor competitive activity"
            ],
            success_metrics=[
                "Positive ROI within 36 months",
                "Market presence established",
                "Operational efficiency targets met"
            ],
            next_steps=[
                "Detailed feasibility analysis",
                "Stakeholder engagement",
                "Financial modeling",
                "Risk assessment"
            ]
        )


# Convenience functions for easy integration

def analyze_competitive_gaps(
    power_breakdown: Dict[str, int],
    location_type: str = "urban_medium_density",
    ev_density: float = 0.0
) -> Dict[str, Any]:
    """Convenience function for gap analysis"""
    analyzer = CompetitiveGapAnalyzer()
    return analyzer.analyze_gaps(power_breakdown, location_type, ev_density)


def assess_confidence(
    data_sources: Dict[str, Any],
    sample_sizes: Dict[str, int],
    analysis_results: Dict[str, Any]
) -> Dict[str, Any]:
    """Convenience function for confidence assessment"""
    assessor = ConfidenceAssessor()
    assessment = assessor.assess_confidence(data_sources, sample_sizes, analysis_results)
    return assessment.to_dict()


def enhance_opportunities(
    basic_opportunities: List[str],
    scores: Dict[str, float],
    competitive_data: Dict[str, Any],
    financial_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Convenience function for opportunity enhancement"""
    enhancer = OpportunityEnhancer()
    enhanced = enhancer.enhance_opportunities(
        basic_opportunities,
        scores,
        competitive_data,
        financial_data
    )
    return [opp.to_dict() for opp in enhanced]
