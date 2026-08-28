"""Deterministic synthetic cost telemetry generator.

Emits FOCUS records with embedded anomalies and stable resource identities
across the observation window.
"""

import random
from datetime import datetime, timedelta, timezone

from finops_engine.schema.focus_spec import ChargeCategory, CloudProvider, FocusRecord, categorize_service


class MockTelemetryConnector:
    """Generates deterministic mock telemetry with stable resource identities."""

    def __init__(self, days: int = 90, seed: int = 42) -> None:
        self.days = days
        self._rng = random.Random(seed)

    def fetch_cost_data(self) -> list[FocusRecord]:
        records: list[FocusRecord] = []
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=self.days)

        providers = [
            (CloudProvider.AWS, ["AmazonEC2", "AmazonS3", "AmazonRDS", "AmazonEKS"], "aws-prod-account"),
            (CloudProvider.GCP, ["Compute Engine", "Cloud Storage", "BigQuery", "GKE"], "gcp-analytics-project"),
            (CloudProvider.AZURE, ["Virtual Machines", "Blob Storage", "SQL Database", "AKS"], "azure-enterprise-sub"),
        ]

        current_dt = start_date
        day_counter = 0

        while current_dt <= end_date:
            day_counter += 1
            next_dt = current_dt + timedelta(days=1)

            for provider, services, sub_acc in providers:
                for service in services:
                    base_cost = self._rng.uniform(80.0, 300.0)

                    # Inject realistic cost anomalies on specific days
                    if provider == CloudProvider.AWS and service == "AmazonEC2" and day_counter in (45, 46, 47):
                        base_cost *= 4.5  # Massive unexpected EC2 spike
                    elif provider == CloudProvider.GCP and service == "BigQuery" and day_counter in (70, 71):
                        base_cost *= 3.8  # Large query spike
                    elif provider == CloudProvider.AZURE and service == "Virtual Machines" and day_counter in (25, 26):
                        base_cost *= 3.0  # Azure VM runaway instance spike

                    effective = base_cost * self._rng.uniform(0.85, 0.98)
                    usage = self._rng.uniform(10.0, 240.0)
                    service_slug = service.lower().replace(" ", "-")
                    resource_id = f"{provider.value.lower()}-{service_slug}-prod-001"

                    records.append(
                        FocusRecord(
                            provider_name=provider,
                            publisher_name=f"{provider.value} Infrastructure",
                            charge_category=ChargeCategory.USAGE,
                            billed_cost=round(base_cost, 2),
                            effective_cost=round(effective, 2),
                            currency="USD",
                            usage_quantity=round(usage, 2),
                            usage_unit="Hours",
                            service_name=service,
                            service_category=categorize_service(service),
                            region_id="us-east-1"
                            if provider == CloudProvider.AWS
                            else ("us-central1" if provider == CloudProvider.GCP else "eastus"),
                            sub_account_id=sub_acc,
                            resource_id=resource_id,
                            billing_period_start=current_dt,
                            billing_period_end=next_dt,
                        )
                    )

            current_dt = next_dt

        return records
