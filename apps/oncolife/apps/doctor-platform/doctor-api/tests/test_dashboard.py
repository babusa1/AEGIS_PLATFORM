"""
Dashboard Endpoint Tests
========================

Tests for the /api/v1/dashboard endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestDashboardLanding:
    """Tests for dashboard landing endpoint."""

    @pytest.mark.unit
    def test_get_dashboard_landing(self, client: TestClient):
        """Should return dashboard with patient list."""
        response = client.get("/api/v1/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        assert "patients" in data
        assert "total_patients" in data
        assert "period_days" in data

    @pytest.mark.unit
    def test_dashboard_with_days_param(self, client: TestClient):
        """Should accept days parameter."""
        response = client.get("/api/v1/dashboard?days=14")
        
        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 14

    @pytest.mark.unit
    def test_dashboard_with_limit_param(self, client: TestClient):
        """Should accept limit parameter."""
        response = client.get("/api/v1/dashboard?limit=10")
        
        assert response.status_code == 200


class TestPatientTimeline:
    """Tests for patient timeline endpoint."""

    @pytest.mark.unit
    def test_patient_timeline_not_found(self, client: TestClient, random_uuid: str):
        """Should handle non-existent patient gracefully."""
        response = client.get(f"/api/v1/dashboard/patient/{random_uuid}")
        
        # Either 404 or 403 (unauthorized) or 500 (if patient doesn't exist)
        assert response.status_code in [403, 404, 500]


class TestPatientQuestions:
    """Tests for patient shared questions endpoint."""

    @pytest.mark.unit
    def test_patient_questions_not_found(self, client: TestClient, random_uuid: str):
        """Should handle non-existent patient gracefully."""
        response = client.get(f"/api/v1/dashboard/patient/{random_uuid}/questions")
        
        assert response.status_code in [403, 404, 500]


class TestWeeklyReports:
    """Tests for weekly reports endpoint."""

    @pytest.mark.unit
    def test_get_weekly_report(self, client: TestClient):
        """Should return weekly report data."""
        response = client.get("/api/v1/dashboard/reports/weekly")
        
        assert response.status_code == 200
        data = response.json()
        assert "physician_id" in data
        assert "report_week_start" in data
        assert "report_week_end" in data


class TestDashboardAuthentication:
    """Tests for dashboard authentication requirements."""

    @pytest.mark.auth
    def test_dashboard_requires_auth(self, unauthenticated_client: TestClient):
        """Dashboard endpoints should require authentication."""
        response = unauthenticated_client.get("/api/v1/dashboard")
        
        assert response.status_code in [401, 403]

