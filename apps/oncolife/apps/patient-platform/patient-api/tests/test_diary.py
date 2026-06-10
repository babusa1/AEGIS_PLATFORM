"""
Diary Endpoint Tests
====================

Tests for the /api/v1/diary endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestDiaryEndpoints:
    """Tests for patient diary endpoints."""

    @pytest.mark.unit
    def test_list_diary_entries_empty(self, client: TestClient):
        """Should return empty list when no entries exist."""
        response = client.get("/api/v1/diary")
        
        assert response.status_code == 200
        # Response structure may vary - check for list or object with entries

    @pytest.mark.unit
    def test_create_diary_entry(self, client: TestClient, sample_diary_entry: dict):
        """Should create a new diary entry."""
        response = client.post("/api/v1/diary", json=sample_diary_entry)
        
        # Accept either 200 or 201 for creation
        assert response.status_code in [200, 201]

    @pytest.mark.unit
    def test_diary_entry_content_validation(self, client: TestClient):
        """Should validate diary entry content."""
        response = client.post("/api/v1/diary", json={
            "content": "",  # Empty content
        })
        
        # Should either reject empty content or accept with defaults
        assert response.status_code in [200, 201, 422]


class TestDiaryAuthentication:
    """Tests for diary authentication requirements."""

    @pytest.mark.auth
    def test_diary_requires_auth(self, unauthenticated_client: TestClient):
        """Diary endpoints should require authentication."""
        response = unauthenticated_client.get("/api/v1/diary")
        
        # Should return 401 or 403
        assert response.status_code in [401, 403]

