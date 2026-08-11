"""
Unit tests for FOCUS 1.0 schema specification and DataFrame normalization.
"""

from datetime import datetime
from finops_engine.schema import FocusRecord, ChargeCategory, CloudProvider, normalize_to_focus_dataframe


def test_focus_record_creation():
    record = FocusRecord(
        provider_name=CloudProvider.AWS,
        publisher_name="Amazon Web Services",
        charge_category=ChargeCategory.USAGE,
        billed_cost=150.75,
        effective_cost=140.20,
        currency="USD",
        usage_quantity=100.0,
        usage_unit="Hours",
        service_name="AmazonEC2",
        service_category="Compute",
        region_id="us-east-1",
        sub_account_id="123456789012",
        billing_period_start=datetime(2024, 3, 1),
        billing_period_end=datetime(2024, 3, 2)
    )

    assert record.provider_name == CloudProvider.AWS
    assert record.billed_cost == 150.75
    assert record.currency == "USD"


def test_normalize_to_focus_dataframe():
    records = [
        FocusRecord(
            provider_name=CloudProvider.AWS,
            billed_cost=100.0,
            effective_cost=95.0,
            service_name="AmazonEC2",
            billing_period_start=datetime(2024, 3, 1),
            billing_period_end=datetime(2024, 3, 2)
        ),
        FocusRecord(
            provider_name=CloudProvider.GCP,
            billed_cost=200.0,
            effective_cost=190.0,
            service_name="Compute Engine",
            billing_period_start=datetime(2024, 3, 1),
            billing_period_end=datetime(2024, 3, 2)
        )
    ]

    df = normalize_to_focus_dataframe(records)
    assert len(df) == 2
    assert df["billed_cost"].sum() == 300.0
    assert "provider_name" in df.columns
