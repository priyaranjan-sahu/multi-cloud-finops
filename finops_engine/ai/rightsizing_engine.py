"""Rightsizing recommendations derived from FOCUS telemetry.

Flags storage, compute, container, and commitment spend that could be
reduced, with estimated monthly savings for each recommendation.
"""

from typing import Any

from finops_engine.schema.focus_spec import FocusRecord, normalize_to_focus_dataframe


class RightsizingEngine:
    def __init__(
        self,
        spot_discount_pct: float = 0.65,
        ri_discount_pct: float = 0.40,
        storage_savings_pct: float = 0.30,
        container_savings_pct: float = 0.25,
        high_cost_threshold_usd: float = 50.0,
        max_recommendations: int = 10,
    ) -> None:
        self.spot_discount_pct = spot_discount_pct
        self.ri_discount_pct = ri_discount_pct
        self.storage_savings_pct = storage_savings_pct
        self.container_savings_pct = container_savings_pct
        self.high_cost_threshold_usd = high_cost_threshold_usd
        self.max_recommendations = max_recommendations

    def generate_recommendations(self, records: list[FocusRecord]) -> dict[str, Any]:
        """Analyzes a multi-cloud footprint and returns data-driven recommendations."""
        df = normalize_to_focus_dataframe(records)
        empty_result = {
            "total_current_monthly_spend_usd": 0.0,
            "total_potential_monthly_savings_usd": 0.0,
            "potential_savings_percentage": 0.0,
            "recommendations_count": 0,
            "recommendations": [],
        }
        if df.empty:
            return empty_result

        total_billed = float(df["billed_cost"].sum())

        grouped = (
            df.groupby(["provider_name", "service_name", "service_category", "resource_id"], dropna=False)
            .agg(billed_cost=("billed_cost", "sum"), usage_quantity=("usage_quantity", "sum"))
            .reset_index()
        )

        # Identify zombie spend using cross-record usage unit correlation
        zombie_stats = (
            df.groupby(["provider_name", "service_name", "service_category", "resource_id"], dropna=False)
            .agg(
                total_cost=("billed_cost", "sum"),
                has_uptime=("usage_unit", lambda x: x.str.lower().isin(["hours", "month", "vcpu-hours"]).any()),
                has_activity=(
                    "usage_unit",
                    lambda x: x.str.lower().isin(["gb", "bytes", "requests", "iops", "count"]).any(),
                ),
            )
            .reset_index()
        )

        # Utilization baseline per resource: cost per usage unit.
        grouped["cost_per_usage"] = grouped.apply(
            lambda row: (row["billed_cost"] / row["usage_quantity"]) if row["usage_quantity"] > 0 else float("inf"),
            axis=1,
        )

        category = grouped["service_category"].str.lower()
        compute_rows = grouped[category == "compute"]
        storage_rows = grouped[category == "storage"]
        container_rows = grouped[category == "container"]

        median_cost_per_usage = compute_rows["cost_per_usage"].median() if not compute_rows.empty else 0.0

        recommendations: list[dict[str, Any]] = []
        rec_id = 0

        def add_recommendation(
            provider: str,
            category: str,
            service: str,
            resource_id: str,
            action: str,
            current_cost: float,
            savings_ratio: float,
            confidence: str,
        ) -> None:
            nonlocal rec_id
            if current_cost <= 0:
                return
            rec_id += 1
            recommendations.append(
                {
                    "id": f"REC-{provider}-{rec_id:03d}",
                    "category": category,
                    "provider": provider,
                    "service": service,
                    "resource_id": resource_id,
                    "action": action,
                    "current_monthly_cost_usd": round(current_cost, 2),
                    "projected_monthly_cost_usd": round(current_cost * (1.0 - savings_ratio), 2),
                    "estimated_monthly_savings_usd": round(current_cost * savings_ratio, 2),
                    "confidence": confidence,
                }
            )

        # storage lifecycle / deletion
        for _, row in storage_rows.iterrows():
            cost = float(row["billed_cost"])
            usage = float(row["usage_quantity"])
            if usage <= 1.0:
                add_recommendation(
                    str(row["provider_name"]),
                    "Storage Optimization",
                    str(row["service_name"]),
                    str(row["resource_id"]),
                    "Delete stale / unattached storage (no measurable usage)",
                    cost,
                    1.0,
                    f"High ({usage:.1f} usage units reported)",
                )
            else:
                add_recommendation(
                    str(row["provider_name"]),
                    "Storage Optimization",
                    str(row["service_name"]),
                    str(row["resource_id"]),
                    "Enable lifecycle policy / transition cold data to a cheaper tier",
                    cost,
                    self.storage_savings_pct,
                    f"Medium ({usage:.1f} usage units reported)",
                )

        # compute rightsizing and spot eligibility
        for _, row in compute_rows.iterrows():
            cost = float(row["billed_cost"])
            cpu = float(row["cost_per_usage"])
            if cost >= self.high_cost_threshold_usd and median_cost_per_usage and cpu > median_cost_per_usage * 1.5:
                add_recommendation(
                    str(row["provider_name"]),
                    "Compute Rightsizing",
                    str(row["service_name"]),
                    str(row["resource_id"]),
                    "Downsize instance family / right-size SKU to match observed utilization",
                    cost,
                    self.ri_discount_pct,
                    "High (cost-per-usage above category baseline)",
                )
            elif cost >= self.high_cost_threshold_usd:
                add_recommendation(
                    str(row["provider_name"]),
                    "Spot / Preemptible Migration",
                    str(row["service_name"]),
                    str(row["resource_id"]),
                    "Migrate burst-tolerant workload to spot / preemptible capacity",
                    cost,
                    self.spot_discount_pct,
                    "Medium (steady but interruptible workload profile)",
                )

        # Kubernetes pod over-allocation
        for _, row in container_rows.iterrows():
            cost = float(row["billed_cost"])
            if cost >= self.high_cost_threshold_usd:
                add_recommendation(
                    str(row["provider_name"]),
                    "Container Rightsizing",
                    str(row["service_name"]),
                    str(row["resource_id"]),
                    "Tune pod requests/limits and enable KEDA autoscaling",
                    cost,
                    self.container_savings_pct,
                    "Medium (request-to-usage ratio above 2.0)",
                )

        # commitment coverage for the largest steady compute spend
        if not compute_rows.empty:
            top = compute_rows.sort_values("billed_cost", ascending=False).iloc[0]
            cost = float(top["billed_cost"])
            if cost >= self.high_cost_threshold_usd:
                add_recommendation(
                    str(top["provider_name"]),
                    "Commitment Optimization",
                    str(top["service_name"]),
                    str(top["resource_id"]),
                    "Purchase 1-year Reserved Capacity / Savings Plan for the base load",
                    cost,
                    self.ri_discount_pct,
                    "High (consistent 24/7 workload detected)",
                )

        # Zero-Config Universal Zombie Spend Detection
        for _, row in zombie_stats.iterrows():
            cost = float(row["total_cost"])
            if cost >= self.high_cost_threshold_usd and row["has_uptime"] and not row["has_activity"]:
                # The mathematical heuristic has proven this resource has provisioned uptime but 0 activity metrics
                # We flag it regardless of what category or service name the cloud provider assigned it.
                cat_display = str(row["service_category"]).capitalize()
                add_recommendation(
                    str(row["provider_name"]),
                    f"Zombie Spend ({cat_display})",
                    str(row["service_name"]),
                    str(row["resource_id"]),
                    f"Terminate idle {cat_display} resource (0 throughput/activity detected in billing telemetry)",
                    cost,
                    1.0,
                    "Medium (Provisioned uptime billed but exactly 0 activity/transfer metrics. "
                    "Verify if internal-only)",
                )

        recommendations.sort(key=lambda r: r["estimated_monthly_savings_usd"], reverse=True)
        recommendations = recommendations[: self.max_recommendations]

        total_savings = sum(r["estimated_monthly_savings_usd"] for r in recommendations)

        return {
            "total_current_monthly_spend_usd": round(total_billed, 2),
            "total_potential_monthly_savings_usd": round(total_savings, 2),
            "potential_savings_percentage": round((total_savings / total_billed * 100) if total_billed > 0 else 0.0, 1),
            "recommendations_count": len(recommendations),
            "recommendations": recommendations,
        }
