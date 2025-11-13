"""
EVL Foundation Package - Integration Examples

Shows 3 different ways to integrate data quality tracking:
1. Decorator Pattern (easiest)
2. TrackedHTTPClient (recommended)
3. Manual Integration (most control)
"""

import asyncio
import httpx
import time
from datetime import datetime

# Import foundation modules
from core import (
    track_fetch,
    validate_response,
    TrackedHTTPClient,
    create_metadata,
    enrich_data_with_metadata,
    enrich_data_with_validation,
    validate_source_data,
    store_fetch_metadata
)


# ============================================================================
# EXAMPLE 1: DECORATOR PATTERN (Easiest - Minimal Code Changes)
# ============================================================================

@track_fetch("entsoe", "ENTSO-E Grid Data")
@validate_response("entsoe")
async def get_entsoe_with_decorators(country_code: str):
    """
    Example using decorators - easiest integration
    
    Just add decorators to your existing functions!
    - @track_fetch: Automatically tracks timing, success, errors
    - @validate_response: Automatically validates against data contract
    """
    
    # Your existing code unchanged
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://web-api.tp.entsoe.eu/api",
            params={"country": country_code}
        )
        
        data = {
            "source": "ENTSO-E",
            "available": True,
            "total_generation_mw": 35420.0,
            "renewable_generation_mw": 23850.0,
            "renewable_share": 0.673,
            "country": country_code
        }
        
        return data
    
    # Decorators automatically add:
    # - data["_metadata"] with fetch info
    # - data["_validation"] with quality score


# ============================================================================
# EXAMPLE 2: TRACKED HTTP CLIENT (Recommended for Production)
# ============================================================================

async def get_national_grid_eso_tracked(lat: float, lon: float):
    """
    Example using TrackedHTTPClient - recommended for production
    
    Gives you explicit control over metadata while still being easy to use.
    """
    
    source_id = "national_grid_eso"
    url = "https://data.nationalgrideso.com/api/data"
    
    # Create tracked client
    client = TrackedHTTPClient(source_id, "National Grid ESO")
    
    try:
        # Make request - automatically tracked
        response, metadata = await client.get(url, params={"lat": lat, "lon": lon})
        
        # Parse response
        data = response.json()
        
        # Process data
        parsed_data = {
            "source": "National Grid ESO",
            "available": True,
            "nearest_connection": {
                "site_name": data.get("name"),
                "distance_km": 2.3,
                "capacity_mw": 132.0
            }
        }
        
        # Validate
        is_valid, errors, quality_score = validate_source_data(source_id, parsed_data)
        
        # Enrich with metadata and validation
        parsed_data = enrich_data_with_metadata(parsed_data, metadata)
        parsed_data = enrich_data_with_validation(parsed_data, is_valid, errors, quality_score)
        
        return parsed_data
        
    except Exception as e:
        print(f"Error fetching National Grid ESO: {e}")
        return None
    finally:
        await client.close()


# ============================================================================
# EXAMPLE 3: MANUAL INTEGRATION (Most Control)
# ============================================================================

async def get_dft_vehicle_licensing_manual():
    """
    Example with manual integration - maximum control
    
    Use this when you need custom logic or special handling.
    """
    
    source_id = "dft_vehicle_licensing"
    source_url = "https://www.gov.uk/dft/stats"
    
    start_time = time.time()
    
    try:
        # Fetch data
        async with httpx.AsyncClient() as client:
            response = await client.get(source_url, timeout=10.0)
            
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Parse data
        data = {
            "source": "DfT Vehicle Licensing Statistics (Q3 2024)",
            "available": True,
            "data_date": "2024-Q3",
            "bevs": 1180000,
            "phevs": 660000,
            "ev_percentage": 4.46,
            "growth_yoy_bev": 38.5
        }
        
        # Create metadata manually
        metadata = create_metadata(
            source_id=source_id,
            source_url=source_url,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
            content=data,
            success=True
        )
        
        # Validate manually
        is_valid, errors, quality_score = validate_source_data(source_id, data)
        
        # Store in database
        store_fetch_metadata(
            source_id=source_id,
            source_url=source_url,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
            content_hash=metadata["content_hash"],
            row_count=metadata["row_count"],
            success=True,
            validation_passed=is_valid,
            validation_errors=[e.to_dict() for e in errors],
            data_quality_score=quality_score,
            data_size_bytes=metadata["data_size_bytes"]
        )
        
        # Enrich data
        data = enrich_data_with_metadata(data, metadata)
        data = enrich_data_with_validation(data, is_valid, errors, quality_score)
        
        return data
        
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Store failure
        store_fetch_metadata(
            source_id=source_id,
            source_url=source_url,
            status_code=0,
            response_time_ms=elapsed_ms,
            content_hash="",
            row_count=0,
            success=False,
            error_message=str(e),
            validation_passed=False,
            data_quality_score=0.0
        )
        
        raise


