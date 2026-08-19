"""
Connector gateway for multi-cloud cost telemetry.

Provides a single, fail-closed entry point that aggregates AWS, GCP, and Azure
cost data, plus the mock connector used for demos and tests.
"""

from datetime import datetime, timedelta, timezone
from typing import Protocol

from finops_engine.errors import DataFetchError
from finops_engine.schema.focus_spec import FocusRecord

from .aws_connector import AWSConnector
from .azure_connector import AzureConnector
from .gcp_connector import GCPConnector
from .mock_connector import MockTelemetryConnector

__all__ = [
    "AWSConnector",
    "GCPConnector",
    "AzureConnector",
    "MockTelemetryConnector",
    "DataFetchError",
    "fetch_multicloud_cost",
]


class CostConnector(Protocol):
    """Structural type shared by every live cloud connector."""

    def fetch_cost_data(self, start_date: str | None = None, end_date: str | None = None) -> list[FocusRecord]: ...


def fetch_multicloud_cost(
    use_mock: bool = True,
    days: int = 30,
    allow_fallback: bool = False,
) -> tuple[list[FocusRecord], str]:
    """
    Fetch cost telemetry across all configured cloud providers.

    Returns a ``(records, source)`` tuple where ``source`` is one of
    ``"mock"``, ``"live"``, or ``"mock-fallback"``.

    Fails closed: when live fetching returns no records and ``allow_fallback``
    is False, a ``DataFetchError`` is raised instead of silently reporting
    synthetic data as real.
    """
    if use_mock:
        return MockTelemetryConnector(days=days).fetch_cost_data(), "mock"

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days)
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = end_dt.strftime("%Y-%m-%d")

    connectors: list[CostConnector] = [AWSConnector(), GCPConnector(), AzureConnector()]
    records: list[FocusRecord] = []
    for connector in connectors:
        records.extend(connector.fetch_cost_data(start_date=start_date, end_date=end_date))

    if not records:
        if allow_fallback:
            return MockTelemetryConnector(days=days).fetch_cost_data(), "mock-fallback"
        raise DataFetchError("No cost data available from any configured cloud provider")

    return records, "live"
