"""
================================================================================
OncoLife Patient API - Test Fixtures
================================================================================

Module:         conftest.py
Description:    Shared pytest fixtures for Patient API tests. Provides test
                database sessions, mock authentication, and sample data factories.

Created:        2026-01-05
Modified:       2026-01-16
Author:         Naveen Babu S A
Version:        2.1.0

Fixtures Provided:
    - db_session: In-memory SQLite database session
    - client: Authenticated test client
    - unauthenticated_client: Test client without auth
    - test_patient_uuid: Consistent test patient ID
    - sample_patient_data: Sample patient registration data
    - sample_diary_entry: Sample diary entry data
    - sample_question: Sample patient question data

Usage:
    def test_my_feature(client: TestClient, sample_question):
        response = client.post("/api/v1/questions", json=sample_question)
        assert response.status_code == 201

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
from db.database import get_patient_db
from routers.auth.dependencies import get_current_user, TokenData


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
def test_patient_uuid() -> str:
    """Returns a consistent test patient UUID."""
    return "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def test_token_data(test_patient_uuid: str) -> TokenData:
    """Returns mock token data for authentication."""
    return TokenData(
        sub=test_patient_uuid,
        email="test.patient@example.com"
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
    app.dependency_overrides[get_patient_db] = lambda: db_session
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
    app.dependency_overrides[get_patient_db] = lambda: db_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# =============================================================================
# Sample Data Factories
# =============================================================================

@pytest.fixture
def sample_patient_data(test_patient_uuid: str) -> Dict[str, Any]:
    """Returns sample patient registration data."""
    return {
        "uuid": test_patient_uuid,
        "email": "test.patient@example.com",
        "first_name": "Test",
        "last_name": "Patient",
        "date_of_birth": "1980-01-15",
        "phone_number": "+1234567890"
    }


@pytest.fixture
def sample_diary_entry() -> Dict[str, Any]:
    """Returns sample diary entry data."""
    return {
        "content": "Today I felt better. Less nausea than yesterday.",
        "mood": "Happy",
        "energy_level": 7,
        "pain_level": 2
    }


@pytest.fixture
def sample_question() -> Dict[str, Any]:
    """Returns sample question data."""
    return {
        "question_text": "Should I take my medication with food?",
        "share_with_physician": True,
        "category": "medication"
    }


@pytest.fixture
def sample_chemo_entry() -> Dict[str, Any]:
    """Returns sample chemotherapy log entry."""
    return {
        "treatment_date": "2026-01-06",
        "treatment_type": "Cycle 3",
        "notes": "Standard infusion, no complications"
    }


# =============================================================================
# Utility Fixtures
# =============================================================================

@pytest.fixture
def random_uuid() -> str:
    """Returns a random UUID string."""
    return str(uuid4())


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """
    Returns mock authorization headers.
    Note: With mock_current_user, these aren't validated but included for completeness.
    """
    return {"Authorization": "Bearer mock_test_token"}

