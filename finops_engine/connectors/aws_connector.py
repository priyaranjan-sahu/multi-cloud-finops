"""
AWS Billing & Cost Explorer Connector
Fetches AWS cost telemetry and maps it into FOCUS 1.0 normalized records.
"""

import logging
from datetime import datetime, timedelta, timezone

from finops_engine.schema.focus_spec import ChargeCategory, CloudProvider, FocusRecord

logger = logging.getLogger("finops.connectors.aws")


class AWSConnector:
    def __init__(self, region_name: str = "us-east-1"):
        self.region_name = region_name

    def fetch_cost_data(self, start_date: str | None = None, end_date: str | None = None) -> list[FocusRecord]:
        """Fetches AWS Cost Explorer metrics and maps to FOCUS schema."""
        if not start_date or not end_date:
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=30)
            start_date = start_dt.strftime("%Y-%m-%d")
            end_date = end_dt.strftime("%Y-%m-%d")

        records: list[FocusRecord] = []
        try:
            import boto3

            client = boto3.client("ce", region_name=self.region_name)
            response = client.get_cost_and_usage(
                TimePeriod={"Start": start_date, "End": end_date},
                Granularity="DAILY",
                Metrics=["UnblendedCost", "AmortizedCost", "UsageQuantity"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )

            for result in response.get("ResultsByTime", []):
                time_start = datetime.strptime(result["TimePeriod"]["Start"], "%Y-%m-%d")
                time_end = datetime.strptime(result["TimePeriod"]["End"], "%Y-%m-%d")
                for group in result.get("Groups", []):
                    service_name = group["Keys"][0]
                    metrics = group["Metrics"]
                    billed = float(metrics.get("UnblendedCost", {}).get("Amount", 0.0))
                    effective = float(metrics.get("AmortizedCost", {}).get("Amount", billed))
                    usage_qty = float(metrics.get("UsageQuantity", {}).get("Amount", 0.0))

                    records.append(
                        FocusRecord(
                            provider_name=CloudProvider.AWS,
                            publisher_name="Amazon Web Services",
                            charge_category=ChargeCategory.USAGE,
                            billed_cost=round(billed, 4),
                            effective_cost=round(effective, 4),
                            currency="USD",
                            usage_quantity=round(usage_qty, 2),
                            usage_unit="Hours",
                            service_name=service_name,
                            service_category="Compute" if "EC2" in service_name else "Storage",
                            region_id=self.region_name,
                            sub_account_id="aws-account-main",
                            billing_period_start=time_start,
                            billing_period_end=time_end,
                        )
                    )
        except Exception as e:
            logger.warning("AWS Cost Explorer call failed or credentials not present (%s).", e)

        return records
