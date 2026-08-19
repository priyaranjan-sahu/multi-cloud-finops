"""
Multi-Cloud Spot Instance Optimization CLI
Analyzes compute workloads and estimates savings from spot / preemptible migration.
"""

import argparse

from finops_engine.connectors import MockTelemetryConnector
from finops_engine.schema import normalize_to_focus_dataframe


def analyze_spot_opportunities(days: int = 30, discount_pct: float = 0.65) -> dict:
    print(f"🚀 Analyzing {days}-day spot / preemptible optimization opportunities...")
    connector = MockTelemetryConnector(days=days)
    records = connector.fetch_cost_data()
    df = normalize_to_focus_dataframe(records)

    compute = df[df["service_category"].str.lower().isin(["compute", "container"])]
    if compute.empty:
        print("⚠️ No compute workloads found in telemetry.")
        return {"evaluated_workloads": 0, "total_compute_spend_usd": 0.0, "estimated_spot_savings_usd": 0.0}

    total_compute = float(compute["billed_cost"].sum())
    by_provider = compute.groupby("provider_name")["billed_cost"].sum().round(2).to_dict()
    savings = round(total_compute * discount_pct, 2)

    print(f"✅ Evaluated {len(compute)} compute workload records across AWS, GCP, and Azure.")
    print(f"💡 Total Compute On-Demand Spend: ${total_compute:,.2f}")
    print(f"💰 Estimated Savings via Spot/Preemptible Migration ({int(discount_pct * 100)}% discount): ${savings:,.2f}/mo")
    print(f"📊 Spend by Provider: {by_provider}")

    return {
        "evaluated_workloads": int(len(compute)),
        "total_compute_spend_usd": round(total_compute, 2),
        "estimated_spot_savings_usd": savings,
        "spend_by_provider_usd": by_provider,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze multi-cloud spot / preemptible savings opportunities")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--discount-pct", type=float, default=0.65)
    args = parser.parse_args()
    analyze_spot_opportunities(days=args.days, discount_pct=args.discount_pct)