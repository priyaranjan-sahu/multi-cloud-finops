"""
Rightsizing Recommendations CLI
Runs multi-cloud compute, storage, and container waste analysis.
"""

import argparse

from finops_engine.ai import RightsizingEngine
from finops_engine.connectors import MockTelemetryConnector


def run_rightsizing_analysis(days: int = 30) -> dict:
    print(f"⚡ Running {days}-day Multi-Cloud Rightsizing & Waste Vector Analysis...")
    connector = MockTelemetryConnector(days=days)
    records = connector.fetch_cost_data()

    engine = RightsizingEngine()
    results = engine.generate_recommendations(records)

    print(f"\n💡 Current Monthly Spend: ${results['total_current_monthly_spend_usd']:,.2f}")
    print(
        f"💰 Potential Monthly Savings: ${results['total_potential_monthly_savings_usd']:,.2f} "
        f"({results['potential_savings_percentage']}%)"
    )
    print("\nActionable Recommendations:")
    for rec in results["recommendations"]:
        print(
            f"   [{rec['id']}] {rec['provider']} | {rec['category']}: {rec['action']} -> "
            f"Save ${rec['estimated_monthly_savings_usd']}/mo"
        )

    print("\n✅ Rightsizing Recommendations execution completed successfully.")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate multi-cloud rightsizing recommendations")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    run_rightsizing_analysis(days=args.days)
