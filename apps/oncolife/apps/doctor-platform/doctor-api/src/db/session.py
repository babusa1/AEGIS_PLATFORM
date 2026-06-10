"""
Database Session Management - Doctor API
========================================

This module provides database connection management:
- Engine creation for doctor and patient databases
- Session factories
- FastAPI dependency injection for database sessions

The doctor platform has access to TWO databases:
1. Doctor DB: Full read/write access for staff/clinic data
2. Patient DB: Read-only access for viewing patient information

Usage:
    from db.session import get_doctor_db, get_patient_db
    
    @router.get("/staff")
    async def get_staff(db: Session = Depends(get_doctor_db)):
        ...
"""

from typing import Generator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Engine Creation
# =============================================================================

def create_db_engine(database_url: Optional[str], db_name: str) -> Optional[Engine]:
    """
    Create a SQLAlchemy engine for the given database URL.
    
    Args:
        database_url: The database connection URL
        db_name: Name of the database (for logging)
        
    Returns:
        SQLAlchemy Engine or None if URL is not configured
    """
    if not database_url:
        logger.warning(f"{db_name} database URL is not configured")
        return None
    
    try:
        engine = create_engine(
            database_url,
            pool_pre_ping=True,  # Verify connections before use
            pool_size=5,         # Maximum number of persistent connections
            max_overflow=10,     # Additional connections when pool is full
            pool_recycle=3600,   # Recycle connections after 1 hour
            echo=settings.debug,  # Log SQL in debug mode
        )
        logger.info(f"{db_name} database engine created successfully")
        return engine
    except Exception as e:
        logger.error(f"Failed to create {db_name} database engine: {e}")
        raise


# Create database engines
doctor_engine = create_db_engine(settings.doctor_database_url, "Doctor")
patient_engine = create_db_engine(settings.patient_database_url, "Patient")


# =============================================================================
# Session Factories
# =============================================================================

# Session factory for doctor database
DoctorSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=doctor_engine,
) if doctor_engine else None

# Session factory for patient database (read-only access)
PatientSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=patient_engine,
) if patient_engine else None


# =============================================================================
# Dependency Injection
# =============================================================================

def get_doctor_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a doctor database session.
    
    The session is automatically closed when the request completes,
    and any uncommitted changes are rolled back.
    
    Usage:
        @router.post("/clinics")
        async def create_clinic(
            request: CreateClinicRequest,
            db: Session = Depends(get_doctor_db)
        ):
            ...
    
    Yields:
        SQLAlchemy Session for the doctor database
        
    Raises:
        RuntimeError: If doctor database is not configured
    """
    if DoctorSessionLocal is None:
        logger.error("Doctor database is not configured")
        raise RuntimeError(
            "Doctor database is not configured. "
            "Please check your environment variables."
        )
    
    db = DoctorSessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error, rolling back: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def get_patient_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a patient database session.
    
    This provides READ-ONLY access to patient data for doctors.
    The session is automatically closed when the request completes.
    
    Usage:
        @router.get("/patients/{patient_id}")
        async def get_patient(
            patient_id: str,
            db: Session = Depends(get_patient_db)
        ):
            ...
    
    Yields:
        SQLAlchemy Session for the patient database
        
    Raises:
        RuntimeError: If patient database is not configured
    """
    if PatientSessionLocal is None:
        logger.error("Patient database is not configured")
        raise RuntimeError(
            "Patient database is not configured. "
            "Please check your environment variables."
        )
    
    db = PatientSessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error, rolling back: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# =============================================================================
# Utilities
# =============================================================================

def verify_database_connections() -> dict:
    """
    Verify that database connections are working.
    
    Returns:
        Dictionary with connection status for each database
    """
    status = {
        "doctor_db": False,
        "patient_db": False,
    }
    
    if doctor_engine:
        try:
            with doctor_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()
            status["doctor_db"] = True
            logger.info("Doctor database connection verified")
        except Exception as e:
            logger.error(f"Doctor database connection failed: {e}")
    
    if patient_engine:
        try:
            with patient_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()
            status["patient_db"] = True
            logger.info("Patient database connection verified")
        except Exception as e:
            logger.error(f"Patient database connection failed: {e}")
    
    return status


def check_doctor_db_health() -> dict:
    """
    Check doctor database connection health with latency.
    
    Returns:
        Dict with status and latency information
    """
    import time
    start = time.perf_counter()
    
    if not doctor_engine:
        return {"status": "not_configured"}
    
    try:
        with doctor_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "status": "ok",
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        logger.error(f"Doctor database health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


def check_patient_db_health() -> dict:
    """
    Check patient database connection health with latency.
    
    Returns:
        Dict with status and latency information
    """
    import time
    start = time.perf_counter()
    
    if not patient_engine:
        return {"status": "not_configured"}
    
    try:
        with patient_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "status": "ok",
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        logger.error(f"Patient database health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
        }





