"""Azure Cost Management connector."""

import logging
from datetime import datetime, timedelta, timezone

from finops_engine.schema.focus_spec import ChargeCategory, CloudProvider, FocusRecord, categorize_service

logger = logging.getLogger("finops.connectors.azure")


class AzureConnector:
    """Connects to Azure Cost Management API and normalizes billing datasets to FOCUS 1.0."""

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
                ExportType,
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
                type=ExportType.USAGE,
                timeframe=TimeframeType.CUSTOM,
                time_period=QueryTimePeriod(
                    from_property=datetime.strptime(start_date, "%Y-%m-%d"),
                    to=datetime.strptime(end_date, "%Y-%m-%d"),
                ),
                dataset=QueryDataset(
                    granularity=GranularityType.DAILY,
                    aggregation={
                        "totalCost": QueryAggregation(name="PreTaxCost", function="Sum"),
                        "usageQuantity": QueryAggregation(name="UsageQuantity", function="Sum"),
                    },
                    grouping=[QueryGrouping(type="Dimension", name="ServiceName")],
                ),
            )

            result = client.query.usage(scope=scope, parameters=query)
            if not result:
                return records

            columns = [c.name for c in result.columns] if result.columns else []

            for row in result.rows or []:
                try:
                    # Normalize column names to lowercase so the lookup is
                    # case-insensitive regardless of Azure API version.
                    values = {(k or "").lower(): v for k, v in zip(columns, row, strict=False)}
                    date_str = values.get("date")
                    time_start = datetime.strptime(str(date_str), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    time_end = time_start + timedelta(days=1)
                    billed = float(values.get("totalcost") or 0.0)
                    usage_qty = float(values.get("usagequantity") or 0.0)
                    service_name = str(values.get("servicename") or "Unknown Service")

                    records.append(
                        FocusRecord(
                            provider_name=CloudProvider.AZURE,
                            publisher_name="Microsoft Azure",
                            charge_category=ChargeCategory.USAGE,
                            billed_cost=round(billed, 4),
                            effective_cost=round(billed, 4),
                            currency="USD",
                            usage_quantity=round(usage_qty, 2),
                            usage_unit="Hours",
                            service_name=service_name,
                            service_category=categorize_service(service_name),
                            region_id="global",
                            sub_account_id=self.subscription_id,
                            billing_period_start=time_start,
                            billing_period_end=time_end,
                        )
                    )
                except (TypeError, ValueError) as exc:
                    logger.warning("Skipping malformed Azure record: %s", exc)
        except Exception as e:
            logger.warning("Azure Cost Management query failed or credentials not present (%s).", e)

        return records
