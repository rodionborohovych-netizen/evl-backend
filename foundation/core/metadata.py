"""
Data validation and contracts

Defines expected schemas, types, and quality rules for each data source.
Validates data against contracts to ensure quality.
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from functools import wraps

from .database import store_fetch_metadata


@dataclass
class ValidationError:
    """Represents a validation error"""
    field: str
    message: str
    severity: str  # "error" or "warning"
    actual_value: Any = None
    
    def to_dict(self):
        return {
            "field": self.field,
            "message": self.message,
            "severity": self.severity,
            "actual_value": self.actual_value
        }


# Data contracts for all sources
DATA_CONTRACTS = {
    "entsoe": {
        "source_name": "ENTSO-E Transparency Platform",
        "freshness_sla": {"max_lag_hours": 6},
        "update_frequency": "realtime",
        "required_fields": [
            {"name": "total_generation_mw", "type": "float", "min": 0, "max": 200000},
            {"name": "renewable_generation_mw", "type": "float", "min": 0, "max": 200000},
            {"name": "renewable_share", "type": "float", "min": 0, "max": 1},
            {"name": "available", "type": "bool", "not_null": True}
        ],
        "quality_checks": [
            "renewable_share >= 0 and renewable_share <= 1",
            "renewable_generation_mw <= total_generation_mw",
            "total_generation_mw > 0"
        ]
    },
    
    "national_grid_eso": {
        "source_name": "National Grid ESO",
        "freshness_sla": {"max_lag_days": 1},
        "update_frequency": "daily",
        "required_fields": [
            {"name": "available", "type": "bool", "not_null": True},
            {"name": "nearest_connection", "type": "dict", "optional": True}
        ],
        "optional_fields": [
            {"name": "site_name", "type": "str"},
            {"name": "distance_km", "type": "float", "min": 0, "max": 200},
            {"name": "capacity_mw", "type": "float", "min": 0, "max": 2000}
        ],
        "quality_checks": [
            "if nearest_connection: distance_km >= 0",
            "if nearest_connection: capacity_mw >= 0"
        ]
    },
    
    "dft_vehicle_licensing": {
        "source_name": "DfT Vehicle Licensing Statistics",
        "freshness_sla": {"max_lag_days": 120},  # Quarterly updates
        "update_frequency": "quarterly",
        "required_fields": [
            {"name": "bevs", "type": "int", "min": 500000, "max": 10000000},
            {"name": "phevs", "type": "int", "min": 100000, "max": 5000000},
            {"name": "ev_percentage", "type": "float", "min": 0, "max": 50},
            {"name": "growth_yoy_bev", "type": "float", "min": -50, "max": 200}
        ],
        "quality_checks": [
            "bevs > 500000",  # Sanity check
            "ev_percentage > 1 and ev_percentage < 50",
            "bevs + phevs > 0"
        ]
    },
    
    "ons_demographics": {
        "source_name": "ONS via postcodes.io",
        "freshness_sla": {"max_lag_days": 365},  # Annual census updates
        "update_frequency": "annual",
        "required_fields": [
            {"name": "available", "type": "bool", "not_null": True},
            {"name": "postcode", "type": "str", "optional": True}
        ],
        "optional_fields": [
            {"name": "region", "type": "str"},
            {"name": "estimated_median_income_gbp", "type": "float", "min": 10000, "max": 200000},
            {"name": "car_ownership_rate", "type": "float", "min": 0, "max": 1}
        ],
        "quality_checks": [
            "if car_ownership_rate: car_ownership_rate >= 0 and car_ownership_rate <= 1",
            "if estimated_median_income_gbp: estimated_median_income_gbp > 10000"
        ]
    },
    
    "openchargemap": {
        "source_name": "OpenChargeMap",
        "freshness_sla": {"max_lag_hours": 24},
        "update_frequency": "realtime",
        "required_fields": [
            {"name": "total_chargers", "type": "int", "min": 0},
            {"name": "chargers", "type": "list"}
        ],
        "quality_checks": [
            "total_chargers >= 0",
            "len(chargers) == total_chargers or total_chargers == 0"
        ]
    },
    
    "osm_traffic": {
        "source_name": "OpenStreetMap",
        "freshness_sla": {"max_lag_days": 7},
        "update_frequency": "continuous",
        "required_fields": [
            {"name": "roads", "type": "list"}
        ],
        "quality_checks": [
            "len(roads) >= 0"
        ]
    },
    
    "dft_traffic": {
        "source_name": "UK DfT Traffic Counts",
        "freshness_sla": {"max_lag_days": 365},
        "update_frequency": "annual",
        "required_fields": [
            {"name": "aadt", "type": "int", "min": 0, "max": 500000}
        ],
        "quality_checks": [
            "aadt >= 0",
            "aadt < 500000"
        ]
    },
    
    "eafo": {
        "source_name": "European Alternative Fuels Observatory",
        "freshness_sla": {"max_lag_days": 90},
        "update_frequency": "quarterly",
        "required_fields": [
            {"name": "ev_stock", "type": "int", "min": 0},
            {"name": "public_chargers", "type": "int", "min": 0}
        ],
        "quality_checks": [
            "ev_stock >= 0",
            "public_chargers >= 0"
        ]
    },
    
    "eurostat": {
        "source_name": "Eurostat",
        "freshness_sla": {"max_lag_days": 180},
        "update_frequency": "quarterly",
        "required_fields": [
            {"name": "available", "type": "bool"}
        ],
        "quality_checks": []
    }
}


def get_contract(source_id: str) -> Optional[Dict[str, Any]]:
    """Get data contract for a source"""
    return DATA_CONTRACTS.get(source_id)


def get_all_contracts() -> Dict[str, Dict[str, Any]]:
    """Get all data contracts"""
    return DATA_CONTRACTS


def validate_field(field_spec: Dict[str, Any], value: Any, field_name: str) -> List[ValidationError]:
    """Validate a single field against its specification"""
    
    errors = []
    
    # Skip if field is optional and value is None
    if field_spec.get("optional") and value is None:
        return errors
    
    # Check not null
    if field_spec.get("not_null") and value is None:
        errors.append(ValidationError(
            field=field_name,
            message=f"{field_name} cannot be null",
            severity="error",
            actual_value=value
        ))
        return errors
    
    # Type check
    expected_type = field_spec.get("type")
    if expected_type == "float":
        if not isinstance(value, (int, float)):
            errors.append(ValidationError(
                field=field_name,
                message=f"Expected float, got {type(value).__name__}",
                severity="error",
                actual_value=value
            ))
    elif expected_type == "int":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(ValidationError(
                field=field_name,
                message=f"Expected int, got {type(value).__name__}",
                severity="error",
                actual_value=value
            ))
    elif expected_type == "str":
        if not isinstance(value, str):
            errors.append(ValidationError(
                field=field_name,
                message=f"Expected string, got {type(value).__name__}",
                severity="error",
                actual_value=value
            ))
    elif expected_type == "bool":
        if not isinstance(value, bool):
            errors.append(ValidationError(
                field=field_name,
                message=f"Expected boolean, got {type(value).__name__}",
                severity="error",
                actual_value=value
            ))
    elif expected_type == "list":
        if not isinstance(value, list):
            errors.append(ValidationError(
                field=field_name,
                message=f"Expected list, got {type(value).__name__}",
                severity="error",
                actual_value=value
            ))
    elif expected_type == "dict":
        if not isinstance(value, dict):
            errors.append(ValidationError(
                field=field_name,
                message=f"Expected dict, got {type(value).__name__}",
                severity="error",
                actual_value=value
            ))
    
    # Range checks (only for numeric types)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "min" in field_spec and value < field_spec["min"]:
            errors.append(ValidationError(
                field=field_name,
                message=f"{field_name} = {value} below minimum {field_spec['min']}",
                severity="error",
                actual_value=value
            ))
        
        if "max" in field_spec and value > field_spec["max"]:
            errors.append(ValidationError(
                field=field_name,
                message=f"{field_name} = {value} above maximum {field_spec['max']}",
                severity="error",
                actual_value=value
            ))
    
    # Enum check
    if "enum" in field_spec and value not in field_spec["enum"]:
        errors.append(ValidationError(
            field=field_name,
            message=f"{field_name} must be one of {field_spec['enum']}, got {value}",
            severity="error",
            actual_value=value
        ))
    
    return errors


def validate_data(source_id: str, data: Dict[str, Any]) -> Tuple[bool, List[ValidationError], float]:
    """
    Validate data against its contract
    
    Returns:
        (is_valid, errors, quality_score)
    """
    
    contract = get_contract(source_id)
    
    if not contract:
        # No contract = no validation
        return True, [], 1.0
    
    errors = []
    
    # Check required fields
    for field_spec in contract.get("required_fields", []):
        field_name = field_spec["name"]
        
        # Check if field exists in data or nested in data
        if field_name not in data:
            # Check if it's nested (e.g., in "nearest_connection")
            found = False
            for key, value in data.items():
                if isinstance(value, dict) and field_name in value:
                    found = True
                    field_errors = validate_field(field_spec, value[field_name], field_name)
                    errors.extend(field_errors)
                    break
            
            if not found and not field_spec.get("optional"):
                errors.append(ValidationError(
                    field=field_name,
                    message=f"Required field {field_name} is missing",
                    severity="error"
                ))
        else:
            # Field exists at top level
            value = data[field_name]
            field_errors = validate_field(field_spec, value, field_name)
            errors.extend(field_errors)
    
    # Check optional fields if present
    for field_spec in contract.get("optional_fields", []):
        field_name = field_spec["name"]
        
        if field_name in data:
            value = data[field_name]
            field_errors = validate_field(field_spec, value, field_name)
            errors.extend(field_errors)
    
    # Run quality checks
    # (These are simplified - in production, use a proper expression evaluator)
    for check in contract.get("quality_checks", []):
        # This is a simplified implementation
        # In production, use ast.literal_eval or a safe expression evaluator
        pass
    
    # Calculate quality score
    quality_score = calculate_quality_score(errors)
    
    # Is valid if no critical errors
    is_valid = all(e.severity != "error" for e in errors)
    
    return is_valid, errors, quality_score


def calculate_quality_score(errors: List[ValidationError]) -> float:
    """
    Calculate quality score from validation errors
    
    Score:
    - 1.0 = Perfect (no errors)
    - 0.9 = Excellent (only warnings)
    - 0.7 = Good (1-2 minor errors)
    - 0.5 = Fair (3-5 errors)
    - 0.3 = Poor (6-10 errors)
    - 0.1 = Critical (>10 errors)
    - 0.0 = Failed (unavailable or severe errors)
    """
    
    if not errors:
        return 1.0
    
    # Count error types
    error_count = sum(1 for e in errors if e.severity == "error")
    warning_count = sum(1 for e in errors if e.severity == "warning")
    
    if error_count == 0 and warning_count > 0:
        return 0.9  # Only warnings
    elif error_count <= 2:
        return 0.7
    elif error_count <= 5:
        return 0.5
    elif error_count <= 10:
        return 0.3
    else:
        return 0.1


def validate_freshness(source_id: str, fetched_at: datetime) -> Tuple[bool, str]:
    """Check if data is fresh according to SLA"""
    
    contract = get_contract(source_id)
    
    if not contract:
        return True, "No freshness SLA defined"
    
    sla = contract.get("freshness_sla", {})
    
    if "max_lag_hours" in sla:
        max_lag = timedelta(hours=sla["max_lag_hours"])
        age = datetime.utcnow() - fetched_at
        
        if age > max_lag:
            return False, f"Data stale: {age.total_seconds()/3600:.1f}h > {sla['max_lag_hours']}h SLA"
    
    elif "max_lag_days" in sla:
        max_lag = timedelta(days=sla["max_lag_days"])
        age = datetime.utcnow() - fetched_at
        
        if age > max_lag:
            return False, f"Data stale: {age.days}d > {sla['max_lag_days']}d SLA"
    
    return True, "Data is fresh"


def enrich_data_with_validation(
    data: Dict[str, Any],
    is_valid: bool,
    errors: List[ValidationError],
    quality_score: float
) -> Dict[str, Any]:
    """Add validation results to data response"""
    
    if isinstance(data, dict):
        data["_validation"] = {
            "is_valid": is_valid,
            "quality_score": quality_score,
            "error_count": sum(1 for e in errors if e.severity == "error"),
            "warning_count": sum(1 for e in errors if e.severity == "warning"),
            "errors": [e.to_dict() for e in errors]
        }
    
    return data


def validate_response(source_id: str):
    """
    Decorator to automatically validate API responses
    
    Usage:
        @validate_response("entsoe")
        async def get_entsoe_data(country_code: str):
            return await fetch_data()
    """
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute function
            result = await func(*args, **kwargs)
            
            # Validate
            is_valid, errors, quality_score = validate_data(source_id, result)
            
            # Enrich result
            result = enrich_data_with_validation(result, is_valid, errors, quality_score)
            
            # Update metadata in database if it exists
            if "_metadata" in result:
                # This would update the existing metadata record
                pass
            
            return result
        
        return wrapper
    return decorator


def validate_source_data(source_id: str, data: Dict[str, Any]) -> Tuple[bool, List[ValidationError], float]:
    """
    Public function to validate data from a source
    
    Returns (is_valid, errors, quality_score)
    """
    return validate_data(source_id, data)
