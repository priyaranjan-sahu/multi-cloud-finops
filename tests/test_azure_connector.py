"""
Unit tests for the Azure Cost Management connector mapping logic.

The live SDK calls are mocked so tests run without Azure credentials.
"""

from datetime import datetime, timezone
from unittest.mock import patch

from finops_engine.connectors.azure_connector import AzureConnector
from finops_engine.schema import ChargeCategory, CloudProvider


class _FakeColumn:
    def __init__(self, name):
        self.name = name


class _FakeQueryResult:
    columns = [_FakeColumn("date"), _FakeColumn("ServiceName"), _FakeColumn("totalCost")]
    rows = [["2026-01-15", "Virtual Machines", "123.45"]]


def test_azure_connector_maps_sdk_response_to_focus_record():
    with (
        patch("azure.identity.DefaultAzureCredential"),
        patch("azure.mgmt.costmanagement.CostManagementClient") as client_cls,
    ):
        client_cls.return_value.query.usage.return_value = _FakeQueryResult()
        records = AzureConnector(subscription_id="sub-123").fetch_cost_data("2026-01-15", "2026-01-15")

    assert len(records) == 1
    record = records[0]
    assert record.provider_name == CloudProvider.AZURE
    assert record.charge_category == ChargeCategory.USAGE
    assert record.service_name == "Virtual Machines"
    assert record.billed_cost == 123.45
    assert record.billing_period_start == datetime(2026, 1, 15, tzinfo=timezone.utc)


def test_azure_connector_builds_query_definition_with_required_type_and_datetimes():
    with (
        patch("azure.identity.DefaultAzureCredential"),
        patch("azure.mgmt.costmanagement.CostManagementClient") as client_cls,
        patch("azure.mgmt.costmanagement.models.QueryDefinition") as qd_cls,
    ):
        client_cls.return_value.query.usage.return_value = _FakeQueryResult()
        AzureConnector(subscription_id="sub-123").fetch_cost_data("2026-01-15", "2026-01-31")

    _, kwargs = qd_cls.call_args
    assert kwargs["type"] == "Usage"
    assert isinstance(kwargs["time_period"].from_property, datetime)
    assert isinstance(kwargs["time_period"].to, datetime)


def test_azure_connector_isolates_malformed_rows():
    class _FakeWithBadRow:
        columns = [_FakeColumn("date"), _FakeColumn("ServiceName"), _FakeColumn("totalCost")]
        rows = [["not-a-date", "Virtual Machines", "12.34"], ["2026-01-15", "Storage", "5.00"]]

    with (
        patch("azure.identity.DefaultAzureCredential"),
        patch("azure.mgmt.costmanagement.CostManagementClient") as client_cls,
    ):
        client_cls.return_value.query.usage.return_value = _FakeWithBadRow()
        records = AzureConnector().fetch_cost_data("2026-01-15", "2026-01-15")

    assert len(records) == 1
    assert records[0].service_name == "Storage"
