"""
Unit tests for the AWS Cost Explorer connector mapping logic.

The live SDK call is mocked so tests run without AWS credentials.
"""

from datetime import datetime, timezone
from unittest.mock import patch

from finops_engine.connectors.aws_connector import AWSConnector
from finops_engine.schema import ChargeCategory, CloudProvider


def _response(
    service: str,
    billed: float,
    amortized: float,
    usage: float,
    start: str = "2026-01-15",
    end: str = "2026-01-16",
) -> dict:
    return {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": start, "End": end},
                "Groups": [
                    {
                        "Keys": [service],
                        "Metrics": {
                            "UnblendedCost": {"Amount": str(billed)},
                            "AmortizedCost": {"Amount": str(amortized)},
                            "UsageQuantity": {"Amount": str(usage)},
                        },
                    }
                ],
            }
        ]
    }


def test_aws_connector_maps_sdk_response_to_focus_record():
    with patch("boto3.client") as client_factory:
        client_factory.return_value.get_cost_and_usage.return_value = _response(
            "Amazon S3", billed=10.5, amortized=9.0, usage=42.0
        )
        records = AWSConnector().fetch_cost_data("2026-01-15", "2026-01-16")

    assert len(records) == 1
    record = records[0]
    assert record.provider_name == CloudProvider.AWS
    assert record.charge_category == ChargeCategory.USAGE
    assert record.service_name == "Amazon S3"
    assert record.billed_cost == 10.5
    assert record.effective_cost == 9.0
    assert record.usage_quantity == 42.0
    assert record.service_category == "Storage"
    assert record.billing_period_start == datetime(2026, 1, 15, tzinfo=timezone.utc)
    assert record.billing_period_end == datetime(2026, 1, 16, tzinfo=timezone.utc)


def test_aws_connector_uses_default_dates_when_omitted():
    with patch("boto3.client") as client_factory:
        client_factory.return_value.get_cost_and_usage.return_value = _response("EC2", 5.0, 5.0, 1.0)
        AWSConnector().fetch_cost_data()

    time_period = client_factory.return_value.get_cost_and_usage.call_args.kwargs["TimePeriod"]
    assert "Start" in time_period
    assert "End" in time_period


def test_aws_connector_isolates_malformed_rows():
    bad_row = {
        "TimePeriod": {"Start": "not-a-date", "End": "2026-01-16"},
        "Groups": [{"Keys": ["EC2"], "Metrics": {"UnblendedCost": {"Amount": "1.00"}}}],
    }
    good_row = {
        "TimePeriod": {"Start": "2026-01-15", "End": "2026-01-16"},
        "Groups": [{"Keys": ["Amazon RDS"], "Metrics": {"UnblendedCost": {"Amount": "5.00"}}}],
    }
    with patch("boto3.client") as client_factory:
        client_factory.return_value.get_cost_and_usage.return_value = {"ResultsByTime": [bad_row, good_row]}
        records = AWSConnector().fetch_cost_data("2026-01-15", "2026-01-16")

    assert len(records) == 1
    assert records[0].service_name == "Amazon RDS"


def test_aws_connector_returns_empty_on_sdk_failure():
    with patch("boto3.client", side_effect=Exception("no credentials")):
        records = AWSConnector().fetch_cost_data("2026-01-15", "2026-01-16")

    assert records == []
