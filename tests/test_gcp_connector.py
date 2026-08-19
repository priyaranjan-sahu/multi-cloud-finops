"""
Unit tests for the GCP BigQuery billing export connector mapping logic.

The live BigQuery client is mocked so tests run without GCP credentials.
"""

from datetime import datetime, timezone
from unittest.mock import patch

from finops_engine.connectors.gcp_connector import GCPConnector
from finops_engine.schema import ChargeCategory, CloudProvider


def _row(service: str = "Cloud Storage", billed: float = 20.0, credit: float = 5.0) -> dict:
    return {
        "service_name": service,
        "usage_start": datetime(2026, 1, 15, tzinfo=timezone.utc),
        "usage_end": datetime(2026, 1, 16, tzinfo=timezone.utc),
        "billed_cost": billed,
        "credit_amount": credit,
        "usage_quantity": 10.0,
        "usage_unit": "GB",
        "project_name": "finops-prod",
        "resource_name": "bucket-123",
    }


def test_gcp_connector_maps_row_to_focus_record():
    with patch("google.cloud.bigquery.Client") as client_cls:
        client_cls.return_value.query.return_value = [_row()]
        records = GCPConnector(project_id="finops-prod").fetch_cost_data("2026-01-15", "2026-01-16")

    assert len(records) == 1
    record = records[0]
    assert record.provider_name == CloudProvider.GCP
    assert record.charge_category == ChargeCategory.USAGE
    assert record.service_name == "Cloud Storage"
    assert record.billed_cost == 20.0
    assert record.effective_cost == 15.0  # billed - credits
    assert record.usage_quantity == 10.0
    assert record.usage_unit == "GB"
    assert record.service_category == "Storage"
    assert record.region_id == "global"
    assert record.sub_account_id == "finops-prod"
    assert record.resource_id == "bucket-123"
    assert record.billing_period_start == datetime(2026, 1, 15, tzinfo=timezone.utc)


def test_gcp_connector_falls_back_to_unknown_service():
    with patch("google.cloud.bigquery.Client") as client_cls:
        row = _row(service="")
        client_cls.return_value.query.return_value = [row]
        records = GCPConnector(project_id="finops-prod").fetch_cost_data("2026-01-15", "2026-01-16")

    assert records[0].service_name == "Unknown Service"


def test_gcp_connector_isolates_malformed_rows():
    bad_row = {
        "service_name": "Compute Engine",
        "usage_start": datetime(2026, 1, 15, tzinfo=timezone.utc),
        "usage_end": datetime(2026, 1, 16, tzinfo=timezone.utc),
        "billed_cost": "not-a-number",
        "credit_amount": 0.0,
    }
    good_row = _row(service="Cloud SQL")
    with patch("google.cloud.bigquery.Client") as client_cls:
        client_cls.return_value.query.return_value = [bad_row, good_row]
        records = GCPConnector(project_id="finops-prod").fetch_cost_data("2026-01-15", "2026-01-16")

    assert len(records) == 1
    assert records[0].service_name == "Cloud SQL"


def test_gcp_connector_returns_empty_on_sdk_failure():
    with patch("google.cloud.bigquery.Client", side_effect=Exception("no credentials")):
        records = GCPConnector(project_id="finops-prod").fetch_cost_data("2026-01-15", "2026-01-16")

    assert records == []
