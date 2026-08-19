"""
Unit tests for AI Anomaly Detection, Cost Forecasting, and Rightsizing engines.
"""

from finops_engine.ai import AnomalyDetector, CostForecaster, RightsizingEngine
from finops_engine.connectors import MockTelemetryConnector


def test_mock_connector_generates_records():
    connector = MockTelemetryConnector(days=30)
    records = connector.fetch_cost_data()
    assert len(records) > 0
    # Each day x 3 providers x 4 services
    assert len(records) >= 30 * 3 * 4


def test_mock_connector_resource_ids_are_stable():
    connector = MockTelemetryConnector(days=30, seed=42)
    records = connector.fetch_cost_data()
    unique_ids = {record.resource_id for record in records}
    # Far fewer unique resources than records -> identities are stable across days
    assert len(unique_ids) < len(records)
    assert len(unique_ids) == 12  # 3 providers x 4 services


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


def test_anomaly_detector_empty_records():
    detector = AnomalyDetector()
    assert detector.detect_anomalies([]) == []


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


def test_forecaster_intervals_widen_with_horizon():
    connector = MockTelemetryConnector(days=60, seed=42)
    records = connector.fetch_cost_data()
    forecaster = CostForecaster(forecast_days=30)
    result = forecaster.predict_future_cost(records)

    first_margin = result["forecast"][0]["confidence_upper_usd"] - result["forecast"][0]["predicted_cost_usd"]
    last_margin = result["forecast"][-1]["confidence_upper_usd"] - result["forecast"][-1]["predicted_cost_usd"]
    assert last_margin >= first_margin


def test_forecaster_empty_records():
    forecaster = CostForecaster(forecast_days=30)
    result = forecaster.predict_future_cost([])
    assert result["forecast"] == []
    assert result["total_projected_spend_usd"] == 0.0


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


def test_rightsizing_recommendations_derived_from_data():
    connector = MockTelemetryConnector(days=30, seed=42)
    records = connector.fetch_cost_data()
    engine = RightsizingEngine()
    result = engine.generate_recommendations(records)

    known_resources = {record.resource_id for record in records}
    assert result["recommendations_count"] > 0
    for rec in result["recommendations"]:
        # Every recommendation must reference a real resource seen in telemetry
        assert rec["resource_id"] in known_resources
        assert rec["estimated_monthly_savings_usd"] > 0
        assert rec["projected_monthly_cost_usd"] < rec["current_monthly_cost_usd"]


def test_rightsizing_empty_records():
    engine = RightsizingEngine()
    result = engine.generate_recommendations([])
    assert result["recommendations"] == []
    assert result["total_potential_monthly_savings_usd"] == 0.0
    assert result["recommendations_count"] == 0
