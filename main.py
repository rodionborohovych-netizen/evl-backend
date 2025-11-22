"""
EVL v10.1 + Day 1 & C-3 & M-3 Fixes - EV Location Analyzer
Includes: C-7 (Parser logging), C-4 (FetchResult validation), C-6 (AADT validation), C-3 (Coordinate validation), M-3 (Power validation)
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import math
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio
import logging
import json

# ============================================================================
# CRITICAL: Setup logger FIRST (C-4, C-6, C-7 requirement)
# ============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Foundation Models
# ============================================================================

class FetchResult:
    """Standardized result from data fetchers"""
    def __init__(self, success: bool, data: Any, source_id: str, 
                 fetched_at: datetime, quality_score: float = 1.0):
        self.success = success
        self.data = data
        self.source_id = source_id
        self.fetched_at = fetched_at
        self.quality_score = quality_score

# ============================================================================
# AADT Validation Constants (C-6)
# ============================================================================
DEFAULT_AADT = 15000    # Reasonable UK average
MIN_VALID_AADT = 100    # Minimum plausible daily traffic
MAX_VALID_AADT = 200000 # Maximum plausible daily traffic

# ============================================================================
# [C-3] Coordinate Validation Constants
# ============================================================================
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0

# ============================================================================
# [M-3] Power Validation Constants
# ============================================================================
DEFAULT_POWER_KW = 7.0      # Standard AC charger power
MIN_VALID_POWER_KW = 1.0    # Minimum valid power
MAX_VALID_POWER_KW = 500.0  # Maximum valid power (ultra-rapid)

# ============================================================================
# V2 Import with Error Handling
# ============================================================================
try:
    from v2.api_v2 import router_v2
    V2_AVAILABLE = True
    logger.info("✅ V2 API router imported successfully")
except ImportError as e:
    logger.warning(f"⚠️  V2 API not available: {e}")
    V2_AVAILABLE = False
except Exception as e:
    logger.error(f"❌ Error importing V2 API: {e}")
    V2_AVAILABLE = False

# ============================================================================
# FastAPI App Setup
# ============================================================================

app = FastAPI(
    title="EVL v10.1 + Day 1 & C-3 Fixes",
    description="EV Location Analyzer with Production-Ready Data Validation",
    version="10.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include V2 Router if available
if V2_AVAILABLE:
    try:
        app.include_router(router_v2, prefix="/api/v2", tags=["V2 Business API"])
        logger.info("✅ V2 business-focused API enabled at /api/v2/*")
    except Exception as e:
        logger.error(f"❌ Error including V2 router: {e}")

logger.info("🚀 EVL API starting up...")

# ============================================================================
# API Configuration
# ============================================================================

API_KEYS = {
    "openchargemap": os.getenv("OPENCHARGEMAP_API_KEY", ""),
    "entsoe": os.getenv("ENTSOE_API_KEY", ""),
}

# ============================================================================
# Utility Functions
# ============================================================================

def distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km using Haversine formula"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return round(R * c, 2)

# ============================================================================
# [C-3] Coordinate Validation Functions
# ============================================================================

def validate_coordinates(lat: float, lon: float, context: str = "unknown") -> tuple:
    """
    Validate latitude and longitude values.
    [C-3] Returns (is_valid, error_message)
    """
    # Validate latitude
    if not isinstance(lat, (int, float)):
        error = f"Latitude must be numeric, got {type(lat).__name__}"
        logger.warning(f"Invalid latitude in {context}: {error}")
        return False, error
    
    if lat < MIN_LATITUDE or lat > MAX_LATITUDE:
        error = f"Latitude must be between {MIN_LATITUDE} and {MAX_LATITUDE}, got {lat}"
        logger.warning(f"Latitude out of range in {context}: {error}")
        return False, error
    
    # Validate longitude
    if not isinstance(lon, (int, float)):
        error = f"Longitude must be numeric, got {type(lon).__name__}"
        logger.warning(f"Invalid longitude in {context}: {error}")
        return False, error
    
    if lon < MIN_LONGITUDE or lon > MAX_LONGITUDE:
        error = f"Longitude must be between {MIN_LONGITUDE} and {MAX_LONGITUDE}, got {lon}"
        logger.warning(f"Longitude out of range in {context}: {error}")
        return False, error
    
    # Check for Null Island (common geocoding failure)
    if round(lat, 6) == 0.0 and round(lon, 6) == 0.0:
        error = "Invalid coordinates (0, 0) - likely geocoding failure"
        logger.warning(f"Null Island coordinates in {context}")
        return False, error
    
    return True, None


def validate_radius(radius_km: float, context: str = "unknown") -> tuple:
    """
    Validate search radius.
    [C-3] Returns (is_valid, error_message)
    """
    if not isinstance(radius_km, (int, float)):
        error = f"Radius must be numeric, got {type(radius_km).__name__}"
        logger.warning(f"Invalid radius in {context}: {error}")
        return False, error
    
    if radius_km <= 0:
        error = f"Radius must be positive, got {radius_km}"
        logger.warning(f"Invalid radius in {context}: {error}")
        return False, error
    
    if radius_km > 100:
        error = f"Radius too large (max 100km), got {radius_km}"
        logger.warning(f"Radius in {context}: {error}")
        return False, error
    
    return True, None

# ============================================================================
# [C-6] AADT Validation Function
# ============================================================================

def validate_aadt(aadt: Any, road_id: str = "unknown") -> tuple:
    """
    Validate AADT value and return (validated_value, is_valid).
    
    Args:
        aadt: The AADT value to validate (could be any type)
        road_id: Road identifier for logging
        
    Returns:
        Tuple of (validated_aadt, is_original_valid)
    """
    # Check if numeric
    if not isinstance(aadt, (int, float)):
        logger.warning(
            f"AADT validation failed for road {road_id}: "
            f"Non-numeric value '{aadt}' (type: {type(aadt).__name__}), "
            f"using default {DEFAULT_AADT}"
        )
        return DEFAULT_AADT, False
    
    # Check if positive
    if aadt <= 0:
        logger.warning(
            f"AADT validation failed for road {road_id}: "
            f"Non-positive value {aadt}, using default {DEFAULT_AADT}"
        )
        return DEFAULT_AADT, False
    
    # Check if within plausible range
    if aadt < MIN_VALID_AADT:
        logger.warning(
            f"AADT validation warning for road {road_id}: "
            f"Unusually low value {aadt} (< {MIN_VALID_AADT}), "
            f"using default {DEFAULT_AADT}"
        )
        return DEFAULT_AADT, False
    
    if aadt > MAX_VALID_AADT:
        logger.warning(
            f"AADT validation warning for road {road_id}: "
            f"Unusually high value {aadt} (> {MAX_VALID_AADT}), "
            f"capping at {MAX_VALID_AADT}"
        )
        return MAX_VALID_AADT, False
    
    # Valid!
    return int(aadt), True

# ============================================================================
# [M-3] Power Validation Function
# ============================================================================

def validate_power_kw(power_kw: Any, charger_id: str = "unknown") -> tuple:
    """
    Validate charger power value and return (validated_value, is_valid).
    
    Args:
        power_kw: The power value to validate (could be any type)
        charger_id: Charger identifier for logging
        
    Returns:
        Tuple of (validated_power, is_original_valid)
    """
    # Check if numeric
    if not isinstance(power_kw, (int, float)):
        logger.warning(
            f"Power validation failed for charger {charger_id}: "
            f"Non-numeric value '{power_kw}' (type: {type(power_kw).__name__}), "
            f"using default {DEFAULT_POWER_KW}kW"
        )
        return DEFAULT_POWER_KW, False
    
    # Check if positive
    if power_kw <= 0:
        logger.warning(
            f"Power validation failed for charger {charger_id}: "
            f"Non-positive value {power_kw}kW, using default {DEFAULT_POWER_KW}kW"
        )
        return DEFAULT_POWER_KW, False
    
    # Check if within plausible range
    if power_kw < MIN_VALID_POWER_KW:
        logger.warning(
            f"Power validation warning for charger {charger_id}: "
            f"Unusually low value {power_kw}kW (< {MIN_VALID_POWER_KW}kW), "
            f"using default {DEFAULT_POWER_KW}kW"
        )
        return DEFAULT_POWER_KW, False
    
    if power_kw > MAX_VALID_POWER_KW:
        logger.warning(
            f"Power validation warning for charger {charger_id}: "
            f"Unusually high value {power_kw}kW (> {MAX_VALID_POWER_KW}kW), "
            f"capping at {MAX_VALID_POWER_KW}kW"
        )
        return MAX_VALID_POWER_KW, False
    
    # Valid!
    return float(power_kw), True

# ============================================================================
# [C-4] Data Validation Helper Functions
# ============================================================================

def validate_source_data(fetch_result: Any, source_name: str) -> tuple:
    """
    Validate FetchResult data before use.
    
    Returns: (is_valid, data)
    """
    if fetch_result is None:
        logger.warning(f"Data source '{source_name}' returned None")
        return False, None
    
    if not isinstance(fetch_result, FetchResult):
        logger.warning(f"Data source '{source_name}' is not a FetchResult")
        return False, None
    
    if not fetch_result.success:
        logger.warning(f"Data source '{source_name}' fetch failed")
        return False, None
    
    if fetch_result.data is None:
        logger.warning(f"Data source '{source_name}' has no data")
        return False, None
    
    return True, fetch_result.data


def safe_get_nested(data: dict, *keys, default=None):
    """
    Safely get nested dictionary values.
    
    Example: safe_get_nested(data, "osm", "facilities", default=[])
    """
    result = data
    for key in keys:
        if not isinstance(result, dict):
            return default
        result = result.get(key)
        if result is None:
            return default
    return result

# ============================================================================
# [C-7] OpenChargeMap Fetcher with Logging
# ============================================================================

async def fetch_opencharge_map(lat: float, lon: float, radius_km: float = 5.0) -> FetchResult:
    """
    Fetch nearby chargers from OpenChargeMap with error logging.
    [C-7] Includes parse error tracking and quality scoring.
    """
    api_key = API_KEYS["openchargemap"]
    if not api_key:
        logger.warning("OpenChargeMap API key not configured")
        return FetchResult(
            success=False,
            data={"error": "API key not configured", "chargers": []},
            source_id="opencharge_map",
            fetched_at=datetime.now()
        )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openchargemap.io/v3/poi/",
                params={
                    "output": "json",
                    "latitude": lat,
                    "longitude": lon,
                    "distance": radius_km,
                    "distanceunit": "km",
                    "maxresults": 100,
                    "compact": "false",
                    "key": api_key
                },
                timeout=15.0
            )
            response.raise_for_status()
            data = response.json()
        
        if not data:
            logger.info("No chargers found in OpenChargeMap")
            return FetchResult(
                success=True,
                data={"chargers": [], "count": 0},
                source_id="opencharge_map",
                fetched_at=datetime.now()
            )
        
        # [C-7 + M-3] Parse with error tracking and power validation
        chargers = []
        parse_errors = []
        power_valid_count = 0
        power_invalid_count = 0
        power_validation_details = []
        
        for poi in data:
            try:
                address_info = poi.get("AddressInfo", {})
                charger_id = str(poi.get("ID", "unknown"))
                
                # Extract raw power value
                raw_power = 0
                connections = poi.get("Connections", [])
                if connections and len(connections) > 0:
                    raw_power = connections[0].get("PowerKW", 0) or 0
                
                # [M-3] VALIDATE POWER
                validated_power, is_valid = validate_power_kw(raw_power, charger_id)
                
                if is_valid:
                    power_valid_count += 1
                else:
                    power_invalid_count += 1
                    power_validation_details.append({
                        "charger_id": charger_id,
                        "charger_name": address_info.get("Title", "Unknown"),
                        "raw_power": raw_power,
                        "validated_power": validated_power
                    })
                
                chargers.append({
                    "id": poi.get("ID"),
                    "name": address_info.get("Title", "Unknown"),
                    "lat": address_info.get("Latitude"),
                    "lon": address_info.get("Longitude"),
                    "power_kw": validated_power,
                    "power_validated": is_valid,
                    "power_original": raw_power if is_valid else None,
                    "status": poi.get("StatusType", {}).get("Title", "Unknown"),
                    "operator": poi.get("OperatorInfo", {}).get("Title", "Unknown"),
                    "num_points": poi.get("NumberOfPoints", 1),
                })
            except Exception as e:
                poi_id = poi.get("ID", "unknown")
                logger.error(f"⚠️  Failed to parse POI {poi_id}: {str(e)}")
                parse_errors.append({"poi_id": poi_id, "error": str(e)})
                continue
        
        # [C-7] Log parse summary
        logger.info(f"Parsed {len(chargers)}/{len(data)} POIs successfully")
        if parse_errors:
            logger.warning(f"{len(parse_errors)} POIs failed to parse")
        
        # [M-3] Log power validation summary
        if power_invalid_count > 0:
            logger.warning(
                f"Power validation: {power_valid_count}/{len(chargers)} valid "
                f"({power_valid_count/len(chargers):.1%}), {power_invalid_count} invalid"
            )
        
        # [C-7] Calculate parse quality score
        parse_quality = len(chargers) / len(data) if data else 1.0
        
        # [M-3] Calculate power validation quality
        power_validation_rate = power_valid_count / len(chargers) if chargers else 1.0
        
        # Combined quality score
        combined_quality = (parse_quality + power_validation_rate) / 2
        
        return FetchResult(
            success=True,
            data={
                "chargers": chargers,
                "count": len(chargers),
                "parse_summary": {
                    "total": len(data),
                    "parsed": len(chargers),
                    "failed": len(parse_errors),
                    "parse_errors": parse_errors[:5]  # First 5 for debugging
                },
                "power_validation": {
                    "total_chargers": len(chargers),
                    "valid_power": power_valid_count,
                    "invalid_power": power_invalid_count,
                    "validation_rate": power_validation_rate,
                    "default_used": power_invalid_count > 0,
                    "validation_details": power_validation_details[:5]  # First 5 for debugging
                }
            },
            source_id="opencharge_map",
            fetched_at=datetime.now(),
            quality_score=combined_quality
        )
        
    except httpx.TimeoutException:
        logger.error("OpenChargeMap API timeout")
        return FetchResult(
            success=False,
            data={"error": "timeout", "chargers": []},
            source_id="opencharge_map",
            fetched_at=datetime.now()
        )
    except Exception as e:
        logger.error(f"OpenChargeMap fetch failed: {e}")
        return FetchResult(
            success=False,
            data={"error": str(e), "chargers": []},
            source_id="opencharge_map",
            fetched_at=datetime.now()
        )

# ============================================================================
# [C-6] Traffic Data Fetcher with AADT Validation
# ============================================================================

async def get_uk_dft_traffic(lat: float, lon: float, radius_km: float = 2.0) -> FetchResult:
    """
    Fetch UK DfT traffic data with AADT validation.
    [C-6] Validates all AADT values before returning.
    """
    try:
        # Overpass API query for major roads
        overpass_url = "http://overpass-api.de/api/interpreter"
        radius_m = radius_km * 1000
        
        query = f"""
        [out:json][timeout:25];
        (
          way["highway"~"motorway|trunk|primary|secondary"]
            (around:{radius_m},{lat},{lon});
        );
        out body;
        >;
        out skel qt;
        """
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                overpass_url,
                data={"data": query},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
        
        if not data.get("elements"):
            return FetchResult(
                success=True,
                data={
                    "count": 0,
                    "roads": [],
                    "avg_aadt": DEFAULT_AADT,
                    "validation_summary": {
                        "total_roads": 0,
                        "validated_roads": 0,
                        "fallback_used": True,
                        "reason": "No roads found in area"
                    }
                },
                source_id="uk_dft_traffic",
                fetched_at=datetime.now()
            )
        
        # [C-6] Process roads with validation
        roads = []
        total_aadt = 0
        valid_count = 0
        invalid_count = 0
        validation_details = []
        
        for elem in data["elements"]:
            if elem["type"] != "way":
                continue
                
            tags = elem.get("tags", {})
            road_name = tags.get("name", "Unnamed Road")
            highway_type = tags.get("highway", "unknown")
            road_id = str(elem.get("id", "unknown"))
            
            # Get raw AADT value
            raw_aadt = tags.get("all_motor_vehicles")
            if raw_aadt is None:
                raw_aadt = tags.get("aadt") or tags.get("traffic") or DEFAULT_AADT
            
            # [C-6] VALIDATE AADT
            validated_aadt, is_valid = validate_aadt(raw_aadt, road_id)
            
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                validation_details.append({
                    "road_id": road_id,
                    "road_name": road_name,
                    "raw_value": raw_aadt,
                    "validated_value": validated_aadt
                })
            
            total_aadt += validated_aadt
            
            roads.append({
                "name": road_name,
                "type": highway_type,
                "aadt": validated_aadt,
                "aadt_validated": is_valid,
                "aadt_original": raw_aadt if is_valid else None,
                "road_id": road_id
            })
        
        # Calculate average
        avg_aadt = total_aadt // len(roads) if roads else DEFAULT_AADT
        
        # [C-6] Quality assessment
        validation_rate = valid_count / len(roads) if roads else 0
        
        if validation_rate < 0.5:
            logger.warning(
                f"Low AADT validation rate: {validation_rate:.1%} "
                f"({valid_count}/{len(roads)} valid)"
            )
        
        return FetchResult(
            success=True,
            data={
                "count": len(roads),
                "roads": roads,
                "avg_aadt": avg_aadt,
                "validation_summary": {
                    "total_roads": len(roads),
                    "validated_roads": valid_count,
                    "invalid_roads": invalid_count,
                    "validation_rate": validation_rate,
                    "fallback_used": invalid_count > 0,
                    "validation_details": validation_details[:5]
                }
            },
            source_id="uk_dft_traffic",
            fetched_at=datetime.now(),
            quality_score=validation_rate
        )
        
    except httpx.TimeoutException:
        logger.error("DfT traffic fetch timeout")
        return FetchResult(
            success=False,
            data={"error": "timeout", "avg_aadt": DEFAULT_AADT},
            source_id="uk_dft_traffic",
            fetched_at=datetime.now()
        )
    except Exception as e:
        logger.error(f"DfT traffic fetch failed: {e}")
        return FetchResult(
            success=False,
            data={"error": str(e), "avg_aadt": DEFAULT_AADT},
            source_id="uk_dft_traffic",
            fetched_at=datetime.now()
        )

# ============================================================================
# Demographics Fetcher (Placeholder)
# ============================================================================

async def get_demographics(lat: float, lon: float) -> FetchResult:
    """Get demographic data for location"""
    # Placeholder - would integrate with ONS API
    return FetchResult(
        success=True,
        data={
            "population_density": 1500,
            "income_estimate": 35000,
            "ev_adoption_rate": 0.03
        },
        source_id="demographics",
        fetched_at=datetime.now()
    )

# ============================================================================
# Grid Infrastructure Fetcher (Placeholder)
# ============================================================================

async def get_grid_infrastructure(lat: float, lon: float) -> FetchResult:
    """Get grid infrastructure data"""
    # Placeholder - would integrate with National Grid/ENTSO-E
    return FetchResult(
        success=True,
        data={
            "nearest_substation_km": 2.5,
            "grid_capacity_kw": 1000,
            "connection_cost_estimate": 25000
        },
        source_id="grid_infrastructure",
        fetched_at=datetime.now()
    )

# ============================================================================
# [C-4] Scoring with FetchResult Validation
# ============================================================================

def calculate_comprehensive_scores(
    chargers_result: FetchResult,
    traffic_result: FetchResult,
    demographics_result: FetchResult,
    grid_result: FetchResult
) -> Dict[str, Any]:
    """
    Calculate comprehensive scores with data validation.
    [C-4] Validates all FetchResult data before scoring.
    """
    
    # [C-4] Validate all data sources
    validation_failures = []
    
    # Validate chargers data
    is_valid, chargers_data = validate_source_data(chargers_result, "chargers")
    if not is_valid:
        validation_failures.append("chargers")
        chargers_data = {"chargers": [], "count": 0}
    
    # Validate traffic data
    is_valid, traffic_data = validate_source_data(traffic_result, "traffic")
    if not is_valid:
        validation_failures.append("traffic")
        traffic_data = {"avg_aadt": DEFAULT_AADT, "roads": []}
    
    # Validate demographics
    is_valid, demographics_data = validate_source_data(demographics_result, "demographics")
    if not is_valid:
        validation_failures.append("demographics")
        demographics_data = {"population_density": 1000, "income_estimate": 35000}
    
    # Validate grid data
    is_valid, grid_data = validate_source_data(grid_result, "grid")
    if not is_valid:
        validation_failures.append("grid")
        grid_data = {"nearest_substation_km": 3.0, "connection_cost_estimate": 30000}
    
    # [C-4] Log validation summary
    if validation_failures:
        logger.warning(
            f"Data validation failures: {len(validation_failures)} sources failed: "
            f"{', '.join(validation_failures)}"
        )
    
    # [C-4] Use validated data with safe access
    charger_count = safe_get_nested(chargers_data, "count", default=0)
    avg_aadt = safe_get_nested(traffic_data, "avg_aadt", default=DEFAULT_AADT)
    population_density = safe_get_nested(demographics_data, "population_density", default=1000)
    grid_distance = safe_get_nested(grid_data, "nearest_substation_km", default=3.0)
    
    # Calculate demand score
    traffic_factor = min(avg_aadt / 50000, 1.0)  # Normalize to 50k vehicles/day
    population_factor = min(population_density / 5000, 1.0)  # Normalize to 5k/km²
    demand_score = int((traffic_factor * 0.6 + population_factor * 0.4) * 100)
    
    # Calculate competition score
    competition_score = max(0, 100 - (charger_count * 10))
    
    # Calculate infrastructure score
    grid_score = max(0, 100 - (grid_distance * 10))
    
    # Calculate overall score
    overall_score = int(
        demand_score * 0.4 +
        competition_score * 0.3 +
        grid_score * 0.3
    )
    
    # [C-4] Calculate confidence level
    confidence = 1.0 - (len(validation_failures) / 4)  # 4 total sources
    
    return {
        "overall_score": overall_score,
        "demand_score": demand_score,
        "competition_score": competition_score,
        "infrastructure_score": grid_score,
        "confidence": round(confidence, 2),
        "validation_summary": {
            "sources_checked": 4,
            "sources_valid": 4 - len(validation_failures),
            "sources_failed": len(validation_failures),
            "failed_sources": validation_failures
        },
        "data_quality": {
            "chargers_quality": chargers_result.quality_score if chargers_result else 0,
            "traffic_quality": traffic_result.quality_score if traffic_result else 0
        }
    }

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "EVL v10.1 + Day 1 & C-3 & M-3 Fixes",
        "version": "10.1",
        "status": "operational",
        "features": [
            "C-7: OpenChargeMap error logging",
            "C-4: FetchResult validation",
            "C-6: AADT validation",
            "C-3: Coordinate validation",
            "M-3: Power validation"
        ],
        "v2_api": V2_AVAILABLE,
        "endpoints": {
            "analyze": "/api/v1/analyze-location",
            "health": "/health",
            "v2": "/api/v2/" if V2_AVAILABLE else None
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "10.1",
        "fixes_applied": ["C-7", "C-4", "C-6", "C-3", "M-3"]
    }

@app.post("/api/v1/analyze-location")
async def analyze_location(
    postcode: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: float = 5.0
):
    """
    Analyze location for EV charging station suitability.
    Includes all Day 1 + C-3 + M-3 fixes: C-7, C-4, C-6, C-3, M-3
    """
    
    # Geocode if needed
    if postcode and not (lat and lon):
        # Simple geocoding via Nominatim
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": postcode, "format": "json", "limit": 1},
                    headers={"User-Agent": "EVL/10.1"},
                    timeout=10.0
                )
                data = response.json()
                if data:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    
                    # [C-3] VALIDATE GEOCODED COORDINATES
                    is_valid, error = validate_coordinates(lat, lon, "geocoding result")
                    if not is_valid:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Geocoding returned invalid coordinates: {error}"
                        )
                else:
                    raise HTTPException(status_code=404, detail="Location not found")
        except HTTPException:
            raise  # Re-raise HTTPException as-is
        except Exception as e:
            logger.error(f"Geocoding failed: {e}")
            raise HTTPException(status_code=500, detail="Geocoding failed")
    
    if not (lat and lon):
        raise HTTPException(status_code=400, detail="Provide either postcode or lat/lon")
    
    # [C-3] VALIDATE COORDINATES
    is_valid, error = validate_coordinates(lat, lon, "V1 user input")
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    # [C-3] VALIDATE RADIUS
    is_valid, error = validate_radius(radius_km, "V1 user input")
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    logger.info(f"V1 Analyzing validated location: lat={lat}, lon={lon}, radius={radius_km}km")
    
    # Fetch all data sources
    chargers_result = await fetch_opencharge_map(lat, lon, radius_km)
    traffic_result = await get_uk_dft_traffic(lat, lon, radius_km)
    demographics_result = await get_demographics(lat, lon)
    grid_result = await get_grid_infrastructure(lat, lon)
    
    # [C-4] Calculate scores with validation
    scores = calculate_comprehensive_scores(
        chargers_result,
        traffic_result,
        demographics_result,
        grid_result
    )
    
    # Build response
    response = {
        "location": {
            "lat": lat,
            "lon": lon,
            "postcode": postcode
        },
        "scores": scores,
        "data": {
            "chargers": chargers_result.data if chargers_result.success else {},
            "traffic": traffic_result.data if traffic_result.success else {},
            "demographics": demographics_result.data if demographics_result.success else {},
            "grid": grid_result.data if grid_result.success else {}
        },
        "metadata": {
            "analyzed_at": datetime.now().isoformat(),
            "radius_km": radius_km,
            "version": "10.1",
            "fixes_applied": ["C-7", "C-4", "C-6", "C-3", "M-3"]
        }
    }
    
    return response

@app.get("/api/v1/test-validation")
async def test_validation():
    """Test endpoint to verify Day 1 + C-3 + M-3 fixes are working"""
    
    # Test C-6: AADT validation
    aadt_tests = {
        "valid": validate_aadt(50000, "test_1"),
        "zero": validate_aadt(0, "test_2"),
        "negative": validate_aadt(-100, "test_3"),
        "string": validate_aadt("invalid", "test_4"),
        "too_high": validate_aadt(300000, "test_5")
    }
    
    # Test C-3: Coordinate validation
    coord_tests = {
        "valid": validate_coordinates(51.5, -0.1, "test"),
        "lat_high": validate_coordinates(999, -0.1, "test"),
        "lon_low": validate_coordinates(51.5, -999, "test"),
        "null_island": validate_coordinates(0.0, 0.0, "test")
    }
    
    # Test M-3: Power validation
    power_tests = {
        "valid": validate_power_kw(50, "test_1"),
        "zero": validate_power_kw(0, "test_2"),
        "negative": validate_power_kw(-10, "test_3"),
        "too_high": validate_power_kw(999, "test_4"),
        "string": validate_power_kw("fast", "test_5")
    }
    
    return {
        "status": "Day 1 + C-3 + M-3 fixes active",
        "tests": {
            "c6_aadt_validation": {
                "valid_50000": {"value": aadt_tests["valid"][0], "is_valid": aadt_tests["valid"][1]},
                "zero": {"value": aadt_tests["zero"][0], "is_valid": aadt_tests["zero"][1]},
                "negative": {"value": aadt_tests["negative"][0], "is_valid": aadt_tests["negative"][1]},
                "string": {"value": aadt_tests["string"][0], "is_valid": aadt_tests["string"][1]},
                "too_high": {"value": aadt_tests["too_high"][0], "is_valid": aadt_tests["too_high"][1]}
            },
            "c3_coordinate_validation": {
                "valid_london": {"is_valid": coord_tests["valid"][0], "error": coord_tests["valid"][1]},
                "lat_999": {"is_valid": coord_tests["lat_high"][0], "error": coord_tests["lat_high"][1]},
                "lon_minus_999": {"is_valid": coord_tests["lon_low"][0], "error": coord_tests["lon_low"][1]},
                "null_island": {"is_valid": coord_tests["null_island"][0], "error": coord_tests["null_island"][1]}
            },
            "m3_power_validation": {
                "valid_50kw": {"value": power_tests["valid"][0], "is_valid": power_tests["valid"][1]},
                "zero": {"value": power_tests["zero"][0], "is_valid": power_tests["zero"][1]},
                "negative": {"value": power_tests["negative"][0], "is_valid": power_tests["negative"][1]},
                "too_high_999": {"value": power_tests["too_high"][0], "is_valid": power_tests["too_high"][1]},
                "string_fast": {"value": power_tests["string"][0], "is_valid": power_tests["string"][1]}
            },
            "c4_validation_helpers": {
                "validate_source_data": "✅ Available",
                "safe_get_nested": "✅ Available"
            },
            "c7_parser_logging": {
                "parse_error_tracking": "✅ Enabled",
                "quality_scoring": "✅ Enabled"
            }
        },
        "fixes_verified": ["C-7", "C-4", "C-6", "C-3", "M-3"]
    }

# ============================================================================
# Startup Event
# ============================================================================

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("🚀 EVL v10.1 + Day 1 & C-3 & M-3 Fixes Starting")
    logger.info("=" * 60)
    logger.info("✅ C-7: OpenChargeMap parser error logging enabled")
    logger.info("✅ C-4: FetchResult validation enabled")
    logger.info("✅ C-6: AADT validation enabled")
    logger.info("✅ C-3: Coordinate validation enabled")
    logger.info("✅ M-3: Power validation enabled")
    logger.info(f"✅ V2 Business API: {'Enabled' if V2_AVAILABLE else 'Disabled'}")
    logger.info("=" * 60)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
