"""Pydantic response models for the API endpoints."""

from pydantic import BaseModel

from finops_engine.schema.focus_spec import FocusRecord


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    focus_compliance: str
    documentation: str
    prometheus_metrics: str


class CostSummaryResponse(BaseModel):
    period_days: int
    total_billed_cost_usd: float
    spend_by_provider: dict[str, float]
    spend_by_service: dict[str, float]
    spend_by_region: dict[str, float]
    total_records_processed: int
    data_source: str


class FocusExportResponse(BaseModel):
    focus_version: str
    record_count: int
    data_source: str
    records: list[FocusRecord]


class AnomalyItem(BaseModel):
    date: str
    provider: str
    service: str
    actual_cost_usd: float
    expected_baseline_usd: float
    anomaly_excess_usd: float
    z_score: float
    severity: str
    root_cause: str


class AnomalyDetectionResponse(BaseModel):
    analyzed_days: int
    anomalies_detected_count: int
    data_source: str
    anomalies: list[AnomalyItem]


class ForecastItem(BaseModel):
    date: str
    predicted_cost_usd: float
    confidence_upper_usd: float
    confidence_lower_usd: float


class ForecastResponse(BaseModel):
    forecast_days: int
    total_projected_spend_usd: float
    average_daily_projected_usd: float
    confidence_level: str
    data_source: str
    forecast: list[ForecastItem]
