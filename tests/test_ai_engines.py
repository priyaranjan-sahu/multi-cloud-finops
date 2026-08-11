"""
Unit tests for AI Anomaly Detection and Cost Forecasting engines.
"""

from datetime import datetime
from finops_engine.connectors import MockTelemetryConnector
from finops_engine.ai import AnomalyDetector, CostForecaster, RightsizingEngine


def test_mock_connector_generates_records():
    connector = MockTelemetryConnector(days=30)
    records = connector.fetch_cost_data()
    assert len(records) > 0
    # Each day x 3 providers x 4 services
    assert len(records) >= 30 * 3 * 4


def test_anomaly_detector_returns_list():
    connector = MockTelemetryConnector(days=90)
    records = connector.fetch_cost_data()
    detector = AnomalyDetector(contamination=0.05, z_threshold=2.0)
    anomalies = detector.detect_anomalies(records)
    assert isinstance(anomalies, list)


def test_anomaly_detector_detects_spikes():
    """Mock connector has hardcoded spikes on days 45-47 (AWS EC2), 70-71 (GCP BigQuery), 25-26 (Azure VM)."""
    connector = MockTelemetryConnector(days=90, seed=42)
    records = connector.fetch_cost_data()
    detector = AnomalyDetector(contamination=0.05, z_threshold=2.0)
    anomalies = detector.detect_anomalies(records)
    # Must detect at least some anomalies given injected spikes
    assert len(anomalies) > 0


def test_anomaly_severity_assignment():
    connector = MockTelemetryConnector(days=90, seed=42)
    records = connector.fetch_cost_data()
    detector = AnomalyDetector()
    anomalies = detector.detect_anomalies(records)
    for a in anomalies:
        assert a["severity"] in ("HIGH", "MEDIUM", "LOW")
        assert "root_cause" in a
        assert "z_score" in a


def test_cost_forecaster_output_structure():
    connector = MockTelemetryConnector(days=60)
    records = connector.fetch_cost_data()
    forecaster = CostForecaster(forecast_days=30)
    result = forecaster.predict_future_cost(records)

    assert "forecast" in result
    assert "total_projected_spend_usd" in result
    assert result["forecast_days"] == 30
    assert len(result["forecast"]) == 30


def test_forecaster_confidence_bounds_present():
    connector = MockTelemetryConnector(days=60)
    records = connector.fetch_cost_data()
    forecaster = CostForecaster(forecast_days=30)
    result = forecaster.predict_future_cost(records)
    for item in result["forecast"]:
        assert item["confidence_upper_usd"] >= item["predicted_cost_usd"]
        assert item["confidence_lower_usd"] >= 0.0


def test_rightsizing_engine_structure():
    connector = MockTelemetryConnector(days=30)
    records = connector.fetch_cost_data()
    engine = RightsizingEngine()
    result = engine.generate_recommendations(records)

    assert "total_potential_monthly_savings_usd" in result
    assert "recommendations" in result
    assert len(result["recommendations"]) > 0


def test_rightsizing_recommendations_fields():
    connector = MockTelemetryConnector(days=30)
    records = connector.fetch_cost_data()
    engine = RightsizingEngine()
    result = engine.generate_recommendations(records)
    for rec in result["recommendations"]:
        assert "id" in rec
        assert "provider" in rec
        assert "action" in rec
        assert "estimated_monthly_savings_usd" in rec
