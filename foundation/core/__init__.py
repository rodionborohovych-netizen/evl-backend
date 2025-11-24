"""
EVL Foundation Package

Production-grade data quality infrastructure for EVL v10.1+

Main components:
- database: SQLAlchemy models for tracking
- metadata: Provenance tracking for API calls
- validation: Data contracts and quality checks
- fetchers: Real data fetchers with graceful degradation

Usage:
    from foundation.core import track_fetch, validate_response, fetch_all_data
    
    @track_fetch("entsoe", "ENTSO-E Grid")
    @validate_response("entsoe")
    async def get_entsoe_data():
        return data
"""

# Database
from .database import (
    init_database,
    get_session,
    store_fetch_metadata,
    get_recent_fetches,
    store_alert,
    FetchMetadata,
    DataContract,
    SourceHealth,
    Alert,
    ReconciliationCheck
)

# Metadata tracking
from .metadata import (
    track_fetch,
    TrackedHTTPClient,
    create_metadata,
    enrich_data_with_metadata,
    calculate_content_hash,
    count_rows,
    calculate_data_size
)

# Validation
from .validation import (
    validate_response,
    validate_source_data,
    validate_freshness,
    enrich_data_with_validation,
    get_contract,
    get_all_contracts,
    calculate_quality_score,
    ValidationError,
    DATA_CONTRACTS
)

# Fetchers
from .fetchers import (
    fetch_all_data,
    FetchResult,
    get_data_sources_summary,
    fetch_opencharge_map,
    fetch_postcode_data,
    fetch_ons_demographics,
    fetch_dft_vehicle_stats,
    fetch_osm_facilities,
    fetch_entsoe_grid,
    fetch_national_grid_eso,
    fetch_tomtom_traffic,
    calculate_overall_quality_score
)

__version__ = "1.0.0"

# SINGLE, COMPLETE __all__ DEFINITION
__all__ = [
    # Database
    "init_database",
    "get_session",
    "store_fetch_metadata",
    "get_recent_fetches",
    "store_alert",
    "FetchMetadata",
    "DataContract",
    "SourceHealth",
    "Alert",
    "ReconciliationCheck",
    
    # Metadata
    "track_fetch",
    "TrackedHTTPClient",
    "create_metadata",
    "enrich_data_with_metadata",
    "calculate_content_hash",
    "count_rows",
    "calculate_data_size",
    
    # Validation
    "validate_response",
    "validate_source_data",
    "validate_freshness",
    "enrich_data_with_validation",
    "get_contract",
    "get_all_contracts",
    "calculate_quality_score",
    "ValidationError",
    "DATA_CONTRACTS",
    
    # Fetchers
    "fetch_all_data",
    "FetchResult",
    "get_data_sources_summary",
    "fetch_opencharge_map",
    "fetch_postcode_data",
    "fetch_ons_demographics",
    "fetch_dft_vehicle_stats",
    "fetch_osm_facilities",
    "fetch_entsoe_grid",
    "fetch_national_grid_eso",
    "fetch_tomtom_traffic",
    "calculate_overall_quality_score",
]
