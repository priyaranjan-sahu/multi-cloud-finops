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

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader

from finops_engine import __version__
from finops_engine.ai import AnomalyDetector, ChangeIntelligenceEngine, CostForecaster, RightsizingEngine
from finops_engine.api.models import (
    AnomalyDetectionResponse,
    ChangeAttributionResponse,
    CostSummaryResponse,
    DeploymentEventCreateRequest,
    DeploymentEventListResponse,
    ForecastResponse,
    HealthResponse,
    RightsizingResponse,
)
from finops_engine.config import settings
from finops_engine.connectors import fetch_multicloud_cost
from finops_engine.connectors.mock_connector import MockTelemetryConnector
from finops_engine.errors import ConnectorError, LicenseError
from finops_engine.exporter import (
    CONTENT_TYPE_LATEST,
    FINOPS_REQUEST_COUNTER,
    get_prometheus_metrics_bytes,
    refresh_finops_metrics_loop,
)
from finops_engine.license import verify_pro_license
from finops_engine.schema import normalize_to_focus_dataframe
from finops_engine.schema.deployment_event import DeploymentEvent

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


@app.exception_handler(LicenseError)
async def license_error_handler(_request: Request, exc: LicenseError) -> Response:
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=402, content={"detail": str(exc)})


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


@api_router.get("/recommendations/rightsizing", response_model=RightsizingResponse)
async def get_rightsizing_recommendations(use_mock: bool | None = None):
    """Fetch actionable rightsizing and waste reduction recommendations."""
    verify_pro_license("Rightsizing API")
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/recommendations/rightsizing").inc()

    def _process():
        records, source = _get_records(use_mock, 30)
        engine = RightsizingEngine()
        result = engine.generate_recommendations(records)
        result["data_source"] = source
        return result

    result = await run_in_threadpool(_process)
    return result


_deployment_events_store: list[DeploymentEvent] = []


@api_router.post("/events/deployments")
async def register_deployment_event(request: DeploymentEventCreateRequest):
    """Ingest a deployment event from CI/CD webhooks or audit logs."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/events/deployments").inc()
    event = DeploymentEvent(
        provider=request.provider,
        service_name=request.service_name,
        resource_id=request.resource_id,
        environment=request.environment,
        commit_sha=request.commit_sha,
        author=request.author,
        change_summary=request.change_summary,
        diff_metadata=request.diff_metadata,
    )
    _deployment_events_store.append(event)
    return {"status": "recorded", "event_id": event.event_id, "event": event.to_dict()}


@api_router.get("/events/deployments", response_model=DeploymentEventListResponse)
async def list_deployment_events(use_mock: bool | None = None):
    """List registered deployment events."""
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/events/deployments").inc()
    mock_mode = settings.mock_mode if use_mock is None else use_mock
    events = list(_deployment_events_store)
    if mock_mode and not events:
        events.extend(MockTelemetryConnector().fetch_deployment_events())
    return {"events_count": len(events), "events": [e.to_dict() for e in events]}


@api_router.get("/intelligence/change-attribution", response_model=ChangeAttributionResponse)
async def get_change_attribution(
    days: int = Query(default=30, ge=7, le=90),
    correlation_window_days: int = Query(default=7, ge=1, le=30),
    use_mock: bool | None = None,
):
    """Run Change Intelligence to attribute cost shifts directly to deployment events."""
    verify_pro_license("Change Intelligence API")
    FINOPS_REQUEST_COUNTER.labels(endpoint="/api/v1/intelligence/change-attribution").inc()

    def _process():
        records, source = _get_records(use_mock, days)
        events = list(_deployment_events_store)
        mock_mode = settings.mock_mode if use_mock is None else use_mock
        if (mock_mode or not events) and source in ("mock", "mock-fallback"):
            events.extend(MockTelemetryConnector().fetch_deployment_events())

        engine = ChangeIntelligenceEngine(correlation_window_days=correlation_window_days)
        attributions = engine.attribute_cost_changes(records, events)
        total_impact = round(sum(item["estimated_monthly_impact_usd"] for item in attributions), 2)
        return attributions, total_impact, source

    attributions, total_impact, source = await run_in_threadpool(_process)

    return {
        "total_attributions_count": len(attributions),
        "total_monthly_impact_usd": total_impact,
        "data_source": source,
        "attributions": attributions,
    }


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
