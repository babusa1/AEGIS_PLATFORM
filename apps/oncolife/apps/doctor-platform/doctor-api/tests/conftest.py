"""
================================================================================
OncoLife Doctor API - Test Fixtures
================================================================================

Module:         conftest.py
Description:    Shared pytest fixtures for Doctor API tests. Provides test
                database sessions, mock authentication, and sample data factories.

Created:        2026-01-05
Modified:       2026-01-16
Author:         Naveen Babu S A
Version:        2.1.0

Fixtures Provided:
    - db_session: In-memory SQLite database session
    - client: Authenticated test client
    - unauthenticated_client: Test client without auth
    - test_physician_uuid: Consistent test physician ID
    - sample_clinic_data: Sample clinic registration data
    - sample_staff_data: Sample staff member data

Usage:
    def test_my_feature(client: TestClient):
        response = client.get("/api/v1/dashboard")
        assert response.status_code == 200

Copyright:
    (c) 2026 OncoLife Health Technologies. All rights reserved.
================================================================================
"""

import os
import sys
from typing import Generator, Dict, Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app
from db.base import Base
from db.database import get_doctor_db_session, get_patient_db_session
from api.deps import get_current_user, TokenData


# =============================================================================
# Database Fixtures
# =============================================================================

# Use in-memory SQLite for tests (fast, isolated)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Creates a fresh database session for each test.
    Tables are created before the test and dropped after.
    """
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


# =============================================================================
# Authentication Fixtures
# =============================================================================

@pytest.fixture
def test_physician_uuid() -> str:
    """Returns a consistent test physician UUID."""
    return "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def test_token_data(test_physician_uuid: str) -> TokenData:
    """Returns mock token data for authentication."""
    return TokenData(
        sub=test_physician_uuid,
        email="dr.test@oncolife.com"
    )


@pytest.fixture
def mock_current_user(test_token_data: TokenData):
    """
    Returns a dependency override that bypasses JWT validation.
    """
    def _mock_current_user():
        return test_token_data
    return _mock_current_user


# =============================================================================
# Test Client Fixtures
# =============================================================================

@pytest.fixture
def client(db_session: Session, mock_current_user) -> Generator[TestClient, None, None]:
    """
    Creates a FastAPI test client with overridden dependencies.
    - Database: Uses test SQLite database
    - Auth: Uses mock authentication (no JWT required)
    """
    # Override dependencies
    app.dependency_overrides[get_doctor_db_session] = lambda: db_session
    app.dependency_overrides[get_patient_db_session] = lambda: db_session  # Same for tests
    app.dependency_overrides[get_current_user] = mock_current_user
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Creates a test client without authentication override.
    Useful for testing auth-required endpoints return 401.
    """
    app.dependency_overrides[get_doctor_db_session] = lambda: db_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# =============================================================================
# Sample Data Factories
# =============================================================================

@pytest.fixture
def sample_clinic_data() -> Dict[str, Any]:
    """Returns sample clinic data."""
    return {
        "name": "Test Oncology Clinic",
        "address": "123 Medical Center Dr",
        "city": "San Francisco",
        "state": "CA",
        "zip_code": "94102",
        "phone": "+1-415-555-0100"
    }


@pytest.fixture
def sample_staff_data(test_physician_uuid: str) -> Dict[str, Any]:
    """Returns sample staff member data."""
    return {
        "email": "nurse.test@oncolife.com",
        "first_name": "Test",
        "last_name": "Nurse",
        "role": "nurse",
        "physician_id": test_physician_uuid
    }


@pytest.fixture
def sample_patient_uuid() -> str:
    """Returns a sample patient UUID for doctor queries."""
    return "33333333-3333-3333-3333-333333333333"


# =============================================================================
# Utility Fixtures
# =============================================================================

@pytest.fixture
def random_uuid() -> str:
    """Returns a random UUID string."""
    return str(uuid4())


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Returns mock authorization headers."""
    return {"Authorization": "Bearer mock_test_token"}