# ============================================================================
# MIGRATION GUIDE: Updating Existing Functions
# ============================================================================

def migration_example():
    """
    Shows how to migrate existing EVL functions to use foundation
    """
    
    print("BEFORE (v10.1):")
    print("""
    async def get_entsoe_grid_data(country_code: str):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                return parse_response(response)
        except Exception as e:
            logger.error(f"ENTSO-E failed: {e}")
            return None
    """)
    
    print("\nAFTER (with foundation) - Option A - Decorators:")
    print("""
    @track_fetch("entsoe", "ENTSO-E Grid")
    @validate_response("entsoe")
    async def get_entsoe_grid_data(country_code: str):
        # Code unchanged!
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return parse_response(response)
    """)
    
    print("\nAFTER (with foundation) - Option B - TrackedHTTPClient:")
    print("""
    async def get_entsoe_grid_data(country_code: str):
        client = TrackedHTTPClient("entsoe", "ENTSO-E Grid")
        
        try:
            response, metadata = await client.get(url)
            data = parse_response(response)
            
            # Validate
            is_valid, errors, score = validate_source_data("entsoe", data)
            
            # Enrich
            data = enrich_data_with_metadata(data, metadata)
            data = enrich_data_with_validation(data, is_valid, errors, score)
            
            return data
        finally:
            await client.close()
    """)


# ============================================================================
# RUN EXAMPLES
# ============================================================================

async def main():
    """Run all examples"""
    
    print("=" * 70)
    print("EVL Foundation Package - Integration Examples")
    print("=" * 70)
    
    # Example 1: Decorators
    print("\n1️⃣  DECORATOR PATTERN (Easiest)")
    print("-" * 70)
    try:
        result1 = await get_entsoe_with_decorators("UK")
        print(f"✅ Success! Quality score: {result1['_validation']['quality_score']:.2f}")
        print(f"   Metadata: {result1['_metadata']['source_id']}")
        print(f"   Response time: {result1['_metadata']['response_time_ms']:.0f}ms")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Example 2: TrackedHTTPClient
    print("\n2️⃣  TRACKED HTTP CLIENT (Recommended)")
    print("-" * 70)
    try:
        result2 = await get_national_grid_eso_tracked(51.5, -0.1)
        if result2:
            print(f"✅ Success! Quality score: {result2['_validation']['quality_score']:.2f}")
            print(f"   Validation errors: {result2['_validation']['error_count']}")
        else:
            print("❌ No data returned")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Example 3: Manual
    print("\n3️⃣  MANUAL INTEGRATION (Most Control)")
    print("-" * 70)
    try:
        result3 = await get_dft_vehicle_licensing_manual()
        print(f"✅ Success! Quality score: {result3['_validation']['quality_score']:.2f}")
        print(f"   BEVs: {result3['bevs']:,}")
        print(f"   Growth: {result3['growth_yoy_bev']}%")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Migration guide
    print("\n4️⃣  MIGRATION GUIDE")
    print("-" * 70)
    migration_example()
    
    print("\n" + "=" * 70)
    print("✅ All examples complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Choose your integration pattern")
    print("2. Update 2-3 functions in main.py")
    print("3. Test with real API calls")
    print("4. Check evl_foundation.db for stored data")
    print("\nDatabase location: evl_foundation.db (SQLite)")
    print("Query example: sqlite3 evl_foundation.db 'SELECT * FROM fetch_metadata LIMIT 5;'")


if __name__ == "__main__":
    # Initialize database first
    from core.database import init_database
    init_database()
    
    # Run examples
    asyncio.run(main())
