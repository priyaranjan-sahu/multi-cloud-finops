"""Unit tests for the Change Intelligence and Deployment Attribution engine."""

from datetime import datetime, timedelta, timezone

from finops_engine.ai.change_intelligence import ChangeIntelligenceEngine
from finops_engine.connectors.mock_connector import MockTelemetryConnector
from finops_engine.schema.deployment_event import DeploymentEvent
from finops_engine.schema.focus_spec import ChargeCategory, CloudProvider, FocusRecord


def test_deployment_event_schema():
    event = DeploymentEvent(
        provider=CloudProvider.GCP,
        service_name="Cloud Run",
        resource_id="gcp-cloud-run-orders-001",
        environment="production",
        commit_sha="abcdef123456",
        author="alice@company.com",
        change_summary="autoscaling: min-instances 0 -> 1",
        diff_metadata={"min_instances": {"old": 0, "new": 1}},
    )
    assert event.event_id.startswith("DEP-")
    assert event.service_name == "Cloud Run"
    data = event.to_dict()
    assert data["commit_sha"] == "abcdef123456"
    assert data["diff_metadata"]["min_instances"]["new"] == 1


def test_change_intelligence_empty_inputs():
    engine = ChangeIntelligenceEngine()
    assert engine.attribute_cost_changes([], []) == []

    connector = MockTelemetryConnector(days=30)
    records = connector.fetch_cost_data()
    assert engine.attribute_cost_changes(records, []) == []
    assert engine.attribute_cost_changes([], connector.fetch_deployment_events()) == []


def test_change_intelligence_attributions_detected():
    connector = MockTelemetryConnector(days=30, seed=42)
    records = connector.fetch_cost_data()
    events = connector.fetch_deployment_events()

    engine = ChangeIntelligenceEngine(correlation_window_days=7, min_shift_threshold_usd=5.0)
    attributions = engine.attribute_cost_changes(records, events)

    assert isinstance(attributions, list)
    # Check that each attribution has required structure
    for attr in attributions:
        assert "attribution_id" in attr
        assert "resource_id" in attr
        assert "estimated_monthly_impact_usd" in attr
        assert attr["confidence"] in ("HIGH", "MEDIUM", "LOW")
        assert "root_cause_narrative" in attr
        assert "actionable_remediation" in attr
        assert attr["deployment_event"]["event_id"] in [e.event_id for e in events]


def test_change_intelligence_synthetic_spike_correlation():
    now = datetime.now(timezone.utc)
    records = [
        FocusRecord(
            provider_name=CloudProvider.GCP,
            publisher_name="Google Cloud",
            charge_category=ChargeCategory.USAGE,
            billed_cost=10.0,
            effective_cost=10.0,
            currency="USD",
            usage_quantity=24.0,
            usage_unit="Hours",
            service_name="Cloud Run",
            service_category="Container",
            region_id="us-central1",
            sub_account_id="gcp-prod",
            resource_id="gcp-cloud-run-orders-001",
            billing_period_start=now - timedelta(days=2),
            billing_period_end=now - timedelta(days=1),
        ),
        FocusRecord(
            provider_name=CloudProvider.GCP,
            publisher_name="Google Cloud",
            charge_category=ChargeCategory.USAGE,
            billed_cost=216.0,  # Big jump from $10 -> $216
            effective_cost=216.0,
            currency="USD",
            usage_quantity=24.0,
            usage_unit="Hours",
            service_name="Cloud Run",
            service_category="Container",
            region_id="us-central1",
            sub_account_id="gcp-prod",
            resource_id="gcp-cloud-run-orders-001",
            billing_period_start=now - timedelta(days=1),
            billing_period_end=now,
        ),
    ]

    event = DeploymentEvent(
        event_id="DEP-LOADTEST-01",
        timestamp=now - timedelta(days=1, hours=2),
        provider=CloudProvider.GCP,
        service_name="Cloud Run",
        resource_id="gcp-cloud-run-orders-001",
        environment="production",
        commit_sha="9876543210ab",
        author="sre-team@company.internal",
        change_summary="min-instances 0 -> 1 for load test",
        diff_metadata={"min_instances": 1},
    )

    engine = ChangeIntelligenceEngine(correlation_window_days=3, min_shift_threshold_usd=10.0)
    attributions = engine.attribute_cost_changes(records, [event])

    assert len(attributions) == 1
    assert attributions[0]["confidence"] == "HIGH"
    assert attributions[0]["resource_id"] == "gcp-cloud-run-orders-001"
    assert "min-instances 0 -> 1" in attributions[0]["root_cause_narrative"]
    assert attributions[0]["estimated_monthly_impact_usd"] > 1000.0
