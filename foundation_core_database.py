"""
Database models for EVL data quality tracking

Uses SQLAlchemy ORM to track:
- API fetch metadata (timing, status, errors)
- Data validation results
- Source health over time
- Alerts and incidents
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import os

Base = declarative_base()


class FetchMetadata(Base):
    """Track every API call made to external sources"""
    
    __tablename__ = "fetch_metadata"
    
    id = Column(Integer, primary_key=True)
    source_id = Column(String(50), nullable=False, index=True)
    source_name = Column(String(100))
    source_url = Column(String(500))
    
    # Timing
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    response_time_ms = Column(Float)
    
    # Status
    status_code = Column(Integer)
    success = Column(Boolean)
    error_message = Column(Text)
    
    # Content
    content_hash = Column(String(64))  # SHA256 hash
    data_size_bytes = Column(Integer)
    row_count = Column(Integer)
    
    # Validation
    validation_passed = Column(Boolean)
    validation_errors = Column(JSON)
    data_quality_score = Column(Float)  # 0-1
    
    # Metadata
    version = Column(String(20), default="10.1")
    
    def __repr__(self):
        return f"<FetchMetadata({self.source_id} at {self.fetched_at})>"


class DataContract(Base):
    """Define expected schema and quality rules for each source"""
    
    __tablename__ = "data_contracts"
    
    id = Column(Integer, primary_key=True)
    source_id = Column(String(50), unique=True, nullable=False)
    source_name = Column(String(100))
    
    # Freshness SLA
    max_lag_hours = Column(Float)
    update_frequency = Column(String(50))  # "realtime", "hourly", "daily", "quarterly"
    
    # Schema definition
    required_fields = Column(JSON)  # List of field definitions
    optional_fields = Column(JSON)
    
    # Quality rules
    quality_checks = Column(JSON)  # List of validation expressions
    
    # Status
    active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<DataContract({self.source_id})>"


class SourceHealth(Base):
    """Track health metrics for each data source over time"""
    
    __tablename__ = "source_health"
    
    id = Column(Integer, primary_key=True)
    source_id = Column(String(50), nullable=False, index=True)
    
    # Snapshot time
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Status
    status = Column(String(20))  # "healthy", "degraded", "down"
    
    # Metrics
    success_rate_24h = Column(Float)
    avg_response_time_ms = Column(Float)
    data_freshness_hours = Column(Float)
    quality_score = Column(Float)
    
    # Details
    last_success = Column(DateTime)
    last_failure = Column(DateTime)
    consecutive_failures = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<SourceHealth({self.source_id}: {self.status})>"


class Alert(Base):
    """Track data quality alerts and incidents"""
    
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True)
    alert_type = Column(String(50), nullable=False)  # "source_down", "validation_failure", "staleness"
    source_id = Column(String(50), index=True)
    
    # Alert details
    severity = Column(String(20))  # "info", "warning", "error", "critical"
    message = Column(Text)
    details = Column(JSON)
    
    # Status
    status = Column(String(20), default="open")  # "open", "acknowledged", "resolved"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime)
    
    def __repr__(self):
        return f"<Alert({self.alert_type} for {self.source_id})>"


class ReconciliationCheck(Base):
    """Track cross-source data reconciliation results"""
    
    __tablename__ = "reconciliation_checks"
    
    id = Column(Integer, primary_key=True)
    check_type = Column(String(50), nullable=False)  # "charger_count", "ev_stock", etc.
    
    # Sources compared
    sources = Column(JSON)  # List of source IDs
    
    # Results
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    agreement_score = Column(Float)  # 0-1
    discrepancies = Column(JSON)
    
    # Status
    passed = Column(Boolean)
    notes = Column(Text)
    
    def __repr__(self):
        return f"<ReconciliationCheck({self.check_type} at {self.checked_at})>"


# Database connection management

_engine = None
_SessionLocal = None


def get_engine():
    """Get or create database engine"""
    global _engine
    
    if _engine is None:
        # Use PostgreSQL if DATABASE_URL is set (Railway), otherwise SQLite
        database_url = os.getenv("DATABASE_URL")
        
        if database_url:
            # PostgreSQL
            _engine = create_engine(database_url)
        else:
            # SQLite (local development)
            _engine = create_engine("sqlite:///evl_foundation.db", echo=False)
    
    return _engine


def get_session_local():
    """Get session factory"""
    global _SessionLocal
    
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return _SessionLocal


def get_session() -> Session:
    """Get a database session"""
    SessionLocal = get_session_local()
    return SessionLocal()


def init_database():
    """Initialize database tables"""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully")


# Convenience functions

def store_fetch_metadata(
    source_id: str,
    source_url: str,
    status_code: int,
    response_time_ms: float,
    content_hash: str,
    row_count: int = 0,
    success: bool = True,
    error_message: str = None,
    validation_passed: bool = True,
    validation_errors: list = None,
    data_quality_score: float = 1.0,
    data_size_bytes: int = 0
):
    """Store API fetch metadata in database"""
    
    session = get_session()
    
    try:
        metadata = FetchMetadata(
            source_id=source_id,
            source_url=source_url,
            status_code=status_code,
            response_time_ms=response_time_ms,
            content_hash=content_hash,
            row_count=row_count,
            success=success,
            error_message=error_message,
            validation_passed=validation_passed,
            validation_errors=validation_errors,
            data_quality_score=data_quality_score,
            data_size_bytes=data_size_bytes
        )
        
        session.add(metadata)
        session.commit()
        
    except Exception as e:
        session.rollback()
        print(f"Error storing metadata: {e}")
    finally:
        session.close()


def get_recent_fetches(source_id: str, limit: int = 10):
    """Get recent fetch metadata for a source"""
    
    session = get_session()
    
    try:
        fetches = session.query(FetchMetadata)\
            .filter(FetchMetadata.source_id == source_id)\
            .order_by(FetchMetadata.fetched_at.desc())\
            .limit(limit)\
            .all()
        
        return fetches
        
    finally:
        session.close()


def store_alert(
    alert_type: str,
    source_id: str,
    severity: str,
    message: str,
    details: dict = None
):
    """Store an alert"""
    
    session = get_session()
    
    try:
        alert = Alert(
            alert_type=alert_type,
            source_id=source_id,
            severity=severity,
            message=message,
            details=details
        )
        
        session.add(alert)
        session.commit()
        
    except Exception as e:
        session.rollback()
        print(f"Error storing alert: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    # Initialize database when run directly
    init_database()
