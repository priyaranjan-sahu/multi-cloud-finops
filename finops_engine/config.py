"""
Application configuration, sourced from environment variables.

Every runtime knob can be overridden at deploy time without code changes:
- FINOP_MOCK_MODE          use synthetic telemetry instead of live cloud APIs (default: true)
- FINOP_ALLOW_MOCK_FALLBACK  silently fall back to synthetic data when live fetch returns nothing (default: false)
- FINOP_API_KEY            when set, all /api/* routes require an X-API-Key header
- FINOP_CORS_ORIGINS       comma-separated allow-list; empty means allow all origins
- FINOP_METRICS_REFRESH_SECONDS  how often Prometheus metrics are recomputed (default: 15)
"""

import os
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the FinOps engine."""

    mock_mode: bool = Field(default=True, validation_alias="FINOP_MOCK_MODE")
    environment: str = Field(default="development", validation_alias="FINOP_ENVIRONMENT")
    aws_region: str = Field(default="us-east-1", validation_alias="FINOP_AWS_REGION")
    aws_account_id: str = Field(default="", validation_alias="FINOP_AWS_ACCOUNT_ID")
    gcp_project_id: str = Field(default="", validation_alias="FINOP_GCP_PROJECT_ID")
    gcp_billing_table: str = Field(default="", validation_alias="FINOP_GCP_BILLING_TABLE")
    azure_subscription_id: str = Field(default="", validation_alias="FINOP_AZURE_SUBSCRIPTION_ID")
    allow_mock_fallback: bool = Field(default=False, validation_alias="FINOP_ALLOW_MOCK_FALLBACK")
    api_key: str = Field(default="", validation_alias="FINOP_API_KEY")
    cors_origins: list[str] = Field(default_factory=list, validation_alias="FINOP_CORS_ORIGINS")
    metrics_refresh_seconds: int = Field(default=15, validation_alias="FINOP_METRICS_REFRESH_SECONDS")
    license_key: str = Field(default="", validation_alias="FINOP_LICENSE_KEY")
    license_public_key: str = Field(default="", validation_alias="FINOP_LICENSE_PUBLIC_KEY")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("mock_mode", mode="before")
    @classmethod
    def parse_mock_mode(cls, v: Any) -> bool:
        if v is None:
            return True
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    @field_validator("allow_mock_fallback", mode="before")
    @classmethod
    def parse_allow_mock_fallback(cls, v: Any) -> bool:
        if v is None:
            return False
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v or []

    @field_validator("api_key", mode="before")
    @classmethod
    def parse_api_key(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v or ""

    @field_validator("metrics_refresh_seconds", mode="before")
    @classmethod
    def parse_metrics_refresh(cls, v: Any) -> int:
        if v is None:
            return 15
        try:
            val = int(str(v).strip())
            if val < 1:
                return 15
            return val
        except ValueError:
            return 15

    @field_validator(
        "environment",
        "aws_region",
        "aws_account_id",
        "gcp_project_id",
        "gcp_billing_table",
        "azure_subscription_id",
        mode="before",
    )
    @classmethod
    def strip_text(cls, v: Any) -> str:
        return str(v).strip() if v is not None else ""


settings = Settings()


def _env_bool(name: str, default: bool) -> bool:
    """Compatibility helper to parse booleans from the environment."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    """Compatibility helper to parse integers from the environment."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        return default
    if value < minimum:
        return default
    return value
