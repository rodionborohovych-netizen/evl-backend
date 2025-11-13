# 🔧 Integration Guide: Adding Foundation to main_v10_1.py

Step-by-step guide to integrate data quality tracking into your existing EVL backend.

## 📋 Overview

This guide shows you how to add production-grade data quality tracking to your EVL v10.1 backend **without breaking existing functionality**.

**Time required:** 30-60 minutes  
**Difficulty:** Easy to Moderate  
**Impact:** High - Get quality scores, tracking, and validation for all API calls

---

## 🎯 What You'll Get

After integration:
- ✅ **Track every API call** (timing, success rate, errors)
- ✅ **Validate data quality** (auto-check against contracts)
- ✅ **Quality scores** (0-1 for each source)
- ✅ **SQLite database** with full history
- ✅ **Ready for monitoring dashboard** (Week 2)

---

## 📦 Step 1: Add Foundation Package (5 minutes)

### 1.1 Copy Foundation to Your Project

```bash
# In your evl-backend directory:
cd /path/to/evl-backend
cp -r /path/to/foundation ./foundation
```

Your structure should look like:
```
evl-backend/
├── main.py (or main_v10_1.py)
├── requirements.txt
├── foundation/        # NEW
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── metadata.py
│   │   └── validation.py
│   ├── examples.py
│   └── README.md
```

### 1.2 Install Dependencies

```bash
pip install sqlalchemy
```

Or add to your `requirements.txt`:
```txt
sqlalchemy>=2.0.0
```

### 1.3 Initialize Database

```bash
python -c "from foundation.core import init_database; init_database()"
```

This creates `evl_foundation.db` in your project root.

---

## 🔨 Step 2: Choose Integration Approach (Pick One)

### Approach A: Decorators (Fastest - 15 minutes)

Add decorators to your existing functions with minimal code changes.

**Best for:** Quick integration, minimal refactoring

### Approach B: TrackedHTTPClient (Recommended - 30 minutes)

Use the TrackedHTTPClient for explicit control.

**Best for:** Production use, explicit metadata handling

### Approach C: Manual (Advanced - 60 minutes)

Manually track and validate each source.

**Best for:** Maximum control, custom logic

**Recommendation:** Start with Approach A (decorators) for 2-3 sources, then decide if you want to migrate to Approach B.

---

## 📝 Step 3A: Integration with Decorators (Easiest)

### 3A.1 Import Foundation

At the top of `main_v10_1.py`, add:

```python
# Add after other imports
from foundation.core import (
    track_fetch,
    validate_response,
    init_database
)

# Initialize database on startup
init_database()
```

### 3A.2 Add to ENTSO-E Function

**BEFORE:**
```python
async def get_entsoe_grid_data(country_code: str = "UK"):
    """Fetch ENTSO-E grid data"""
    
    api_key = os.getenv("ENTSOE_API_KEY")
    
    if not api_key:
        logger.warning("ENTSO-E API key not found")
        return None
    
    # ... rest of function ...
    return data
```

**AFTER:**
```python
@track_fetch("entsoe", "ENTSO-E Grid Data")
@validate_response("entsoe")
async def get_entsoe_grid_data(country_code: str = "UK"):
    """Fetch ENTSO-E grid data"""
    
    api_key = os.getenv("ENTSOE_API_KEY")
    
    if not api_key:
        logger.warning("ENTSO-E API key not found")
        return None
    
    # Code unchanged!
    # ... rest of function ...
    return data
    
    # Now data includes:
    # - data["_metadata"] = {timing, hash, status, ...}
    # - data["_validation"] = {quality_score, errors, ...}
```

### 3A.3 Add to National Grid ESO

```python
@track_fetch("national_grid_eso", "National Grid ESO")
@validate_response("national_grid_eso")
async def get_national_grid_eso_real(lat: float, lon: float):
    # Code unchanged!
    return data
```

### 3A.4 Add to DfT Vehicle Licensing

```python
@track_fetch("dft_vehicle_licensing", "DfT Vehicle Licensing")
@validate_response("dft_vehicle_licensing")
async def get_dft_vehicle_licensing_real():
    # Code unchanged!
    return data
```

### 3A.5 Add to ONS Demographics

