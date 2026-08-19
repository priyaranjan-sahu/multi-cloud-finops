"""
Enterprise FastAPI REST API Server for Multi-Cloud FinOps Platform
Exposes RESTful endpoints for FOCUS telemetry, AI anomaly detection, forecasting,
and rightsizing, with typed response models and optional API-key authentication.
"""

import asyncio
import contextlib
import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from finops_engine import __version__
from finops_engine.ai import AnomalyDetector, CostForecaster, RightsizingEngine
from finops_engine.api.models import (
    AnomalyDetectionResponse,
    CostSummaryResponse,
    FocusExportResponse,
    ForecastResponse,
    HealthResponse,
    RightsizingResponse,
)
from finops_engine.config import settings
from finops_engine.connectors import fetch_multicloud_cost
from finops_engine.errors import ConnectorError
from finops_engine.exporter import (
    CONTENT_TYPE_LATEST,
    FINOPS_REQUEST_COUNTER,
    get_prometheus_metrics_bytes,
    refresh_finops_metrics_loop,
)
from finops_engine.schema import normalize_to_focus_dataframe

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("finops.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Starts the background Prometheus metrics refresh loop."""
    if settings.environment.lower() == "production":
        if not settings.api_key:
            raise RuntimeError("FINOP_API_KEY must be set when FINOP_ENVIRONMENT=production")
        if not settings.cors_origins:
            raise RuntimeError("FINOP_CORS_ORIGINS must be set when FINOP_ENVIRONMENT=production")

    metrics_task = asyncio.create_task(refresh_finops_metrics_loop(settings.metrics_refresh_seconds))
    logger.info("Background Prometheus metrics refresh started (every %ss)", settings.metrics_refresh_seconds)
    try:
        yield
    finally:
        metrics_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await metrics_task


app = FastAPI(
    title="Multi-Cloud FinOps API",
    description="Cost optimization and anomaly detection for AWS, GCP, and Azure (FOCUS-aligned)",
    version=__version__,
    lifespan=lifespan,
)

# CORS: credentials are only allowed when an explicit origin allow-list is configured.
origins = settings.cors_origins or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=bool(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key Security Dependency
api_key_header = APIKeyHeader(name="X-API-Key", scheme_name="ApiKeyAuth", auto_error=False)


async def verify_api_key(api_key: str | None = Depends(api_key_header)):
    """Validates the API key when configured."""
    if settings.api_key and (not api_key or not hmac.compare_digest(api_key, settings.api_key)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


# OpenAPI dynamic schema customizer to match settings.api_key configuration
_original_openapi = app.openapi


def custom_openapi() -> dict:
    """Dynamically includes or omits API-key security schemes based on config."""
    if app.openapi_schema:
        return app.openapi_schema

    schema = _original_openapi()
    if not settings.api_key:
        # Strip API key security if disabled
        if "components" in schema and "securitySchemes" in schema["components"]:
            schema["components"].pop("securitySchemes", None)
        for path in schema.get("paths", {}).values():
            for method in path.values():
                method.pop("security", None)
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi  # type: ignore[method-assign]

# Sub-router for versioned API endpoints, secured by API Key validation
api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)])


def _get_records(use_mock: bool | None, days: int = 30):
    """Fetches records and returns (records, source), failing closed on empty live data."""
    mock_mode = settings.mock_mode if use_mock is None else use_mock
    try:
        return fetch_multicloud_cost(use_mock=mock_mode, days=days, allow_fallback=settings.allow_mock_fallback)
    except ConnectorError as exc:
        logger.warning("No cost data available: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@app.get("/", response_model=HealthResponse)
def root():
    """Platform health check and system info."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/").inc()
    return {
        "status": "online",
        "service": "Multi-Cloud FinOps Engine",
        "version": __version__,
        "focus_compliance": "FOCUS-aligned",
        "documentation": "/docs",
        "prometheus_metrics": "/metrics",
    }


@api_router.get("/costs/summary", response_model=CostSummaryResponse)
def get_cost_summary(
    days: int = Query(default=30, ge=1, le=365),
    use_mock: bool | None = None,
):
    """Aggregate multi-cloud spend by Provider, Service, and Region."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/costs/summary").inc()
    records, source = _get_records(use_mock, days)
    df = normalize_to_focus_dataframe(records)

    total_spend = float(df["billed_cost"].sum()) if not df.empty else 0.0
    by_provider = df.groupby("provider_name")["billed_cost"].sum().round(2).to_dict() if not df.empty else {}
    by_service = df.groupby("service_name")["billed_cost"].sum().round(2).to_dict() if not df.empty else {}
    by_region = df.groupby("region_id")["billed_cost"].sum().round(2).to_dict() if not df.empty else {}

    return {
        "period_days": days,
        "total_billed_cost_usd": round(total_spend, 2),
        "spend_by_provider": by_provider,
        "spend_by_service": by_service,
        "spend_by_region": by_region,
        "total_records_processed": len(records),
        "data_source": source,
    }


@api_router.get("/costs/focus-export", response_model=FocusExportResponse)
def export_focus_telemetry(
    days: int = Query(default=30, ge=1, le=90),
    use_mock: bool | None = None,
    limit: int = Query(default=1000, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
):
    """Export standardized FOCUS 1.0 normalized billing telemetry (paginated)."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/costs/focus-export").inc()
    records, source = _get_records(use_mock, days)
    page = records[offset : offset + limit]
    return {
        "focus_version": "1.0",
        "record_count": len(records),
        "data_source": source,
        "records": page,
    }


@api_router.get("/anomalies/detect", response_model=AnomalyDetectionResponse)
def detect_anomalies(
    days: int = Query(default=60, ge=7, le=180),
    contamination: float = Query(default=0.05, ge=0.001, le=0.5),
    use_mock: bool | None = None,
):
    """Trigger AI anomaly detection on cloud cost telemetry."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/anomalies/detect").inc()
    records, source = _get_records(use_mock, days)
    detector = AnomalyDetector(contamination=contamination)
    anomalies = detector.detect_anomalies(records)

    return {
        "analyzed_days": days,
        "anomalies_detected_count": len(anomalies),
        "data_source": source,
        "anomalies": anomalies,
    }


@api_router.get("/forecast/predict", response_model=ForecastResponse)
def predict_costs(
    forecast_days: int = Query(default=30, ge=7, le=90),
    use_mock: bool | None = None,
):
    """Run AI time-series forecasting model to project future cloud costs."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/forecast/predict").inc()
    records, source = _get_records(use_mock, 60)
    forecaster = CostForecaster(forecast_days=forecast_days)
    result = forecaster.predict_future_cost(records)
    result["data_source"] = source
    return result


@api_router.get("/recommendations/rightsizing", response_model=RightsizingResponse)
def get_rightsizing_recommendations(use_mock: bool | None = None):
    """Fetch actionable rightsizing and waste reduction recommendations."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/recommendations/rightsizing").inc()
    records, source = _get_records(use_mock, 30)
    engine = RightsizingEngine()
    result = engine.generate_recommendations(records)
    result["data_source"] = source
    return result


@app.get("/metrics")
def prometheus_metrics():
    """Prometheus metrics scraper endpoint (served from the background refresh cache)."""
    metrics_data = get_prometheus_metrics_bytes()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


# Include the API router into the main app
app.include_router(api_router)
