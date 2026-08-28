"""
Unit tests for FOCUS schema specification and DataFrame normalization.
"""

from datetime import datetime

import pytest

from finops_engine.schema import (
    ChargeCategory,
    CloudProvider,
    FocusRecord,
    categorize_service,
    normalize_to_focus_dataframe,
)


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
        billing_period_end=datetime(2024, 3, 2),
    )

    assert record.provider_name == CloudProvider.AWS
    assert record.billed_cost == 150.75
    assert record.currency == "USD"


def test_focus_record_allows_credit_charges():
    record = FocusRecord(
        provider_name=CloudProvider.AWS,
        charge_category=ChargeCategory.CREDIT,
        billed_cost=-50.0,
        effective_cost=-50.0,
        service_name="AmazonEC2",
        billing_period_start=datetime(2024, 3, 1),
        billing_period_end=datetime(2024, 3, 2),
    )

    assert record.billed_cost == -50.0
    assert record.effective_cost == -50.0


def test_focus_record_to_dict_is_json_serializable():
    record = FocusRecord(
        provider_name=CloudProvider.GCP,
        billed_cost=200.0,
        effective_cost=190.0,
        service_name="Compute Engine",
        billing_period_start=datetime(2024, 3, 1),
        billing_period_end=datetime(2024, 3, 2),
    )

    data = record.to_dict()
    assert data["provider_name"] == "GCP"
    assert data["billing_period_start"].endswith("T00:00:00")


def test_normalize_to_focus_dataframe():
    records = [
        FocusRecord(
            provider_name=CloudProvider.AWS,
            billed_cost=100.0,
            effective_cost=95.0,
            service_name="AmazonEC2",
            billing_period_start=datetime(2024, 3, 1),
            billing_period_end=datetime(2024, 3, 2),
        ),
        FocusRecord(
            provider_name=CloudProvider.GCP,
            billed_cost=200.0,
            effective_cost=190.0,
            service_name="Compute Engine",
            billing_period_start=datetime(2024, 3, 1),
            billing_period_end=datetime(2024, 3, 2),
        ),
    ]

    df = normalize_to_focus_dataframe(records)
    assert len(df) == 2
    assert df["billed_cost"].sum() == 300.0
    assert "provider_name" in df.columns


def test_normalize_empty_records_returns_expected_columns():
    df = normalize_to_focus_dataframe([])
    assert df.empty
    assert "provider_name" in df.columns
    assert "billed_cost" in df.columns


@pytest.mark.parametrize(
    ("service", "expected"),
    [
        ("AmazonEC2", "Compute"),
        ("Compute Engine", "Compute"),
        ("Virtual Machines", "Compute"),
        ("AWS Lambda", "Compute"),
        ("AmazonS3", "Storage"),
        ("Cloud Storage", "Storage"),
        ("Blob Storage", "Storage"),
        ("AmazonRDS", "Database"),
        ("BigQuery", "Database"),
        ("SQL Database", "Database"),
        ("AmazonDynamoDB", "Database"),
        ("AmazonEKS", "Container"),
        ("GKE", "Container"),
        ("AKS", "Container"),
        ("AmazonECS", "Container"),
        ("AmazonVPC", "Network"),
        ("Virtual Network", "Network"),
        ("Cloud CDN", "Network"),
    ],
)
def test_categorize_service_shared_across_providers(service, expected):
    """Live connectors and the mock connector must agree on categorization."""
    assert categorize_service(service) == expected
