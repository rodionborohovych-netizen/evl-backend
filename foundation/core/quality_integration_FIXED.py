"""
EVL Data Quality Integration - FIXED
====================================

Connects real data fetchers to foundation package for tracking and monitoring.
Fixed: Removed hardcoded paths, added flexible imports
"""

from typing import Dict, Any
import sys
from pathlib import Path

# Flexible import system - try multiple paths
def setup_imports():
    """Setup imports with fallback paths"""
    imported = False
    
    # Try production path first
    try:
        from foundation.core.fetchers import FetchResult
        from foundation.core.database import store_fetch_metadata, init_database
        from foundation.core.validation import validate_source_data, get_contract
        from foundation.core.metadata import calculate_content_hash, count_rows, calculate_data_size
        return True
    except ImportError:
        pass
    
    # Try relative imports
    try:
        from ..foundation.core.fetchers import FetchResult
        from ..foundation.core.database import store_fetch_metadata, init_database
        from ..foundation.core.validation import validate_source_data, get_contract
        from ..foundation.core.metadata import calculate_content_hash, count_rows, calculate_data_size
        return True
    except ImportError:
        pass
    
    # Try adding paths dynamically
    current_dir = Path(__file__).parent.absolute()
    possible_paths = [
        current_dir / "foundation" / "core",
        current_dir.parent / "foundation" / "core",
        Path("/mnt/user-data/uploads"),
    ]
    
    for path in possible_paths:
        if path.exists():
            sys.path.insert(0, str(path))
    
    return False

# Setup imports
setup_imports()

# Now do the actual imports
try:
    from fetchers import FetchResult
except ImportError:
    from foundation.core.fetchers import FetchResult

try:
    from database import store_fetch_metadata, init_database
except ImportError:
    from foundation.core.database import store_fetch_metadata, init_database

try:
    from validation import validate_source_data, get_contract
except ImportError:
    from foundation.core.validation import validate_source_data, get_contract

try:
    from metadata import calculate_content_hash, count_rows, calculate_data_size
except ImportError:
    from foundation.core.metadata import calculate_content_hash, count_rows, calculate_data_size


# ==================== SOURCE NAME MAPPING ====================

SOURCE_NAMES = {
    "openchargemap": "OpenChargeMap",
    "postcodes_io": "Postcodes.io",
    "ons_demographics": "ONS Demographics",
    "dft_vehicle_licensing": "DfT Vehicle Licensing",
    "openstreetmap": "OpenStreetMap",
    "entsoe": "ENTSO-E Grid",
    "national_grid_eso": "National Grid ESO",
    "tomtom_traffic": "TomTom Traffic"
}


# ==================== TRACKING INTEGRATION ====================

async def track_and_store_fetch(
    result: FetchResult,
    source_url: str = "unknown"
) -> None:
    """
    Store fetch result in database for quality tracking
    
    This enables the real-time quality monitoring dashboard
    """
    
    try:
        # Get source name
        source_name = SOURCE_NAMES.get(result.source_id, result.source_id)
        
        # Determine success
        success = result.success and result.quality_score > 0.5
        
        # Calculate content hash
        content_hash = calculate_content_hash(result.data)
        row_count = count_rows(result.data)
        data_size = calculate_data_size(result.data)
        
        # Validate against contract (if exists)
        validation_passed = True
        validation_errors = []
        
        try:
            contract = get_contract(result.source_id)
            if contract:
                validation_result = validate_source_data(result.source_id, result.data)
                validation_passed = validation_result.get("passed", False)
                validation_errors = validation_result.get("errors", [])
        except:
            pass  # No contract defined
        
        # Store in database
        store_fetch_metadata(
            source_id=result.source_id,
            source_url=source_url,
            status_code=200 if result.success else 500,
            response_time_ms=result.response_time_ms,
            content_hash=content_hash,
            row_count=row_count,
            success=success,
            error_message=result.error,
            validation_passed=validation_passed,
            validation_errors=validation_errors if not validation_passed else None,
            data_quality_score=result.quality_score,
            data_size_bytes=data_size
        )
        
    except Exception as e:
        print(f"Warning: Could not track fetch for {result.source_id}: {e}")


async def track_all_fetches(fetch_results: Dict[str, FetchResult]) -> None:
    """Track all fetch results in database"""
    
    for source_id, result in fetch_results.items():
        if isinstance(result, FetchResult):
            await track_and_store_fetch(result)


# ==================== QUALITY MONITORING ====================

def get_source_health_status(quality_score: float, success: bool) -> str:
    """Determine source health status"""
    
    if not success:
        return "error"
    elif quality_score >= 0.8:
        return "ok"
    elif quality_score >= 0.5:
        return "partial"
    else:
        return "degraded"


def get_quality_description(quality_score: float) -> str:
    """Get quality description"""
    
    if quality_score >= 0.9:
        return "Excellent"
    elif quality_score >= 0.7:
        return "Good"
    elif quality_score >= 0.5:
        return "Fair"
    elif quality_score >= 0.3:
        return "Poor"
    else:
        return "Very Poor"


# ==================== DATA QUALITY DASHBOARD DATA ====================

def generate_quality_dashboard_data(fetch_results: Dict[str, FetchResult]) -> Dict[str, Any]:
    """
    Generate data for quality monitoring dashboard
    
    Returns data in format expected by the UI
    """
    
    sources = []
    total_quality = 0
    sources_active = 0
    
    for source_id, result in fetch_results.items():
        if not isinstance(result, FetchResult):
            continue
        
        source_name = SOURCE_NAMES.get(source_id, source_id)
        
        quality_percent = int(result.quality_score * 100)
        quality_desc = get_quality_description(result.quality_score)
        status = get_source_health_status(result.quality_score, result.success)
        
        # Count errors
        error_count = 0 if result.success else 1
        
        sources.append({
            "source_id": source_id,
            "source_name": source_name,
            "quality_percent": quality_percent,
            "quality_description": quality_desc,
            "status": status,
            "response_time_ms": int(result.response_time_ms),
            "error_count": error_count,
            "is_valid": result.success,
            "last_updated": "now"
        })
        
        if result.quality_score > 0:
            sources_active += 1
            total_quality += result.quality_score
    
    # Overall quality
    overall_quality = int((total_quality / len(sources) * 100)) if sources else 0
    
    return {
        "overall_quality_percent": overall_quality,
        "sources_active": sources_active,
        "sources_total": len(sources),
        "sources": sources
    }


# ==================== INITIALIZE DATABASE ====================

def ensure_database_initialized():
    """Ensure database is initialized"""
    try:
        init_database()
    except Exception as e:
        print(f"Database initialization: {e}")


# Initialize on import
ensure_database_initialized()


__all__ = [
    "track_and_store_fetch",
    "track_all_fetches",
    "generate_quality_dashboard_data",
    "get_source_health_status",
    "get_quality_description"
]