```python
@track_fetch("ons_demographics", "ONS Demographics")
@validate_response("ons_demographics")
async def get_ons_real(lat: float, lon: float):
    # Code unchanged!
    return data
```

**That's it! Now test:**

```bash
# Run your backend
uvicorn main_v10_1:app --reload

# Test an endpoint
curl "http://localhost:8000/api/analyze?address=London&country_code=UK"

# Check database
sqlite3 evl_foundation.db "SELECT source_id, status_code, response_time_ms FROM fetch_metadata ORDER BY fetched_at DESC LIMIT 10;"
```

---

## 📝 Step 3B: Integration with TrackedHTTPClient (Recommended)

### 3B.1 Import Foundation

```python
from foundation.core import (
    TrackedHTTPClient,
    validate_source_data,
    enrich_data_with_metadata,
    enrich_data_with_validation,
    init_database
)

init_database()
```

### 3B.2 Update ENTSO-E Function

**BEFORE:**
```python
async def get_entsoe_grid_data(country_code: str = "UK"):
    api_key = os.getenv("ENTSOE_API_KEY")
    
    if not api_key:
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            # ... parse XML ...
            return data
    except Exception as e:
        logger.error(f"ENTSO-E error: {e}")
        return None
```

**AFTER:**
```python
async def get_entsoe_grid_data(country_code: str = "UK"):
    api_key = os.getenv("ENTSOE_API_KEY")
    
    if not api_key:
        return None
    
    # Create tracked client
    client = TrackedHTTPClient("entsoe", "ENTSO-E Grid Data")
    
    try:
        # Make request - automatically tracked
        response, metadata = await client.get(url, params=params)
        
        # Parse response (your existing code)
        data = parse_entsoe_response(response)
        
        # Validate
        is_valid, errors, quality_score = validate_source_data("entsoe", data)
        
        # Enrich with metadata and validation
        data = enrich_data_with_metadata(data, metadata)
        data = enrich_data_with_validation(data, is_valid, errors, quality_score)
        
        return data
        
    except Exception as e:
        logger.error(f"ENTSO-E error: {e}")
        return None
    finally:
        await client.close()
```

### 3B.3 Benefits of TrackedHTTPClient

- ✅ Explicit metadata access
- ✅ Clear validation step
- ✅ Easy to add custom logic
- ✅ Better error handling
- ✅ Production-ready

---

## 🧪 Step 4: Test Your Integration (10 minutes)

### 4.1 Run Examples

```bash
cd foundation
python examples.py
```

Should see:
```
✅ Success! Quality score: 1.00
   Metadata: entsoe
   Response time: 1234ms
```

### 4.2 Test Your Backend

```bash
# Start backend
uvicorn main_v10_1:app --reload

# Test analyze endpoint
curl "http://localhost:8000/api/analyze?address=London&country_code=UK&radius=5"
```

### 4.3 Check Database

```bash
# View recent fetches
sqlite3 evl_foundation.db "SELECT 
    source_id,
    status_code,
    response_time_ms,
    validation_passed,
    data_quality_score
FROM fetch_metadata 
ORDER BY fetched_at DESC 
LIMIT 10;"
```

### 4.4 Verify Response Structure

Your API responses should now include:

```json
{
  "comprehensive_data": {
    "entsoe_grid": {
      "source": "ENTSO-E",
      "renewable_share": 0.673,
      "_metadata": {
        "source_id": "entsoe",
        "fetched_at": "2024-11-12T21:30:00",
        "response_time_ms": 1234,
        "data_quality": "good"
      },
      "_validation": {
        "is_valid": true,
        "quality_score": 1.0,
        "error_count": 0
      }
    }
  }
}
```

---

## 📊 Step 5: Add Quality Dashboard (Optional - 15 minutes)

### 5.1 Add Health Endpoint

Add to `main_v10_1.py`:

