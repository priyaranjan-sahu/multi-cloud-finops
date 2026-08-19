"""
Integration tests for the FastAPI REST API endpoints.
"""

from fastapi.testclient import TestClient

from finops_engine.api.app import app
from finops_engine.errors import DataFetchError

client = TestClient(app)


def test_root_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "version" in data
    assert "focus_compliance" in data


def test_cost_summary_endpoint():
    response = client.get("/api/v1/costs/summary?days=30&use_mock=true")
    assert response.status_code == 200
    data = response.json()
    assert "total_billed_cost_usd" in data
    assert data["total_billed_cost_usd"] > 0
    assert "spend_by_provider" in data
    assert "spend_by_service" in data


def test_cost_summary_reports_data_source():
    response = client.get("/api/v1/costs/summary?days=7")
    assert response.status_code == 200
    data = response.json()
    assert data["data_source"] == "mock"


def test_cost_summary_includes_region_breakdown():
    response = client.get("/api/v1/costs/summary?days=7&use_mock=true")
    assert response.status_code == 200
    data = response.json()
    assert "spend_by_region" in data
    assert data["spend_by_region"]  # mock telemetry spans us-east-1 / us-central1 / eastus


def test_focus_export_endpoint():
    response = client.get("/api/v1/costs/focus-export?days=7&use_mock=true")
    assert response.status_code == 200
    data = response.json()
    assert data["focus_version"] == "1.0"
    assert "records" in data
    assert data["record_count"] > 0


def test_focus_export_pagination():
    response = client.get("/api/v1/costs/focus-export?days=7&limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["record_count"] >= 10
    assert len(data["records"]) == 10


def test_anomaly_detection_endpoint():
    response = client.get("/api/v1/anomalies/detect?days=60&use_mock=true")
    assert response.status_code == 200
    data = response.json()
    assert "anomalies_detected_count" in data
    assert isinstance(data["anomalies"], list)


def test_cost_forecast_endpoint():
    response = client.get("/api/v1/forecast/predict?forecast_days=30&use_mock=true")
    assert response.status_code == 200
    data = response.json()
    assert "total_projected_spend_usd" in data
    assert "forecast" in data
    assert len(data["forecast"]) == 30


def test_rightsizing_recommendations_endpoint():
    response = client.get("/api/v1/recommendations/rightsizing?use_mock=true")
    assert response.status_code == 200
    data = response.json()
    assert "total_potential_monthly_savings_usd" in data
    assert len(data["recommendations"]) > 0


def test_prometheus_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"finops_" in response.content


def test_docs_available():
    response = client.get("/docs")
    assert response.status_code == 200


def test_api_key_enforced_when_configured(monkeypatch):
    from finops_engine.config import settings

    monkeypatch.setattr(settings, "api_key", "test-secret")

    unauthorized = client.get("/api/v1/costs/summary?days=7")
    assert unauthorized.status_code == 401

    authorized = client.get("/api/v1/costs/summary?days=7", headers={"X-API-Key": "test-secret"})
    assert authorized.status_code == 200


def test_live_mode_fails_closed_when_no_data(monkeypatch):
    import sys

    app_module = sys.modules["finops_engine.api.app"]

    def boom(*args, **kwargs):
        raise DataFetchError("No cost data available from any configured cloud provider")

    monkeypatch.setattr(app_module, "fetch_multicloud_cost", boom)

    response = client.get("/api/v1/costs/summary?days=7&use_mock=false")
    assert response.status_code == 503


def test_openapi_declares_api_key_scheme_when_configured(monkeypatch):
    from finops_engine.config import settings

    monkeypatch.setattr(settings, "api_key", "test-secret")

    schema = app.openapi()
    assert "ApiKeyAuth" in schema["components"]["securitySchemes"]
    assert schema["components"]["securitySchemes"]["ApiKeyAuth"]["name"] == "X-API-Key"
    # /api/* operations are documented as requiring the key...
    assert schema["paths"]["/api/v1/costs/summary"]["get"]["security"] == [{"ApiKeyAuth": []}]
    # ...while public endpoints are not.
    assert "security" not in schema["paths"]["/"]["get"]


def test_openapi_omits_security_when_key_disabled(monkeypatch):
    from finops_engine.config import settings

    monkeypatch.setattr(settings, "api_key", "")
    app.openapi_schema = None
    schema = app.openapi()
    assert "securitySchemes" not in schema["components"]
