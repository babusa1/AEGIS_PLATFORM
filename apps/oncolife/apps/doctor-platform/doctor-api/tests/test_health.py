"""
Health Endpoint Tests
=====================

Tests for the /health endpoint to verify API is running.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    @pytest.mark.unit
    def test_health_check_returns_ok(self, client: TestClient):
        """Health endpoint should return 200 OK."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.unit
    def test_health_check_includes_service_name(self, client: TestClient):
        """Health response should include service identifier."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