```python
from foundation.core import get_session, FetchMetadata
from sqlalchemy import func
from datetime import datetime, timedelta

@app.get("/api/health/sources")
async def get_sources_health():
    """Get health status of all data sources"""
    
    session = get_session()
    
    try:
        # Last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        # Get stats per source
        stats = session.query(
            FetchMetadata.source_id,
            func.count(FetchMetadata.id).label('total_calls'),
            func.sum(case((FetchMetadata.success == True, 1), else_=0)).label('successes'),
            func.avg(FetchMetadata.response_time_ms).label('avg_response_ms'),
            func.avg(FetchMetadata.data_quality_score).label('avg_quality')
        )\
        .filter(FetchMetadata.fetched_at >= cutoff)\
        .group_by(FetchMetadata.source_id)\
        .all()
        
        sources = []
        for stat in stats:
            success_rate = stat.successes / stat.total_calls if stat.total_calls > 0 else 0
            
            sources.append({
                "source_id": stat.source_id,
                "status": "healthy" if success_rate > 0.9 else "degraded" if success_rate > 0.7 else "down",
                "success_rate_24h": success_rate,
                "avg_response_time_ms": round(stat.avg_response_ms, 1),
                "avg_quality_score": round(stat.avg_quality, 2),
                "total_calls_24h": stat.total_calls
            })
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "sources": sources
        }
        
    finally:
        session.close()
```

### 5.2 Test Health Endpoint

```bash
curl http://localhost:8000/api/health/sources
```

Expected response:
```json
{
  "timestamp": "2024-11-12T21:30:00",
  "sources": [
    {
      "source_id": "entsoe",
      "status": "healthy",
      "success_rate_24h": 0.98,
      "avg_response_time_ms": 1523.4,
      "avg_quality_score": 1.0,
      "total_calls_24h": 24
    },
    ...
  ]
}
```

---

## 🎯 Success Checklist

After integration, verify:

- [ ] Database created (`evl_foundation.db` exists)
- [ ] At least 3 sources decorated with `@track_fetch`
- [ ] At least 3 sources decorated with `@validate_response`
- [ ] Backend runs without errors
- [ ] API responses include `_metadata` and `_validation`
- [ ] Database has fetch records
- [ ] `/api/health/sources` endpoint works (optional)

---

## 🔍 Troubleshooting

### Issue: "Module not found: foundation"

**Fix:**
```bash
# Make sure foundation is in your project directory
ls -la foundation/

# If missing, copy it:
cp -r /path/to/foundation ./
```

### Issue: "Database not created"

**Fix:**
```python
from foundation.core import init_database
init_database()
```

### Issue: "Validation errors on good data"

**Cause:** Data structure doesn't match contract

**Fix:** Check your data structure matches the contract in `foundation/core/validation.py`. Example:

```python
# If getting errors on "renewable_share"
# Check that data has this exact key name:
data = {
    "renewable_share": 0.673,  # Must be named exactly this
    # not "renewable_pct" or "renewables"
}
```

### Issue: "_metadata not appearing in response"

**Cause:** Decorator not applied or function not returning dict

**Fix:**
```python
# Make sure function returns a dict
@track_fetch("source_id")
async def get_data():
    data = {...}  # Must be dict
    return data   # Don't return None
```

---

## 📈 Next Steps (Week 2)

After Week 1 integration:

1. **Build monitoring dashboard** - Visual health status
2. **Add alerting** - Get notified of issues
3. **Implement caching** - Reduce repeated API calls
4. **Add reconciliation** - Cross-validate sources

See `PHASE_2_ROADMAP.md` for full plan.

---

## 💡 Pro Tips

1. **Start small** - Integrate 2-3 sources first, then expand
2. **Check logs** - Railway logs show all tracking activity
3. **Use quality scores** - Filter data with score < 0.7
4. **Monitor database size** - Rotate old records after 30 days
5. **Deploy to Railway** - Works same as local

---

## 🚀 Deploy to Railway

Foundation works on Railway without changes:

1. **Copy foundation to repo:**
   ```bash
   git add foundation/
   git commit -m "Add data quality foundation"
   git push
   ```

2. **Railway auto-detects dependencies** from `requirements.txt`

3. **Database:** Railway creates PostgreSQL automatically (just set `DATABASE_URL`)

4. **Test:**
   ```bash
   curl https://your-app.up.railway.app/api/health/sources
   ```

---

**Questions?** Check `foundation/README.md` or `foundation/examples.py`

**Ready to integrate?** Start with Step 1! 🎯
