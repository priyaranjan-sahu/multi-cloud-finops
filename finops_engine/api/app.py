"""
FastAPI REST API Server for Multi-Cloud FinOps Platform (Community Edition)
Exposes RESTful endpoints for FOCUS telemetry, AI anomaly detection, forecasting,
and Prometheus monitoring, with typed response models and API-key authentication.
"""

import asyncio
import hmac
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader

from finops_engine import __version__
from finops_engine.ai import AnomalyDetector, CostForecaster
from finops_engine.api.models import (
    AnomalyDetectionResponse,
    CostSummaryResponse,
    ForecastResponse,
    HealthResponse,
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
    is_prod = settings.environment.lower() == "production" or not settings.mock_mode
    if is_prod and not settings.api_key and not settings.allow_anonymous:
        raise RuntimeError(
            "FATAL: FINOP_API_KEY must be set in production mode. "
            "Set FINOP_ALLOW_ANONYMOUS=true if you explicitly intend to expose unauthenticated endpoints."
        )
    if settings.environment.lower() == "production" and not settings.cors_origins:
        raise RuntimeError("FINOP_CORS_ORIGINS must be set when FINOP_ENVIRONMENT=production")

    metrics_task = asyncio.create_task(refresh_finops_metrics_loop(settings.metrics_refresh_seconds))
    logger.info("Background Prometheus metrics refresh started (every %ss)", settings.metrics_refresh_seconds)
    try:
        yield
    finally:
        metrics_task.cancel()
        with suppress(asyncio.CancelledError):
            await metrics_task


app = FastAPI(
    title="Multi-Cloud FinOps API (Community Edition)",
    description="Cost optimization and anomaly detection for AWS, GCP, and Azure (FOCUS-aligned)",
    version=__version__,
    lifespan=lifespan,
)


# CORS: credentials are only allowed when an explicit origin allow-list is configured.
is_prod_env = settings.environment.lower() == "production" or not settings.mock_mode
origins = settings.cors_origins if settings.cors_origins else ([] if is_prod_env else ["*"])
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
    """Validates the API key with strict security and constant-time comparison."""
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
async def get_cost_summary(
    days: int = Query(default=30, ge=1, le=365),
    use_mock: bool | None = None,
):
    """Aggregate multi-cloud spend by Provider, Service, and Region."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/costs/summary").inc()

    def _process():
        records, source = _get_records(use_mock, days)
        df = normalize_to_focus_dataframe(records)
        total_spend = float(df["billed_cost"].sum()) if not df.empty else 0.0
        by_provider = df.groupby("provider_name")["billed_cost"].sum().round(2).to_dict() if not df.empty else {}
        by_service = df.groupby("service_name")["billed_cost"].sum().round(2).to_dict() if not df.empty else {}
        by_region = df.groupby("region_id")["billed_cost"].sum().round(2).to_dict() if not df.empty else {}
        return records, source, total_spend, by_provider, by_service, by_region

    records, source, total_spend, by_provider, by_service, by_region = await run_in_threadpool(_process)

    return {
        "period_days": days,
        "total_billed_cost_usd": round(total_spend, 2),
        "spend_by_provider": by_provider,
        "spend_by_service": by_service,
        "spend_by_region": by_region,
        "total_records_processed": len(records),
        "data_source": source,
    }


@api_router.get("/costs/focus-export")
async def export_focus_telemetry(
    days: int = Query(default=30, ge=1, le=90),
    use_mock: bool | None = None,
    limit: int = Query(default=1000, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
):
    """Export standardized FOCUS 1.0 normalized billing telemetry (paginated)."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/costs/focus-export").inc()
    records, source = await run_in_threadpool(_get_records, use_mock, days)
    page = records[offset : offset + limit]

    async def stream_records():
        yield f'{{"focus_version": "1.0", "record_count": {len(records)}, "data_source": "{source}", "records": ['
        first = True
        for rec in page:
            if not first:
                yield ","
            yield rec.model_dump_json()
            first = False
        yield "]}"

    return StreamingResponse(stream_records(), media_type="application/json")


@api_router.get("/anomalies/detect", response_model=AnomalyDetectionResponse)
async def detect_anomalies(
    days: int = Query(default=60, ge=7, le=180),
    contamination: float = Query(default=0.05, ge=0.001, le=0.5),
    use_mock: bool | None = None,
):
    """Trigger AI anomaly detection on cloud cost telemetry."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/anomalies/detect").inc()

    def _process():
        records, source = _get_records(use_mock, days)
        detector = AnomalyDetector(contamination=contamination)
        anomalies = detector.detect_anomalies(records)
        return records, source, anomalies

    records, source, anomalies = await run_in_threadpool(_process)

    return {
        "analyzed_days": days,
        "anomalies_detected_count": len(anomalies),
        "data_source": source,
        "anomalies": anomalies,
    }


@api_router.get("/forecast/predict", response_model=ForecastResponse)
async def predict_costs(
    forecast_days: int = Query(default=30, ge=7, le=90),
    use_mock: bool | None = None,
):
    """Run AI time-series forecasting model to project future cloud costs."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/forecast/predict").inc()

    def _process():
        records, source = _get_records(use_mock, 60)
        forecaster = CostForecaster(forecast_days=forecast_days)
        result = forecaster.predict_future_cost(records)
        result["data_source"] = source
        return result

    result = await run_in_threadpool(_process)
    return result


@app.get("/metrics", dependencies=[Depends(verify_api_key)])
def prometheus_metrics():
    """Prometheus metrics scraper endpoint (served from the background refresh cache).

    Protected by the same API-key gate as all /api/v1 routes so that
    cloud spend figures are not exposed to unauthenticated scrapers.
    """
    metrics_data = get_prometheus_metrics_bytes()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


# Include the API router into the main app
app.include_router(api_router)
