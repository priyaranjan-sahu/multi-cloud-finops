"""
Mock Telemetry Generator Connector
Generates realistic 90-day FOCUS 1.0 compliant multi-cloud cost data with embedded anomalies and idle waste vectors.
"""

from datetime import datetime, timedelta
import random
from typing import List
from finops_engine.schema.focus_spec import FocusRecord, CloudProvider, ChargeCategory

class MockTelemetryConnector:
    def __init__(self, days: int = 90, seed: int = 42):
        self.days = days
        random.seed(seed)

    def fetch_cost_data(self) -> List[FocusRecord]:
        records = []
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=self.days)

        providers = [
            (CloudProvider.AWS, ["AmazonEC2", "AmazonS3", "AmazonRDS", "AmazonEKS"], "aws-prod-account"),
            (CloudProvider.GCP, ["Compute Engine", "Cloud Storage", "BigQuery", "GKE"], "gcp-analytics-project"),
            (CloudProvider.AZURE, ["Virtual Machines", "Blob Storage", "SQL Database", "AKS"], "azure-enterprise-sub")
        ]

        current_dt = start_date
        day_counter = 0

        while current_dt <= end_date:
            day_counter += 1
            next_dt = current_dt + timedelta(days=1)

            for provider, services, sub_acc in providers:
                for service in services:
                    base_cost = random.uniform(80.0, 300.0)
                    
                    # Inject realistic cost anomalies on specific days
                    if provider == CloudProvider.AWS and service == "AmazonEC2" and day_counter in [45, 46, 47]:
                        base_cost *= 4.5  # Massive unexpected EC2 spike
                    elif provider == CloudProvider.GCP and service == "BigQuery" and day_counter in [70, 71]:
                        base_cost *= 3.8  # Large query spike
                    elif provider == CloudProvider.AZURE and service == "Virtual Machines" and day_counter in [25, 26]:
                        base_cost *= 3.0  # Azure VM runaway instance spike

                    effective = base_cost * random.uniform(0.85, 0.98)
                    usage = random.uniform(10.0, 240.0)

                    records.append(FocusRecord(
                        provider_name=provider,
                        publisher_name=f"{provider.value} Infrastructure",
                        charge_category=ChargeCategory.USAGE,
                        billed_cost=round(base_cost, 2),
                        effective_cost=round(effective, 2),
                        currency="USD",
                        usage_quantity=round(usage, 2),
                        usage_unit="Hours",
                        service_name=service,
                        service_category="Compute" if "Storage" not in service else "Storage",
                        region_id="us-east-1" if provider == CloudProvider.AWS else ("us-central1" if provider == CloudProvider.GCP else "eastus"),
                        sub_account_id=sub_acc,
                        resource_id=f"{service.lower()}-inst-{random.randint(100, 999)}",
                        billing_period_start=current_dt,
                        billing_period_end=next_dt
                    ))

            current_dt = next_dt

        return records
