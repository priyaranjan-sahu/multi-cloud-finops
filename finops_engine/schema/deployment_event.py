"""Deployment event schema for Change-to-Cost Attribution."""

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from finops_engine.schema.focus_spec import CloudProvider


class DeploymentEvent(BaseModel):
    """Represents a configuration change or deployment event."""

    event_id: str = Field(default_factory=lambda: f"DEP-{uuid.uuid4().hex[:8].upper()}")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the deployment event",
    )
    provider: CloudProvider = Field(default=CloudProvider.GCP, description="Cloud or platform provider")
    service_name: str = Field(..., description="Target service, e.g., Cloud Run, Lambda, EC2")
    resource_id: str = Field(..., description="Unique resource ARN, URI, or ID")
    environment: str = Field(default="production", description="Environment: production, staging, load-test, dev")
    commit_sha: str | None = Field(default=None, description="Git commit hash")
    author: str | None = Field(default=None, description="Author or service account")
    change_summary: str = Field(..., description="Short summary of the change, e.g. min-instances 0 -> 1")
    diff_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured key-value configuration changes",
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize event to a JSON-compatible dictionary."""
        return self.model_dump(mode="json")
