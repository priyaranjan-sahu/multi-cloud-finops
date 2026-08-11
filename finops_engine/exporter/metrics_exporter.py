"""
Prometheus Metrics Exporter for Multi-Cloud FinOps Telemetry
Exposes metrics for scraping by Prometheus server.
"""

import logging
from prometheus_client import Gauge, Counter, generate_latest, CONTENT_TYPE_LATEST
from finops_engine.connectors.mock_connector import MockTelemetryConnector
from finops_engine.ai.anomaly_detector import AnomalyDetector
from finops_engine.ai.rightsizing_engine import RightsizingEngine

logger = logging.getLogger("finops.exporter")

# Prometheus Metrics Definitions
FINOPS_COST_GAUGE = Gauge(
    "finops_cloud_cost_usd",
    "Current accumulated cloud cost in USD",
    ["provider", "service"]
)

FINOPS_ANOMALIES_GAUGE = Gauge(
    "finops_anomalies_active_count",
    "Active detected cloud cost anomalies count",
    ["severity"]
)

FINOPS_SAVINGS_GAUGE = Gauge(
    "finops_potential_savings_usd",
    "Potential monthly savings identified by rightsizing engine in USD",
    ["provider", "category"]
)

FINOPS_REQUEST_COUNTER = Counter(
    "finops_api_requests_total",
    "Total API requests served by FinOps Engine",
    ["endpoint"]
)


def update_finops_metrics():
    """Fetches latest telemetry, runs AI engines, and updates Prometheus metrics."""
    try:
        connector = MockTelemetryConnector(days=30)
        records = connector.fetch_cost_data()

        # Update Cost Gauge by Provider and Service
        cost_map = {}
        for r in records:
            key = (r.provider_name.value, r.service_name)
            cost_map[key] = cost_map.get(key, 0.0) + r.billed_cost

        for (provider, service), cost in cost_map.items():
            FINOPS_COST_GAUGE.labels(provider=provider, service=service).set(round(cost, 2))

        # Update Anomaly Metrics
        detector = AnomalyDetector()
        anomalies = detector.detect_anomalies(records)
        severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for a in anomalies:
            sev = a.get("severity", "LOW")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        for sev, count in severity_counts.items():
            FINOPS_ANOMALIES_GAUGE.labels(severity=sev).set(count)

        # Update Potential Savings Metrics
        rightsizing = RightsizingEngine()
        recs = rightsizing.generate_recommendations(records)
        for r in recs.get("recommendations", []):
            FINOPS_SAVINGS_GAUGE.labels(
                provider=r.get("provider", "Multi-Cloud"),
                category=r.get("category", "General")
            ).set(r.get("estimated_monthly_savings_usd", 0.0))

    except Exception as e:
        logger.error(f"Failed to update Prometheus metrics: {e}")


def get_prometheus_metrics_bytes() -> bytes:
    """Returns encoded Prometheus metrics for HTTP handler."""
    update_finops_metrics()
    return generate_latest()
