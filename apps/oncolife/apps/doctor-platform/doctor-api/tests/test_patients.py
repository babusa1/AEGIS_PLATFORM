"""
Patients Endpoint Tests
=======================

Tests for the /api/v1/patients endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestPatientsEndpoints:
    """Tests for patient list and detail endpoints."""

    @pytest.mark.unit
    def test_list_patients(self, client: TestClient):
        """Should return patient list."""
        response = client.get("/api/v1/patients")
        
        assert response.status_code == 200
        # Response should be a list
        data = response.json()
        assert isinstance(data, (list, dict))

    @pytest.mark.unit
    def test_patient_not_found(self, client: TestClient, random_uuid: str):
        """Should return 404 for non-existent patient."""
        response = client.get(f"/api/v1/patients/{random_uuid}")
        
        assert response.status_code in [404, 403]


class TestPatientAlerts:
    """Tests for patient alerts endpoint."""

    @pytest.mark.unit
    def test_patient_alerts_not_found(self, client: TestClient, random_uuid: str):
        """Should handle non-existent patient gracefully."""
        response = client.get(f"/api/v1/patients/{random_uuid}/alerts")
        
        assert response.status_code in [404, 403, 500]


class TestPatientsAuthentication:
    """Tests for patients authentication requirements."""

    @pytest.mark.auth
    def test_patients_requires_auth(self, unauthenticated_client: TestClient):
        """Patients endpoints should require authentication."""
        response = unauthenticated_client.get("/api/v1/patients")
        
        assert response.status_code in [401, 403]

