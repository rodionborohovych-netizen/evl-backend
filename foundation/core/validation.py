"""
Metadata tracking for API calls

Provides decorators and utilities to track:
- When data was fetched
- How long it took
- Whether it succeeded
- Content hash (to detect changes)
- Size and row count
"""

import time
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from functools import wraps
import httpx

from .database import store_fetch_metadata


def calculate_content_hash(data: Any) -> str:
    """Calculate SHA256 hash of data"""
    
    if isinstance(data, (dict, list)):
        # Convert to stable JSON string
        content = json.dumps(data, sort_keys=True)
    elif isinstance(data, str):
        content = data
    elif isinstance(data, bytes):
        content = data.decode('utf-8', errors='ignore')
    else:
        content = str(data)
    
    return hashlib.sha256(content.encode()).hexdigest()


def count_rows(data: Any) -> int:
    """Count rows in data"""
    
    if isinstance(data, list):
        return len(data)
    elif isinstance(data, dict):
        # Look for common list keys
        for key in ['items', 'results', 'data', 'records']:
            if key in data and isinstance(data[key], list):
                return len(data[key])
        return 1
    else:
        return 1


def calculate_data_size(data: Any) -> int:
    """Calculate size of data in bytes"""
    
    if isinstance(data, (dict, list)):
        return len(json.dumps(data).encode())
    elif isinstance(data, str):
        return len(data.encode())
    elif isinstance(data, bytes):
        return len(data)
    else:
        return len(str(data).encode())


def create_metadata(
    source_id: str,
    source_url: str,
    status_code: int,
    response_time_ms: float,
    content: Any,
    success: bool = True,
    error_message: str = None,
    row_count: int = None
) -> Dict[str, Any]:
    """Create metadata dictionary for a fetch"""
    
    content_hash = calculate_content_hash(content)
    data_size = calculate_data_size(content)
    
    if row_count is None:
        row_count = count_rows(content)
    
    return {
        "source_id": source_id,
        "source_url": source_url,
        "fetched_at": datetime.utcnow().isoformat(),
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "content_hash": content_hash,
        "data_size_bytes": data_size,
        "row_count": row_count,
        "success": success,
        "error_message": error_message,
        "data_quality": "good" if success else "error"
    }


def enrich_data_with_metadata(data: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Add metadata to data response"""
    
    if isinstance(data, dict):
        data["_metadata"] = metadata
    
    return data


def track_fetch(source_id: str, source_name: str = None):
    """
    Decorator to automatically track API fetch metadata
    
    Usage:
        @track_fetch("entsoe", "ENTSO-E Grid Data")
        async def get_entsoe_data(country_code: str):
            return await fetch_data()
    """
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            source_url = kwargs.get('url', 'unknown')
            
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                elapsed_ms = (time.time() - start_time) * 1000
                
                # Create metadata
                metadata = create_metadata(
                    source_id=source_id,
                    source_url=source_url,
                    status_code=200,
                    response_time_ms=elapsed_ms,
                    content=result,
                    success=True
                )
                
                # Store in database
                store_fetch_metadata(
                    source_id=source_id,
                    source_url=source_url,
                    status_code=200,
                    response_time_ms=elapsed_ms,
                    content_hash=metadata["content_hash"],
                    row_count=metadata["row_count"],
                    success=True,
                    data_size_bytes=metadata["data_size_bytes"]
                )
                
                # Enrich result
                if isinstance(result, dict):
                    result["_metadata"] = metadata
                
                return result
                
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                
                # Store failure metadata
                store_fetch_metadata(
                    source_id=source_id,
                    source_url=source_url,
                    status_code=0,
                    response_time_ms=elapsed_ms,
                    content_hash="",
                    row_count=0,
                    success=False,
                    error_message=str(e),
                    data_quality_score=0.0
                )
                
                raise
        
        return wrapper
    return decorator


class TrackedHTTPClient:
    """
    HTTP client that automatically tracks all requests
    
    Usage:
        client = TrackedHTTPClient("entsoe", "ENTSO-E API")
        response, metadata = await client.get("https://api.example.com")
    """
    
    def __init__(self, source_id: str, source_name: str = None):
        self.source_id = source_id
        self.source_name = source_name or source_id
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get(self, url: str, **kwargs) -> Tuple[httpx.Response, Dict[str, Any]]:
        """GET request with tracking"""
        
        start_time = time.time()
        
        try:
            response = await self.client.get(url, **kwargs)
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Parse content
            try:
                content = response.json()
            except:
                content = response.text
            
            # Create metadata
            metadata = create_metadata(
                source_id=self.source_id,
                source_url=url,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                content=content,
                success=response.status_code == 200
            )
            
            # Store in database
            store_fetch_metadata(
                source_id=self.source_id,
                source_url=url,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                content_hash=metadata["content_hash"],
                row_count=metadata["row_count"],
                success=response.status_code == 200,
                data_size_bytes=metadata["data_size_bytes"]
            )
            
            return response, metadata
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Store failure
            store_fetch_metadata(
                source_id=self.source_id,
                source_url=url,
                status_code=0,
                response_time_ms=elapsed_ms,
                content_hash="",
                row_count=0,
                success=False,
                error_message=str(e),
                data_quality_score=0.0
            )
            
            raise
    
    async def post(self, url: str, **kwargs) -> Tuple[httpx.Response, Dict[str, Any]]:
        """POST request with tracking"""
        
        start_time = time.time()
        
        try:
            response = await self.client.post(url, **kwargs)
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Parse content
            try:
                content = response.json()
            except:
                content = response.text
            
            # Create metadata
            metadata = create_metadata(
                source_id=self.source_id,
                source_url=url,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                content=content,
                success=response.status_code == 200
            )
            
            # Store in database
            store_fetch_metadata(
                source_id=self.source_id,
                source_url=url,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                content_hash=metadata["content_hash"],
                row_count=metadata["row_count"],
                success=response.status_code == 200,
                data_size_bytes=metadata["data_size_bytes"]
            )
            
            return response, metadata
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Store failure
            store_fetch_metadata(
                source_id=self.source_id,
                source_url=url,
                status_code=0,
                response_time_ms=elapsed_ms,
                content_hash="",
                row_count=0,
                success=False,
                error_message=str(e),
                data_quality_score=0.0
            )
            
            raise
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
