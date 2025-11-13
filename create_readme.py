"""
README for EVL Foundation Package
"""

CONTENT = """# 🗃️ EVL Foundation Package

Production-grade data quality infrastructure for EVL v10.1+

## 📋 What's Included

### Core Modules

- **`core/database.py`** - SQLAlchemy models for data tracking
  - FetchMetadata: Track every API call
  - DataContract: Define quality rules
  - SourceHealth: Monitor source status
  - Alert: Track data quality issues
  - ReconciliationCheck: Cross-source validation

- **`core/metadata.py`** - Data provenance tracking
  - `@track_fetch` decorator
  - `TrackedHTTPClient` for automatic tracking
  - Helper functions for metadata management

- **`core/validation.py`** - Data validation framework
  - Data contracts for all 15+ sources
  - `validate_data()` function
  - `@validate_response` decorator
  - Freshness checking

- **`examples.py`** - Working examples
  - 3 different integration patterns
  - Migration guide
  - Best practices

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Dependencies

```bash
pip install sqlalchemy
```

Already have: `fastapi`, `httpx`, `pyyaml`

### Step 2: Initialize Database

```bash
python -c "from core.database import init_database; init_database()"
```

This creates `evl_foundation.db` (SQLite) locally.

### Step 3: Use in Your Code

```python
# Add to your existing function
from core import track_fetch, validate_response

@track_fetch("entsoe", "ENTSO-E Grid")
@validate_response("entsoe")
async def get_entsoe_grid_data(country_code: str):
    # Your existing code unchanged!
    data = await fetch_entsoe(country_code)
    return data
```

**That's it!** Now every call is:
- ✅ Tracked (timing, status, errors)
- ✅ Validated (against data contract)
- ✅ Scored (quality 0-1)

---

## 📊 Features

### 1. Data Provenance Tracking

**Every API call records:**
- Source ID and URL
- Fetch timestamp
- Response time (ms)
- Status code
- Content hash (detect changes)
- Row count
- Validation results
- Quality score

**Example:**
```python
from core import TrackedHTTPClient

client = TrackedHTTPClient("national_grid_eso")
response, metadata = await client.get("https://api.example.com")

print(metadata)
# {
#   "source_id": "national_grid_eso",
#   "fetched_at": "2024-11-12T17:30:00",
#   "status_code": 200,
#   "response_time_ms": 1523.4,
#   "content_hash": "a3f5e9...",
#   "row_count": 245,
#   "data_quality_score": 1.0
# }
```

### 2. Data Validation

**Automatic validation against contracts:**

```python
# Contract defines rules
DATA_CONTRACTS = {
    "entsoe": {
        "required_fields": [
            {"name": "renewable_share", "type": "float", "min": 0, "max": 1}
        ],
        "quality_checks": [
            "renewable_share >= 0 and renewable_share <= 1"
        ]
    }
}

# Validation happens automatically
result = await get_entsoe_data("UK")

if result["_validation"]["passed"]:
    print("✅ Data is good!")
else:
    print("❌ Issues:", result["_validation"]["errors"])
```

### 3. Freshness Monitoring

**Check if data is stale:**

```python
from core import validate_freshness

is_fresh, message = validate_freshness("entsoe", last_fetch_time)

if not is_fresh:
    print(f"⚠️ Data too old: {message}")
    # e.g., "Data stale: 8.5h > 6h SLA"
```

### 4. Quality Scores

**Every response gets a quality score:**

- 1.0 = Perfect (all validations passed)
- 0.7 = Minor issues (1-2 validation errors)
- 0.4 = Moderate issues (3-5 errors)
- 0.1 = Severe issues (6+ errors)
- 0.0 = Failed (unavailable or critical error)

---

## 🔧 Integration Patterns

### Pattern 1: Decorator (Easiest)

```python
@track_fetch("source_id", "Source Name")
@validate_response("source_id")
async def get_data():
    return await fetch_data()
```

**Pros:**
- ✅ Minimal code changes
- ✅ Automatic tracking & validation
- ✅ Works with existing code

**Cons:**
- ⚠️ Less control over metadata

### Pattern 2: TrackedHTTPClient (Recommended)

```python
async def get_data():
    client = TrackedHTTPClient("source_id", "Source Name")
    
    try:
        response, metadata = await client.get(url)
        data = parse_response(response)
        
        # Validate
        is_valid, errors, score = validate_data("source_id", data)
        
        # Add to response
        data["_metadata"] = metadata
        data["_validation"] = {
            "passed": is_valid,
            "errors": errors,
            "quality_score": score
        }
        
        return data
    finally:
        await client.close()
```

**Pros:**
- ✅ Full control over metadata
- ✅ Explicit validation
- ✅ Easy to customize

**Cons:**
- ⚠️ More verbose

### Pattern 3: Manual (Most Control)

```python
async def get_data():
    start = time.time()
    
    try:
        data = await fetch()
        
        # Track manually
        store_fetch_metadata(
            source_id="source_id",
            source_url="https://...",
            status_code=200,
            response_time_ms=(time.time() - start) * 1000,
            content_hash=calculate_content_hash(data),
            row_count=len(data),
            validation_passed=True,
            data_quality_score=1.0
        )
        
        return data
    except Exception as e:
        # Track error
        store_fetch_metadata(...)
        raise
```

**Pros:**
- ✅ Maximum control
- ✅ Custom logic

**Cons:**
- ⚠️ Most verbose
- ⚠️ Easy to forget tracking

---

## 📈 Query Metadata

### Get Recent Fetches

```python
from core import get_recent_fetches

# Last 24 hours
fetches = get_recent_fetches("entsoe", hours=24)

for fetch in fetches:
    print(f"{fetch.fetched_at}: {fetch.status_code} in {fetch.response_time_ms}ms")
```

### Calculate Success Rate

```python
from core import get_session, FetchMetadata
from datetime import datetime, timedelta

session = get_session()

# Last 24 hours
cutoff = datetime.utcnow() - timedelta(hours=24)

total = session.query(FetchMetadata)\\
    .filter(FetchMetadata.source_id == "entsoe")\\
    .filter(FetchMetadata.fetched_at >= cutoff)\\
    .count()

successes = session.query(FetchMetadata)\\
    .filter(FetchMetadata.source_id == "entsoe")\\
    .filter(FetchMetadata.fetched_at >= cutoff)\\
    .filter(FetchMetadata.status_code == 200)\\
    .count()

success_rate = successes / total if total > 0 else 0
print(f"Success rate: {success_rate:.1%}")
```

### Get Quality Trends

```python
from sqlalchemy import func

# Average quality score over time
scores = session.query(
    func.date_trunc('hour', FetchMetadata.fetched_at).label('hour'),
    func.avg(FetchMetadata.data_quality_score).label('avg_quality')
)\\
.filter(FetchMetadata.source_id == "entsoe")\\
.group_by('hour')\\
.all()

for hour, quality in scores:
    print(f"{hour}: {quality:.2f}")
```

---

## 🔍 Data Contracts

### Viewing Contracts

```python
from core import get_contract, get_all_contracts

# Get specific contract
contract = get_contract("entsoe")
print(contract["required_fields"])

# Get all contracts
all_contracts = get_all_contracts()
for source_id, contract in all_contracts.items():
    print(f"{source_id}: {contract['update_frequency']}")
```

### Adding Custom Contract

```python
from core import DATA_CONTRACTS

DATA_CONTRACTS["my_custom_source"] = {
    "source_name": "My Custom API",
    "freshness_sla": {"max_lag_hours": 12},
    "update_frequency": "hourly",
    "required_fields": [
        {"name": "field1", "type": "float", "min": 0, "max": 100},
        {"name": "field2", "type": "str", "not_null": True}
    ],
    "quality_checks": [
        "field1 > 0",
        "field2 is not None"
    ]
}
```

---

## 🗄️ Database Schema

### Tables Created

1. **`fetch_metadata`** - Every API call
2. **`data_contracts`** - Quality rules (future: DB storage)
3. **`source_health`** - Health snapshots
4. **`alerts`** - Data quality alerts
5. **`reconciliation_checks`** - Cross-source validation

### Database Locations

**Local Development:**
```
evl_foundation.db (SQLite in project root)
```

**Production (Railway):**
```
Set DATABASE_URL environment variable to PostgreSQL
Foundation automatically uses it
```

---

## 🚨 Alerts (Coming in Week 3)

Framework is ready, alerting implementation is next phase:

```python
from core import store_alert

store_alert(
    alert_type="source_down",
    source_id="entsoe",
    severity="critical",
    message="ENTSO-E has been down for 30 minutes",
    details={"last_success": "2024-11-12T16:00:00"}
)
```

---

## 📊 Health Monitoring (Coming in Week 2)

```python
from core import SourceHealth

# Store health snapshot
health = SourceHealth(
    source_id="entsoe",
    status="healthy",
    success_rate_24h=0.98,
    avg_response_time_ms=1523.4,
    data_freshness_hours=0.5,
    quality_score=1.0
)

session.add(health)
session.commit()
```

---

## 🧪 Testing

```python
# Test validation
from core import validate_data

test_data = {
    "total_generation_mw": 35000,
    "renewable_share": 0.67,
    "country": "UK"
}

is_valid, errors, score = validate_data("entsoe", test_data)

assert is_valid
assert score == 1.0
assert len(errors) == 0
```

---

## 🗂️ File Structure

```
foundation/
├── core/
│   ├── __init__.py       # Module exports
│   ├── database.py       # SQLAlchemy models
│   ├── metadata.py       # Tracking functions
│   └── validation.py     # Validation logic
├── examples.py           # Integration examples
└── README.md            # This file

Your project:
evl-backend/
├── main.py              # Your FastAPI app
├── foundation/          # Add this folder
├── evl_foundation.db    # Created automatically
└── requirements.txt     # Add: sqlalchemy
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Optional: PostgreSQL (Railway)
DATABASE_URL=postgresql://user:pass@host:5432/db

# If not set, uses SQLite (evl_foundation.db)
```

---

## 🎯 Quick Wins

### 1. See What's Being Tracked (30 seconds)

```python
from core import get_session, FetchMetadata

session = get_session()
recent = session.query(FetchMetadata)\\
    .order_by(FetchMetadata.fetched_at.desc())\\
    .limit(10)\\
    .all()

for fetch in recent:
    print(f"{fetch.source_id}: {fetch.status_code} in {fetch.response_time_ms}ms")
```

### 2. Check Data Quality (1 minute)

```python
from core import get_session, FetchMetadata
from sqlalchemy import func

# Average quality per source
quality = session.query(
    FetchMetadata.source_id,
    func.avg(FetchMetadata.data_quality_score).label('avg_quality')
)\\
.group_by(FetchMetadata.source_id)\\
.all()

for source, score in quality:
    print(f"{source}: {score:.2f}/1.0")
```

### 3. Find Slow Sources (1 minute)

```python
# Average response time per source
speed = session.query(
    FetchMetadata.source_id,
    func.avg(FetchMetadata.response_time_ms).label('avg_ms')
)\\
.group_by(FetchMetadata.source_id)\\
.all()

for source, ms in speed:
    print(f"{source}: {ms:.0f}ms")
```

---

## 🛠 Troubleshooting

### Database not created?

```python
from core.database import init_database
init_database()
```

### Import errors?

```bash
# Make sure you're in the right directory
cd evl-backend

# Install SQLAlchemy
pip install sqlalchemy
```

### Want to reset database?

```bash
rm evl_foundation.db
python -c "from core.database import init_database; init_database()"
```

---

## 📚 Next Steps

1. ✅ **This Week:** Integrate tracking into 3-5 key sources
2. **Week 2:** Build health dashboard (`/api/health/sources`)
3. **Week 3:** Implement alerting system
4. **Week 4:** Add cross-source reconciliation
5. **Week 5:** Automated testing
6. **Week 6:** Production hardening

---

## 💡 Pro Tips

1. **Start with one source** - Don't try to integrate everything at once
2. **Use decorators** - Easiest way to add tracking
3. **Check the database** - SQL queries show what's happening
4. **Validation is optional** - Tracking works without it
5. **Quality scores matter** - 0.7+ is good, <0.5 needs attention

---

## 🤝 Contributing

To add a new data contract:

1. Add to `core/validation.py`:
```python
DATA_CONTRACTS["new_source"] = {
    "source_name": "New Source",
    "freshness_sla": {"max_lag_hours": 24},
    "required_fields": [...],
    "quality_checks": [...]
}
```

2. Use in your code:
```python
@validate_response("new_source")
async def get_new_source_data():
    ...
```

---

**Built with ❤️ for production-grade data quality**

Questions? Check `examples.py` or see the Phase 2 Roadmap!
"""

if __name__ == "__main__":
    with open("/home/claude/foundation/README.md", "w") as f:
        f.write(CONTENT)
    print("✅ README.md created")
