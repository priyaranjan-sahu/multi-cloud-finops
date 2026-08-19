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


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    """Runtime settings for the FinOps engine."""

    def __init__(self) -> None:
        self.mock_mode: bool = _env_bool("FINOP_MOCK_MODE", True)
        self.allow_mock_fallback: bool = _env_bool("FINOP_ALLOW_MOCK_FALLBACK", False)
        self.api_key: str = os.getenv("FINOP_API_KEY", "").strip()
        self.cors_origins: list[str] = [
            origin.strip() for origin in os.getenv("FINOP_CORS_ORIGINS", "").split(",") if origin.strip()
        ]
        self.metrics_refresh_seconds: int = int(os.getenv("FINOP_METRICS_REFRESH_SECONDS", "15"))


settings = Settings()