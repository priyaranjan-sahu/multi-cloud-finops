"""Generate rightsizing recommendations from the command line."""

import argparse

from finops_engine.ai import RightsizingEngine
from finops_engine.connectors import MockTelemetryConnector
from finops_engine.license import verify_pro_license


def run_rightsizing_analysis(days: int = 30) -> dict:
    verify_pro_license("CLI Rightsizing Analysis")
    print(f"Running {days}-day rightsizing and waste analysis...")
    connector = MockTelemetryConnector(days=days)
    records = connector.fetch_cost_data()

    engine = RightsizingEngine()
    results = engine.generate_recommendations(records)

    print(f"\nCurrent monthly spend: ${results['total_current_monthly_spend_usd']:,.2f}")
    print(
        f"Potential monthly savings: ${results['total_potential_monthly_savings_usd']:,.2f} "
        f"({results['potential_savings_percentage']}%)"
    )
    print("\nRecommendations:")
    for rec in results["recommendations"]:
        print(
            f"   [{rec['id']}] {rec['provider']} | {rec['category']}: {rec['action']} -> "
            f"save ${rec['estimated_monthly_savings_usd']}/mo"
        )

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate multi-cloud rightsizing recommendations")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    run_rightsizing_analysis(days=args.days)
