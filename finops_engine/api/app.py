"""
Enterprise FastAPI REST API Server for Multi-Cloud FinOps Platform
Exposes RESTful endpoints for FOCUS 1.0 telemetry, AI anomaly detection, forecasting, and rightsizing.
"""

import logging
from typing import Optional
from fastapi import FastAPI, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from finops_engine import __version__
from finops_engine.connectors import MockTelemetryConnector, AWSConnector, GCPConnector, AzureConnector
from finops_engine.schema import normalize_to_focus_dataframe
from finops_engine.ai import AnomalyDetector, CostForecaster, RightsizingEngine
from finops_engine.exporter import get_prometheus_metrics_bytes, FINOPS_REQUEST_COUNTER, CONTENT_TYPE_LATEST

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("finops.api")

app = FastAPI(
    title="Multi-Cloud FinOps Platform API",
    description="Production-Grade Multi-Cloud Cost Optimization & AI Anomaly Detection Engine (FOCUS 1.0 Compliant)",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend / web integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_records(use_mock: bool = True, days: int = 90):
    if use_mock:
        return MockTelemetryConnector(days=days).fetch_cost_data()
    
    # Live connector aggregation fallback
    records = []
    records.extend(AWSConnector().fetch_cost_data())
    records.extend(GCPConnector().fetch_cost_data())
    records.extend(AzureConnector().fetch_cost_data())
    
    if not records:
        records = MockTelemetryConnector(days=days).fetch_cost_data()
    return records


@app.get("/", status_code=status.HTTP_200_OK)
def root():
    """Platform health check and system info."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/").inc()
    return {
        "status": "online",
        "service": "Multi-Cloud FinOps Engine",
        "version": __version__,
        "focus_compliance": "FOCUS 1.0 Standard",
        "documentation": "/docs",
        "prometheus_metrics": "/metrics"
    }


@app.get("/api/v1/costs/summary")
def get_cost_summary(days: int = Query(default=30, ge=1, le=365), use_mock: bool = True):
    """Aggregate multi-cloud spend by Provider, Service, and Region."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/costs/summary").inc()
    records = _get_records(use_mock=use_mock, days=days)
    df = normalize_to_focus_dataframe(records)

    total_spend = float(df["billed_cost"].sum()) if not df.empty else 0.0
    by_provider = df.groupby("provider_name")["billed_cost"].sum().round(2).to_dict() if not df.empty else {}
    by_service = df.groupby("service_name")["billed_cost"].sum().round(2).to_dict() if not df.empty else {}

    return {
        "period_days": days,
        "total_billed_cost_usd": round(total_spend, 2),
        "spend_by_provider": by_provider,
        "spend_by_service": by_service,
        "total_records_processed": len(records)
    }


@app.get("/api/v1/costs/focus-export")
def export_focus_telemetry(days: int = Query(default=30, ge=1, le=90), use_mock: bool = True):
    """Export standardized FOCUS 1.0 normalized billing telemetry."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/costs/focus-export").inc()
    records = _get_records(use_mock=use_mock, days=days)
    return {
        "focus_version": "1.0",
        "record_count": len(records),
        "records": [r.to_dict() for r in records]
    }


@app.get("/api/v1/anomalies/detect")
def detect_anomalies(days: int = Query(default=60, ge=7, le=180), contamination: float = 0.05, use_mock: bool = True):
    """Trigger AI anomaly detection on cloud cost telemetry."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/anomalies/detect").inc()
    records = _get_records(use_mock=use_mock, days=days)
    detector = AnomalyDetector(contamination=contamination)
    anomalies = detector.detect_anomalies(records)

    return {
        "analyzed_days": days,
        "anomalies_detected_count": len(anomalies),
        "anomalies": anomalies
    }


@app.get("/api/v1/forecast/predict")
def predict_costs(forecast_days: int = Query(default=30, ge=7, le=90), use_mock: bool = True):
    """Run AI time-series forecasting model to project future cloud costs."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/forecast/predict").inc()
    records = _get_records(use_mock=use_mock, days=60)
    forecaster = CostForecaster(forecast_days=forecast_days)
    return forecaster.predict_future_cost(records)


@app.get("/api/v1/recommendations/rightsizing")
def get_rightsizing_recommendations(use_mock: bool = True):
    """Fetch actionable rightsizing and waste reduction recommendations."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/recommendations/rightsizing").inc()
    records = _get_records(use_mock=use_mock, days=30)
    engine = RightsizingEngine()
    return engine.generate_recommendations(records)


@app.get("/metrics")
def prometheus_metrics():
    """Prometheus metrics scraper endpoint."""
    metrics_data = get_prometheus_metrics_bytes()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
