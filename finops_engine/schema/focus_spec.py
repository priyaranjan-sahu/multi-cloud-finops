"""FOCUS 1.0 schema types and normalization helpers."""

from datetime import datetime
from enum import Enum

import pandas as pd
from pydantic import BaseModel, Field


class ChargeCategory(str, Enum):
    USAGE = "Usage"
    PURCHASE = "Purchase"
    TAX = "Tax"
    CREDIT = "Credit"
    ADJUSTMENT = "Adjustment"


class CloudProvider(str, Enum):
    AWS = "AWS"
    GCP = "GCP"
    AZURE = "Azure"


def categorize_service(service: str) -> str:
    """Map a cloud service name to a coarse FOCUS service category.

    Shared by every connector (mock, AWS, GCP, Azure) so that live telemetry
    and synthetic telemetry produce identical categorization. This keeps the
    rightsizing engine's waste-vector detection (storage / compute /
    container / database / network) consistent across providers.
    """
    lowered = service.lower()
    if any(key in lowered for key in ("storage", "s3", "blob", "disk")):
        return "Storage"
    if any(
        key in lowered
        for key in (
            "database",
            "sql",
            "rds",
            "bigquery",
            "cosmos",
            "dynamodb",
            "spanner",
            "redshift",
            "elasticache",
            "cache",
        )
    ):
        return "Database"
    if any(key in lowered for key in ("eks", "gke", "aks", "kubernetes", "ecs", "container")):
        return "Container"
    if any(
        key in lowered
        for key in (
            "vpc",
            "vnet",
            "cdn",
            "cloudfront",
            "load balancer",
            "network",
            "route 53",
            "firewall",
            "nat",
            "gateway",
        )
    ):
        return "Network"
    return "Compute"


class FocusRecord(BaseModel):
    """Represents a single FOCUS 1.0 compliant billing record."""

    provider_name: CloudProvider = Field(..., description="AWS, GCP, or Azure")
    publisher_name: str = Field(default="Cloud Provider", description="Entity publishing the bill")
    charge_category: ChargeCategory = Field(default=ChargeCategory.USAGE)
    billed_cost: float = Field(..., description="Raw cost billed before adjustments (negative for credits)")
    effective_cost: float = Field(..., description="Net cost including amortized commitments")
    currency: str = Field(default="USD")
    usage_quantity: float = Field(default=0.0, ge=0.0)
    usage_unit: str = Field(default="Hours")
    service_name: str = Field(..., description="EC2, Compute Engine, Virtual Machines, S3, etc.")
    service_category: str = Field(default="Compute", description="Compute, Storage, Database, Network")
    region_id: str = Field(default="global", description="us-east-1, us-central1, eastus, etc.")
    sub_account_id: str = Field(
        default="default-account", description="AWS Account ID, GCP Project ID, Azure Subscription ID"
    )
    resource_id: str | None = Field(default=None, description="ARN, instance ID, or resource URI")
    billing_period_start: datetime = Field(...)
    billing_period_end: datetime = Field(...)

    def to_dict(self) -> dict:
        """Serialize the record to a JSON-friendly dictionary."""
        return self.model_dump(mode="json")


def normalize_to_focus_dataframe(records: list[FocusRecord]) -> pd.DataFrame:
    """Converts a list of FocusRecord objects into a normalized pandas DataFrame."""
    if not records:
        return pd.DataFrame(
            columns=[
                "provider_name",
                "publisher_name",
                "charge_category",
                "billed_cost",
                "effective_cost",
                "currency",
                "usage_quantity",
                "usage_unit",
                "service_name",
                "service_category",
                "region_id",
                "sub_account_id",
                "resource_id",
                "billing_period_start",
                "billing_period_end",
            ]
        )

    dict_list = [r.to_dict() for r in records]
    df = pd.DataFrame(dict_list)
    df["billing_period_start"] = pd.to_datetime(df["billing_period_start"])
    df["billing_period_end"] = pd.to_datetime(df["billing_period_end"])
    return df
