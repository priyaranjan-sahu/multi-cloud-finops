"""
Azure Cost Management Connector
Fetches Azure subscription cost telemetry via the Cost Management query API
and maps it into FOCUS 1.0 format.
"""

import logging
from datetime import datetime, timedelta, timezone

from finops_engine.schema.focus_spec import ChargeCategory, CloudProvider, FocusRecord

logger = logging.getLogger("finops.connectors.azure")


class AzureConnector:
    def __init__(self, subscription_id: str = "default-azure-subscription"):
        self.subscription_id = subscription_id

    def fetch_cost_data(self, start_date: str | None = None, end_date: str | None = None) -> list[FocusRecord]:
        """Fetches Azure Cost Management metrics and maps to FOCUS schema."""
        if not start_date or not end_date:
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=30)
            start_date = start_dt.strftime("%Y-%m-%d")
            end_date = end_dt.strftime("%Y-%m-%d")

        records: list[FocusRecord] = []
        try:
            from azure.identity import DefaultAzureCredential
            from azure.mgmt.costmanagement import CostManagementClient
            from azure.mgmt.costmanagement.models import (
                GranularityType,
                QueryAggregation,
                QueryDataset,
                QueryDefinition,
                QueryGrouping,
                QueryTimePeriod,
                TimeframeType,
            )

            credential = DefaultAzureCredential()
            client = CostManagementClient(credential)
            scope = f"/subscriptions/{self.subscription_id}"

            query = QueryDefinition(
                timeframe=TimeframeType.CUSTOM,
                time_period=QueryTimePeriod(from_property=start_date, to=end_date),
                dataset=QueryDataset(
                    granularity=GranularityType.DAILY,
                    aggregation={"totalCost": QueryAggregation(name="PreTaxCost", function="Sum")},
                    grouping=[QueryGrouping(type="Dimension", name="ServiceName")],
                ),
            )

            result = client.query.usage(scope=scope, parameters=query)
            columns = [c["name"] for c in result.columns] if result.columns else []

            for row in result.rows or []:
                values = dict(zip(columns, row, strict=False))
                date_str = values.get("date")
                time_start = datetime.strptime(str(date_str), "%Y-%m-%d")
                time_end = time_start + timedelta(days=1)
                billed = float(values.get("totalCost") or 0.0)
                service_name = str(values.get("ServiceName") or "Unknown Service")

                records.append(
                    FocusRecord(
                        provider_name=CloudProvider.AZURE,
                        publisher_name="Microsoft Azure",
                        charge_category=ChargeCategory.USAGE,
                        billed_cost=round(billed, 4),
                        effective_cost=round(billed, 4),
                        currency="USD",
                        usage_quantity=0.0,
                        usage_unit="Hours",
                        service_name=service_name,
                        service_category="Compute" if "Virtual Machines" in service_name else "Storage",
                        region_id="global",
                        sub_account_id=self.subscription_id,
                        billing_period_start=time_start,
                        billing_period_end=time_end,
                    )
                )
        except Exception as e:
            logger.warning("Azure Cost Management query failed or credentials not present (%s).", e)

        return records
