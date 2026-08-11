"""
Integration tests for the FastAPI REST API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from finops_engine.api.app import app

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


def test_focus_export_endpoint():
    response = client.get("/api/v1/costs/focus-export?days=7&use_mock=true")
    assert response.status_code == 200
    data = response.json()
    assert data["focus_version"] == "1.0"
    assert "records" in data
    assert data["record_count"] > 0


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
