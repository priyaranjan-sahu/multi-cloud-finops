"""Prometheus metrics for the FinOps engine.

Metrics are recomputed on a background loop so /metrics stays fast and never
blocks on model fitting, cached between refreshes, and label sets are cleared
each cycle to avoid stale series.
"""

import asyncio
import logging
import time
from typing import TypedDict

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

from finops_engine.ai.anomaly_detector import AnomalyDetector
from finops_engine.ai.rightsizing_engine import RightsizingEngine
from finops_engine.config import settings
from finops_engine.connectors import fetch_multicloud_cost

logger = logging.getLogger("finops.exporter")

__all__ = [
    "CONTENT_TYPE_LATEST",
    "FINOPS_REQUEST_COUNTER",
    "get_prometheus_metrics_bytes",
    "refresh_finops_metrics_loop",
    "update_finops_metrics",
]

FINOPS_COST_GAUGE = Gauge(
    "finops_cloud_cost_usd",
    "Current accumulated cloud cost in USD",
    ["provider", "service"],
)

FINOPS_ANOMALIES_GAUGE = Gauge(
    "finops_anomalies_active_count",
    "Active detected cloud cost anomalies count",
    ["severity"],
)

FINOPS_SAVINGS_GAUGE = Gauge(
    "finops_potential_savings_usd",
    "Potential monthly savings identified by rightsizing engine in USD",
    ["provider", "category"],
)

FINOPS_REQUEST_COUNTER = Counter(
    "finops_api_requests_total",
    "Total API requests served by FinOps Engine",
    ["endpoint"],
)


class MetricsCache(TypedDict):
    content: bytes | None
    last_refresh: float


_metrics_cache: MetricsCache = {"content": None, "last_refresh": 0.0}


def update_finops_metrics() -> None:
    """Fetches latest telemetry, runs AI engines, and updates Prometheus metrics."""
    try:
        records, _ = fetch_multicloud_cost(use_mock=settings.mock_mode, days=30, allow_fallback=True)

        FINOPS_COST_GAUGE.clear()
        FINOPS_SAVINGS_GAUGE.clear()
        FINOPS_ANOMALIES_GAUGE.clear()

        cost_map: dict[tuple[str, str], float] = {}
        for record in records:
            key = (record.provider_name.value, record.service_name)
            cost_map[key] = cost_map.get(key, 0.0) + record.billed_cost

        for (provider, service), cost in cost_map.items():
            FINOPS_COST_GAUGE.labels(provider=provider, service=service).set(round(cost, 2))

        detector = AnomalyDetector()
        anomalies = detector.detect_anomalies(records)
        severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for anomaly in anomalies:
            sev = anomaly.get("severity", "LOW")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        for sev, count in severity_counts.items():
            FINOPS_ANOMALIES_GAUGE.labels(severity=sev).set(count)

        rightsizing = RightsizingEngine()
        recs = rightsizing.generate_recommendations(records)

        # Accumulate per (provider, category) so multiple recommendations
        # sharing a label set are summed instead of overwriting each other.
        savings_map: dict[tuple[str, str], float] = {}
        for rec in recs.get("recommendations", []):
            key = (rec.get("provider", "Multi-Cloud"), rec.get("category", "General"))
            savings_map[key] = savings_map.get(key, 0.0) + rec.get("estimated_monthly_savings_usd", 0.0)

        for (provider, category), savings in savings_map.items():
            FINOPS_SAVINGS_GAUGE.labels(provider=provider, category=category).set(round(savings, 2))

    except Exception:
        logger.exception("Failed to update Prometheus metrics")


def _refresh_cached_metrics() -> None:
    update_finops_metrics()
    _metrics_cache["content"] = generate_latest()
    _metrics_cache["last_refresh"] = time.monotonic()


def get_prometheus_metrics_bytes() -> bytes:
    """Returns the latest cached Prometheus metrics payload for HTTP handlers."""
    if _metrics_cache["content"] is None:
        _refresh_cached_metrics()
    content = _metrics_cache["content"]
    assert content is not None
    return content


async def refresh_finops_metrics_loop(interval_seconds: int = 15) -> None:
    """Background task that recomputes and caches metrics on a fixed interval."""
    _refresh_cached_metrics()
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            _refresh_cached_metrics()
        except Exception:
            logger.exception("Background metrics refresh failed")
