"""
GCP Billing Connector
Fetches Google Cloud cost telemetry from the BigQuery billing export
and normalizes it into FOCUS 1.0 format.
"""

import logging
from datetime import datetime, timedelta, timezone

from finops_engine.schema.focus_spec import ChargeCategory, CloudProvider, FocusRecord, categorize_service

logger = logging.getLogger("finops.connectors.gcp")


class GCPConnector:
    def __init__(self, project_id: str = "default-gcp-project", billing_table: str | None = None):
        self.project_id = project_id
        self.billing_table = billing_table or f"{project_id}.billing.gcp_billing_export_v1"

    def fetch_cost_data(self, start_date: str | None = None, end_date: str | None = None) -> list[FocusRecord]:
        """Fetches GCP billing metrics from the BigQuery export and maps to FOCUS schema."""
        if not start_date or not end_date:
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=30)
            start_date = start_dt.strftime("%Y-%m-%d")
            end_date = end_dt.strftime("%Y-%m-%d")

        records: list[FocusRecord] = []
        try:
            from google.cloud import bigquery

            client = bigquery.Client(project=self.project_id)
            # LEFT JOIN UNNEST keeps usage lines that carry no credits (a
            # CROSS JOIN would silently drop them), and SUM()/GROUP BY folds
            # multiple credit rows for one usage line into a single record.
            query = f"""
                SELECT
                    service.description          AS service_name,
                    MIN(usage_start_time)        AS usage_start,
                    MAX(usage_end_time)          AS usage_end,
                    SUM(cost)                    AS billed_cost,
                    SUM(COALESCE(credits.amount, 0.0)) AS credit_amount,
                    SUM(usage.amount)            AS usage_quantity,
                    ANY_VALUE(usage.unit)        AS usage_unit,
                    project.name                 AS project_name,
                    resource.name                AS resource_name
                FROM `{self.billing_table}`
                LEFT JOIN UNNEST(credits) AS credits
                WHERE DATE(usage_start_time) BETWEEN @start_date AND @end_date
                GROUP BY service.description, project.name, resource.name, DATE(usage_start_time)
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("start_date", "STRING", start_date),
                    bigquery.ScalarQueryParameter("end_date", "STRING", end_date),
                ]
            )
            rows = client.query(query, job_config=job_config)

            for row in rows:
                try:
                    billed = float(row.get("billed_cost") or 0.0)
                    credit = float(row.get("credit_amount") or 0.0)
                    effective = round(billed - credit, 4)
                    service_name = str(row.get("service_name") or "Unknown Service")

                    records.append(
                        FocusRecord(
                            provider_name=CloudProvider.GCP,
                            publisher_name="Google Cloud",
                            charge_category=ChargeCategory.USAGE,
                            billed_cost=round(billed, 4),
                            effective_cost=effective,
                            currency="USD",
                            usage_quantity=round(float(row.get("usage_quantity") or 0.0), 2),
                            usage_unit=str(row.get("usage_unit") or "Hours"),
                            service_name=service_name,
                            service_category=categorize_service(service_name),
                            region_id="global",
                            sub_account_id=str(row.get("project_name") or self.project_id),
                            resource_id=str(row.get("resource_name") or None),
                            billing_period_start=row.get("usage_start"),
                            billing_period_end=row.get("usage_end"),
                        )
                    )
                except (TypeError, ValueError) as exc:
                    logger.warning("Skipping malformed GCP record for %s: %s", service_name, exc)
        except Exception as e:
            logger.warning("GCP BigQuery billing export query failed or credentials not present (%s).", e)

        return records
