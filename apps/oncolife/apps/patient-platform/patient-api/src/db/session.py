"""
Database Session Management for OncoLife Patient API.

This module handles:
- Database engine creation with connection pooling
- Session factory configuration
- FastAPI dependency injection for database sessions
- Connection health checking

Features:
- Automatic connection pooling and recycling
- SSL support for cloud databases (AWS RDS)
- Proper session lifecycle management
- Support for multiple databases (patient, doctor)

Usage:
    from db import get_patient_db
    
    @app.get("/patients")
    async def get_patients(db: Session = Depends(get_patient_db)):
        patients = db.query(Patient).all()
        return patients
"""

from typing import Generator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from core import settings, get_logger

logger = get_logger(__name__)


# =============================================================================
# ENGINE CONFIGURATION
# =============================================================================

def create_db_engine(database_url: str, db_name: str):
    """
    Create a SQLAlchemy engine with production-ready configuration.
    
    Features:
    - Connection pooling for efficiency
    - Automatic connection recycling
    - SSL support for cloud databases
    - Keepalive for long-running connections
    
    Args:
        database_url: PostgreSQL connection URL
        db_name: Identifier for logging purposes
    
    Returns:
        SQLAlchemy Engine instance
    """
    logger.info(
        f"Creating database engine",
        extra={"database": db_name}
    )
    
    # Configure SSL mode based on environment
    # Always require SSL for cloud databases (Neon, AWS RDS)
    # Only disable for truly local Docker/localhost PostgreSQL
    is_localhost = settings.patient_db_host and (
        'localhost' in settings.patient_db_host or 
        '127.0.0.1' in settings.patient_db_host
    )
    ssl_mode = "disable" if is_localhost else "require"
    
    return create_engine(
        database_url,
        # Connection pool settings
        poolclass=QueuePool,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,  # Verify connections before use
        
        # Connection arguments for PostgreSQL
        connect_args={
            "sslmode": ssl_mode,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
            "connect_timeout": 10,
            "application_name": settings.app_name,
        },
        
        # Echo SQL in debug mode
        echo=settings.debug and settings.is_development,
    )


# =============================================================================
# PATIENT DATABASE
# =============================================================================

# Patient database engine (created lazily)
_patient_engine = None
PatientSessionLocal: Optional[sessionmaker] = None


def _get_patient_engine():
    """Get or create patient database engine."""
    global _patient_engine, PatientSessionLocal
    
    if _patient_engine is None:
        if not settings.patient_database_url:
            raise RuntimeError(
                "Patient database is not configured. "
                "Please check your environment variables: "
                "PATIENT_DB_USER, PATIENT_DB_PASSWORD, PATIENT_DB_HOST, "
                "PATIENT_DB_PORT, PATIENT_DB_NAME"
            )
        
        _patient_engine = create_db_engine(
            settings.patient_database_url,
            "patient_db"
        )
        PatientSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_patient_engine
        )
    
    return _patient_engine


def get_patient_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a patient database session.
    
    Yields a session and ensures proper cleanup after request completion.
    The session is automatically committed if no exceptions occur,
    and rolled back if an exception is raised.
    
    Yields:
        SQLAlchemy Session for patient database
    
    Usage:
        @app.get("/patients/{patient_id}")
        async def get_patient(
            patient_id: UUID,
            db: Session = Depends(get_patient_db)
        ):
            patient = db.query(Patient).filter_by(uuid=patient_id).first()
            return patient
    """
    _get_patient_engine()  # Ensure engine is created
    
    if PatientSessionLocal is None:
        raise RuntimeError("Patient database session factory not initialized")
    
    db = PatientSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# =============================================================================
# DOCTOR DATABASE
# =============================================================================

# Doctor database engine (created lazily)
_doctor_engine = None
DoctorSessionLocal: Optional[sessionmaker] = None


def _get_doctor_engine():
    """Get or create doctor database engine."""
    global _doctor_engine, DoctorSessionLocal
    
    if _doctor_engine is None:
        if not settings.doctor_database_url:
            raise RuntimeError(
                "Doctor database is not configured. "
                "Please check your environment variables: "
                "DOCTOR_DB_USER, DOCTOR_DB_PASSWORD, DOCTOR_DB_HOST, "
                "DOCTOR_DB_PORT, DOCTOR_DB_NAME"
            )
        
        _doctor_engine = create_db_engine(
            settings.doctor_database_url,
            "doctor_db"
        )
        DoctorSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_doctor_engine
        )
    
    return _doctor_engine


def get_doctor_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a doctor database session.
    
    Yields a session and ensures proper cleanup after request completion.
    
    Yields:
        SQLAlchemy Session for doctor database
    
    Usage:
        @app.get("/doctors/{doctor_id}")
        async def get_doctor(
            doctor_id: UUID,
            db: Session = Depends(get_doctor_db)
        ):
            doctor = db.query(Doctor).filter_by(uuid=doctor_id).first()
            return doctor
    """
    _get_doctor_engine()  # Ensure engine is created
    
    if DoctorSessionLocal is None:
        raise RuntimeError("Doctor database session factory not initialized")
    
    db = DoctorSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# =============================================================================
# HEALTH CHECKS
# =============================================================================

def check_patient_db_health() -> dict:
    """
    Check if patient database connection is healthy.
    
    Returns:
        Dict with status and latency information
    """
    import time
    start = time.perf_counter()
    
    try:
        engine = _get_patient_engine()
        with engine.connect() as conn:
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


def check_doctor_db_health() -> dict:
    """
    Check if doctor database connection is healthy.
    
    Returns:
        Dict with status and latency information
    """
    import time
    start = time.perf_counter()
    
    try:
        engine = _get_doctor_engine()
        with engine.connect() as conn:
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





