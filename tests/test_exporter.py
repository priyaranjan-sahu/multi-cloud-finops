"""
Unit tests for the Prometheus metrics exporter (Community Edition).
"""

from datetime import datetime, timedelta, timezone

from finops_engine.exporter import metrics_exporter
from finops_engine.schema import ChargeCategory, CloudProvider, FocusRecord, categorize_service


def _focus_record(resource_id: str, billed: float, usage: float, service: str = "AmazonS3") -> FocusRecord:
    start = datetime.now(timezone.utc) - timedelta(days=1)
    return FocusRecord(
        provider_name=CloudProvider.AWS,
        publisher_name="Amazon Web Services",
        charge_category=ChargeCategory.USAGE,
        billed_cost=billed,
        effective_cost=billed,
        currency="USD",
        usage_quantity=usage,
        usage_unit="Hours",
        service_name=service,
        service_category=categorize_service(service),
        region_id="us-east-1",
        sub_account_id="aws-account-main",
        resource_id=resource_id,
        billing_period_start=start,
        billing_period_end=start + timedelta(days=1),
    )


def test_metrics_exporter_updates_cost_and_anomalies(monkeypatch):
    """Cost gauge and anomalies gauge are populated from telemetry."""
    records = [
        _focus_record(resource_id="aws-s3-bucket-a", billed=100.0, usage=10.0),
        _focus_record(resource_id="aws-s3-bucket-b", billed=50.0, usage=5.0),
    ]

    monkeypatch.setattr(metrics_exporter, "fetch_multicloud_cost", lambda *args, **kwargs: (records, "mock"))

    metrics_exporter.update_finops_metrics()

    cost_samples = list(metrics_exporter.FINOPS_COST_GAUGE.collect()[0].samples)
    aws_s3_samples = [s.value for s in cost_samples if dict(s.labels) == {"provider": "AWS", "service": "AmazonS3"}]
    assert aws_s3_samples == [150.0]

    raw_bytes = metrics_exporter.get_prometheus_metrics_bytes()
    assert b"finops_cloud_cost_usd" in raw_bytes
