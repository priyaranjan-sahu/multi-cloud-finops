"""
Unit tests for the Prometheus metrics exporter.
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


def test_savings_gauge_accumulates_same_label_recommendations(monkeypatch):
    """Two recommendations sharing a (provider, category) label must be summed, not overwritten."""
    records = [
        _focus_record(resource_id="aws-s3-bucket-a", billed=100.0, usage=0.5),
        _focus_record(resource_id="aws-s3-bucket-b", billed=50.0, usage=0.5),
    ]

    monkeypatch.setattr(metrics_exporter, "fetch_multicloud_cost", lambda *args, **kwargs: (records, "mock"))

    metrics_exporter.update_finops_metrics()

    savings_samples = list(metrics_exporter.FINOPS_SAVINGS_GAUGE.collect()[0].samples)
    aws_storage = [
        s.value for s in savings_samples if dict(s.labels) == {"provider": "AWS", "category": "Storage Optimization"}
    ]
    # Both low-usage storage resources yield "delete" recommendations (100% savings),
    # so the single label set must report their combined savings.
    assert aws_storage == [150.0]
