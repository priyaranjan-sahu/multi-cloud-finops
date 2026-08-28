"""
Domain exceptions for the FinOps engine.

Centralizes error types so the API layer can translate failures into
appropriate HTTP responses without coupling to provider SDK internals.
"""


class FinOpsError(Exception):
    """Base class for all FinOps engine domain errors."""


class ConnectorError(FinOpsError):
    """Raised when a cloud provider connector cannot retrieve telemetry."""


class DataFetchError(ConnectorError):
    """Raised when live fetching returns no cost data (fail-closed)."""


class LicenseError(FinOpsError):
    """Raised when an enterprise feature is accessed without a valid Pro license."""
