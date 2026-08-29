"""Change Intelligence and Deployment-to-Cost Attribution Engine."""

from typing import Any

from finops_engine.schema.deployment_event import DeploymentEvent
from finops_engine.schema.focus_spec import FocusRecord, normalize_to_focus_dataframe


class ChangeIntelligenceEngine:
    """Correlates infrastructure deployment events with cost baseline shifts."""

    def __init__(self, correlation_window_days: int = 7, min_shift_threshold_usd: float = 10.0) -> None:
        self.correlation_window_days = correlation_window_days
        self.min_shift_threshold_usd = min_shift_threshold_usd

    def attribute_cost_changes(
        self,
        records: list[FocusRecord],
        events: list[DeploymentEvent],
    ) -> list[dict[str, Any]]:
        """Correlates spend shifts with recent deployment events."""
        if not records or not events:
            return []

        df = normalize_to_focus_dataframe(records)
        if df.empty:
            return []

        df["date"] = df["billing_period_start"].dt.date
        resource_daily = (
            df.groupby(["resource_id", "provider_name", "service_name", "date"])["billed_cost"].sum().reset_index()
        )
        resource_daily = resource_daily.sort_values(["resource_id", "date"]).reset_index(drop=True)

        attributions: list[dict[str, Any]] = []

        # Analyze each resource for cost shifts
        for (resource_id, provider, service), group in resource_daily.groupby(
            ["resource_id", "provider_name", "service_name"]
        ):
            if not resource_id or len(group) < 2:
                continue

            # Check for baseline increase
            earlier_mean = float(group.iloc[:-1]["billed_cost"].mean())
            latest_cost = float(group.iloc[-1]["billed_cost"])
            latest_date = group.iloc[-1]["date"]
            shift_usd = round(latest_cost - earlier_mean, 2)
            monthly_impact_usd = round(shift_usd * 30.0, 2)

            if shift_usd < self.min_shift_threshold_usd and monthly_impact_usd < self.min_shift_threshold_usd:
                continue

            # Find candidate deployment events for this resource or service
            for event in events:
                event_date = event.timestamp.date()
                days_diff = (latest_date - event_date).days

                # Ensure event occurred prior to or on the shift date within window
                if 0 <= days_diff <= self.correlation_window_days:
                    # Match exact resource or service
                    is_exact_resource = event.resource_id == str(resource_id)
                    is_same_service = (
                        event.service_name.lower() in str(service).lower()
                        or str(service).lower() in event.service_name.lower()
                    )

                    if not (is_exact_resource or is_same_service):
                        continue

                    # Determine confidence
                    if is_exact_resource and days_diff <= 2:
                        confidence = "HIGH"
                    elif is_exact_resource or (is_same_service and days_diff <= 3):
                        confidence = "MEDIUM"
                    else:
                        confidence = "LOW"

                    author_str = f" by {event.author}" if event.author else ""
                    commit_str = f" (commit {event.commit_sha[:7]})" if event.commit_sha else ""

                    narrative = (
                        f"{provider} {service} '{resource_id}' shifted spend by "
                        f"+${monthly_impact_usd:.2f}/mo following deployment '{event.event_id}'"
                        f"{author_str}{commit_str}: {event.change_summary}"
                    )

                    remediation = f"Review configuration changes in {event.change_summary} and revert if unintended."

                    attributions.append(
                        {
                            "attribution_id": f"ATTR-{event.event_id}-{str(resource_id)[:8]}",
                            "resource_id": str(resource_id),
                            "provider": str(provider),
                            "service": str(service),
                            "cost_shift_daily_usd": shift_usd,
                            "estimated_monthly_impact_usd": monthly_impact_usd,
                            "confidence": confidence,
                            "detected_date": str(latest_date),
                            "deployment_event": event.to_dict(),
                            "root_cause_narrative": narrative,
                            "actionable_remediation": remediation,
                        }
                    )

        return sorted(attributions, key=lambda x: x["estimated_monthly_impact_usd"], reverse=True)
