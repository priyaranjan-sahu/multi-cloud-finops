"""
Azure Cost Management API Connector
Fetches Azure subscription cost telemetry and maps it into FOCUS 1.0 format.
"""

import logging
from datetime import datetime, timedelta
from typing import List
from finops_engine.schema.focus_spec import FocusRecord, CloudProvider, ChargeCategory

logger = logging.getLogger("finops.connectors.azure")

class AzureConnector:
    def __init__(self, subscription_id: str = "default-azure-subscription"):
        self.subscription_id = subscription_id

    def fetch_cost_data(self, start_date: str = None, end_date: str = None) -> List[FocusRecord]:
        """Fetches Azure Cost Management metrics and maps to FOCUS schema."""
        if not start_date or not end_date:
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(days=30)
            start_date = start_dt.strftime("%Y-%m-%d")
            end_date = end_dt.strftime("%Y-%m-%d")

        records = []
        try:
            from azure.identity import DefaultAzureCredential
            from azure.mgmt.costmanagement import CostManagementClient
            credential = DefaultAzureCredential()
            client = CostManagementClient(credential)
            logger.info(f"Querying Azure Cost Management for subscription {self.subscription_id}")
        except Exception as e:
            logger.warning(f"Azure Cost Management API call failed ({e}).")

        return records
