"""
Unit tests for the multi-provider connector gateway.
"""

import pytest

from finops_engine.connectors import (
    AWSConnector,
    AzureConnector,
    DataFetchError,
    GCPConnector,
    MockTelemetryConnector,
    fetch_multicloud_cost,
)


def test_mock_connector_returns_focus_records():
    records = MockTelemetryConnector(days=7).fetch_cost_data()
    assert len(records) > 0
    assert all(record.billed_cost > 0 for record in records)


def test_fetch_multicloud_cost_mock_mode():
    records, source = fetch_multicloud_cost(use_mock=True, days=7)
    assert source == "mock"
    assert len(records) > 0


def test_fetch_multicloud_cost_fails_closed(monkeypatch):
    for connector_cls in (AWSConnector, GCPConnector, AzureConnector):
        monkeypatch.setattr(connector_cls, "fetch_cost_data", lambda self, *args, **kwargs: [])

    with pytest.raises(DataFetchError, match="No live cloud providers are configured"):
        fetch_multicloud_cost(use_mock=False, days=7)


def test_fetch_multicloud_cost_fails_closed_empty_data(monkeypatch):
    monkeypatch.setattr(AWSConnector, "fetch_cost_data", lambda self, *args, **kwargs: [])
    monkeypatch.setenv("FINOP_AWS_ACCOUNT_ID", "12345")
    from finops_engine.config import settings

    monkeypatch.setattr(settings, "aws_account_id", "12345")
    with pytest.raises(DataFetchError, match="No cost data available from any configured cloud provider"):
        fetch_multicloud_cost(use_mock=False, days=7)


def test_fetch_multicloud_cost_mock_fallback(monkeypatch):
    for connector_cls in (AWSConnector, GCPConnector, AzureConnector):
        monkeypatch.setattr(connector_cls, "fetch_cost_data", lambda self, *args, **kwargs: [])

    records, source = fetch_multicloud_cost(use_mock=False, days=7, allow_fallback=True)
    assert source == "mock-fallback"
    assert len(records) > 0


def test_live_connectors_are_never_imported_in_mock_mode(monkeypatch):
    """Fetching mock data must not instantiate live cloud SDK connectors."""
    called = []

    def guard(*args, **kwargs):
        called.append(True)
        return []

    monkeypatch.setattr(AWSConnector, "fetch_cost_data", guard)
    monkeypatch.setattr(GCPConnector, "fetch_cost_data", guard)
    monkeypatch.setattr(AzureConnector, "fetch_cost_data", guard)

    fetch_multicloud_cost(use_mock=True, days=7)
    assert called == []
