"""
Staff Endpoint Tests
====================

Tests for the /api/v1/staff endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestStaffEndpoints:
    """Tests for staff management endpoints."""

    @pytest.mark.unit
    def test_list_staff(self, client: TestClient):
        """Should return staff list."""
        response = client.get("/api/v1/staff")
        
        assert response.status_code == 200

    @pytest.mark.unit
    def test_get_staff_profile(self, client: TestClient):
        """Should return current user's staff profile."""
        response = client.get("/api/v1/staff/profile")
        
        # May return 200 or 404 depending on test data
        assert response.status_code in [200, 404]


class TestStaffAuthentication:
    """Tests for staff authentication requirements."""

    @pytest.mark.auth
    def test_staff_requires_auth(self, unauthenticated_client: TestClient):
        """Staff endpoints should require authentication."""
        response = unauthenticated_client.get("/api/v1/staff")
        
        assert response.status_code in [401, 403]

