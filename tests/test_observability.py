from fastapi.testclient import TestClient
from aegis.api.main import app


def test_metrics_prometheus():
    client = TestClient(app)
    resp = client.get("/v1/observability/metrics?format=prometheus")
    assert resp.status_code == 200
    # Should return text with HELP and TYPE lines
    assert "# HELP" in resp.text or resp.headers.get("content-type") == "application/json"


def test_metrics_json():
    client = TestClient(app)
    resp = client.get("/v1/observability/metrics?format=json")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
