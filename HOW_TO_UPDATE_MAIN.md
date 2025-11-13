# 🔧 How to Update main_v10_1.py with Foundation Package

## Step-by-Step Integration Guide

This guide shows **exactly** what to add and where in your `main_v10_1.py` file.

**Time:** 15-30 minutes  
**Difficulty:** Easy  

---

## 📋 Prerequisites

1. Copy `foundation/` folder to your `evl-backend` directory
2. Install SQLAlchemy: `pip install sqlalchemy`

Your structure should be:
```
evl-backend/
├── main_v10_1.py       # Your existing file
├── foundation/         # NEW - Copy this here
│   └── core/
└── requirements.txt
```

---

## ✏️ Changes to Make

### STEP 1: Add Imports (Line ~20)

**Find this section (around line 20):**
```python
import logging
import xml.etree.ElementTree as ET
import csv
import io

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

**Add AFTER the imports, BEFORE "# Setup logging":**
```python
import logging
import xml.etree.ElementTree as ET
import csv
import io

# ⭐ NEW: Import Foundation Package
from foundation.core import (
    track_fetch,
    validate_response,
    init_database
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

---

### STEP 2: Initialize Database on Startup (Line ~25)

**Find this section (around line 25):**
```python
app = FastAPI(title="EVL v10.1 - Real API Integrations")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
```

**Add AFTER creating the app:**
```python
app = FastAPI(title="EVL v10.1 - Real API Integrations")

# ⭐ NEW: Initialize data quality database
init_database()
logger.info("✅ Data quality tracking initialized")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
```

---

### STEP 3: Update ENTSO-E Function (Line ~57)

**Find this function (around line 57):**
```python
async def get_entsoe_grid_data(country_code: str) -> Dict[str, Any]:
    """
    REAL ENTSO-E Transparency Platform integration
    Provides: actual grid load, generation mix, renewable share
    """
```

**Add decorators BEFORE the function:**
```python
# ⭐ NEW: Add tracking and validation
@track_fetch("entsoe", "ENTSO-E Grid Data")
@validate_response("entsoe")
async def get_entsoe_grid_data(country_code: str) -> Dict[str, Any]:
    """
    REAL ENTSO-E Transparency Platform integration
    Provides: actual grid load, generation mix, renewable share
    """
```

**That's it for this function! No other changes needed.**

---

### STEP 4: Update National Grid ESO Function (Line ~201)

**Find this function (around line 201):**
```python
async def get_national_grid_eso_real(lat: float, lon: float) -> Dict[str, Any]:
    """
    REAL National Grid ESO Connection Queue
```

**Add decorators BEFORE the function:**
```python
# ⭐ NEW: Add tracking and validation
@track_fetch("national_grid_eso", "National Grid ESO")
@validate_response("national_grid_eso")
async def get_national_grid_eso_real(lat: float, lon: float) -> Dict[str, Any]:
    """
    REAL National Grid ESO Connection Queue
```

---

### STEP 5: Update DfT Vehicle Licensing Function (Line ~296)

**Find this function (around line 296):**
```python
async def get_dft_vehicle_licensing_real() -> Dict[str, Any]:
    """
    REAL DfT Vehicle Licensing Statistics
```

**Add decorators BEFORE the function:**
```python
# ⭐ NEW: Add tracking and validation
@track_fetch("dft_vehicle_licensing", "DfT Vehicle Licensing")
@validate_response("dft_vehicle_licensing")
async def get_dft_vehicle_licensing_real() -> Dict[str, Any]:
    """
    REAL DfT Vehicle Licensing Statistics
```

---

### STEP 6: Update ONS Demographics Function (Line ~373)

**Find this function (around line 373):**
```python
async def get_ons_real(lat: float, lon: float) -> Dict[str, Any]:
    """
    REAL ONS data via postcodes.io
```

**Add decorators BEFORE the function:**
```python
# ⭐ NEW: Add tracking and validation
@track_fetch("ons_demographics", "ONS Demographics")
@validate_response("ons_demographics")
async def get_ons_real(lat: float, lon: float) -> Dict[str, Any]:
    """
    REAL ONS data via postcodes.io
```

---

### STEP 7 (Optional): Update OpenChargeMap Function (Line ~589)

**Find this function (around line 589):**
```python
async def get_openchargemap_data(lat: float, lon: float, radius: int) -> Dict[str, Any]:
    """Get nearby charging stations from OpenChargeMap"""
```

**Add decorators BEFORE the function:**
```python
# ⭐ NEW: Add tracking and validation
@track_fetch("openchargemap", "OpenChargeMap")
@validate_response("openchargemap")
async def get_openchargemap_data(lat: float, lon: float, radius: int) -> Dict[str, Any]:
    """Get nearby charging stations from OpenChargeMap"""
```

---

### STEP 8 (Optional): Update UK DfT Traffic Function (Line ~561)

**Find this function (around line 561):**
```python
async def get_uk_dft_traffic(lat: float, lon: float) -> Dict[str, Any]:
    """Get real UK DfT traffic counts"""
```

**Add decorators BEFORE the function:**
```python
# ⭐ NEW: Add tracking and validation
@track_fetch("dft_traffic", "UK DfT Traffic")
@validate_response("dft_traffic")
async def get_uk_dft_traffic(lat: float, lon: float) -> Dict[str, Any]:
    """Get real UK DfT traffic counts"""
```

---

## 🧪 Testing Your Changes

### 1. Check Syntax

```bash
python -m py_compile main_v10_1.py
```

Should show no errors.

### 2. Start Backend

```bash
uvicorn main_v10_1:app --reload
```

**Look for this in startup logs:**
```
INFO:     ✅ Data quality tracking initialized
INFO:     Application startup complete.
```

### 3. Test Endpoint

```bash
curl "http://localhost:8000/api/analyze?address=London&country_code=UK&radius=5"
```

### 4. Check Response Structure

Response should now include `_metadata` and `_validation`:

```json
{
  "comprehensive_data": {
    "entsoe_grid": {
      "source": "ENTSO-E",
      "renewable_share": 0.673,
      "_metadata": {
        "source_id": "entsoe",
        "fetched_at": "2024-11-12T22:00:00",
        "status_code": 200,
        "response_time_ms": 1234.5,
        "content_hash": "a3f5e9...",
        "data_quality": "good"
      },
      "_validation": {
        "is_valid": true,
        "quality_score": 1.0,
        "error_count": 0,
        "warning_count": 0,
        "errors": []
      }
    }
  }
}
```

### 5. Check Database

```bash
# Should exist
ls -la evl_foundation.db

# Should have data
sqlite3 evl_foundation.db "SELECT source_id, status_code, response_time_ms FROM fetch_metadata ORDER BY fetched_at DESC LIMIT 5;"
```

Expected output:
```
entsoe|200|1234.5
national_grid_eso|200|2345.6
dft_vehicle_licensing|200|567.8
ons_demographics|200|891.2
openchargemap|200|1122.3
```

---

## 📊 Verify It's Working

### Check Quality Scores

```bash
sqlite3 evl_foundation.db "SELECT 
    source_id, 
    COUNT(*) as calls,
    AVG(data_quality_score) as avg_quality,
    AVG(response_time_ms) as avg_response_ms
FROM fetch_metadata 
GROUP BY source_id;"
```

Expected output:
```
entsoe|5|1.0|1234.5
national_grid_eso|5|1.0|2345.6
dft_vehicle_licensing|5|1.0|567.8
ons_demographics|5|0.9|891.2
```

### Check Success Rate

```bash
sqlite3 evl_foundation.db "SELECT 
    source_id,
    AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
FROM fetch_metadata 
GROUP BY source_id;"
```

Should show >0.95 for healthy sources.

---

## 🚨 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'foundation'"

**Fix:**
```bash
# Make sure foundation is in your project directory
ls -la foundation/
# Should show: core/ folder

# If missing, copy it:
cp -r /path/to/outputs/foundation ./
```

### Error: "ModuleNotFoundError: No module named 'sqlalchemy'"

**Fix:**
```bash
pip install sqlalchemy
```

### Error: Function returns None, no _metadata added

**Cause:** Function must return a dictionary, not None

**Fix:** Check that your function always returns a dict:
```python
@track_fetch("source_id", "Source")
async def get_data():
    if error:
        return {"available": False}  # Return dict, not None
    return data  # Return dict
```

### Decorators don't seem to work

**Check decorator order:**
```python
# ✅ Correct order
@track_fetch("source_id", "Source")
@validate_response("source_id")
async def get_data():
    pass

# ❌ Wrong - decorators in wrong order
@validate_response("source_id")
@track_fetch("source_id", "Source")
async def get_data():
    pass
```

### Validation always shows errors

**Cause:** Data structure doesn't match contract

**Check contract:**
```python
from foundation.core import get_contract
print(get_contract("entsoe"))
```

**Fix:** Ensure your data has the exact field names:
```python
# ✅ Correct
data = {
    "renewable_share": 0.673,  # Exact name from contract
    "total_generation_mw": 35420.0
}

# ❌ Wrong
data = {
    "renewable_pct": 0.673,  # Wrong field name
    "generation": 35420.0
}
```

---

## 📈 What You Should See After Integration

### In API Response:
- Every data source has `_metadata` section
- Every data source has `_validation` section  
- Quality scores present (0.0 to 1.0)
- Response times tracked

### In Database:
- `evl_foundation.db` file exists
- Multiple sources tracked
- Quality scores logged
- Success/failure tracked

### In Logs:
```
INFO:     ✅ Data quality tracking initialized
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## 🎯 Success Checklist

After making these changes:

- [ ] Imports added at top
- [ ] `init_database()` called on startup
- [ ] 4+ functions have `@track_fetch` decorator
- [ ] 4+ functions have `@validate_response` decorator
- [ ] Backend starts without errors
- [ ] Database file created
- [ ] API responses include `_metadata` and `_validation`
- [ ] Quality scores are reasonable (>0.7)
- [ ] Database has records from multiple sources

---

## 🚀 What's Next?

**After integration works:**

1. **Test thoroughly** - Make 10+ API calls to different locations
2. **Check quality** - Query database for insights
3. **Add health endpoint** - See foundation/INTEGRATION_GUIDE_MAIN.md section 5.1
4. **Deploy to Railway** - Just push to git, Railway auto-deploys
5. **Week 2** - Build monitoring dashboard

---

## 💡 Pro Tips

1. **Start with 2-3 functions first** - Don't do all at once
2. **Test after each function** - Easier to debug
3. **Check logs** - Shows what's being tracked
4. **Query database often** - See your data quality improving
5. **Quality score < 0.7?** - Investigate what's wrong with data

---

## 🔗 Related Docs

- **QUICK_START.md** - Overview of foundation package
- **INTEGRATION_GUIDE_MAIN.md** - Detailed integration patterns
- **foundation/README.md** - Complete API reference
- **foundation/examples.py** - Working code examples

---

## ✅ Summary

**What you changed:**
1. Added 3 import lines at top
2. Added 1 line to initialize database
3. Added 2 lines (decorators) before 4-6 functions

**Total changes:** ~15 lines of code

**What you got:**
- Full API tracking
- Data validation
- Quality scoring
- Database history
- Production-ready monitoring

**Not bad for 15 lines! 🎉**
