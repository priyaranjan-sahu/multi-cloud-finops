"""
Rightsizing Recommendations Engine Script
Runs multi-cloud compute, storage, and container waste analysis.
"""

from finops_engine.connectors import MockTelemetryConnector
from finops_engine.ai import RightsizingEngine

def run_rightsizing_analysis():
    print("⚡ Running Multi-Cloud Rightsizing & Waste Vector Analysis...")
    connector = MockTelemetryConnector(days=30)
    records = connector.fetch_cost_data()

    engine = RightsizingEngine()
    results = engine.generate_recommendations(records)

    print(f"\n💡 Current Monthly Spend: ${results['total_current_monthly_spend_usd']:,.2f}")
    print(f"💰 Potential Monthly Savings: ${results['total_potential_monthly_savings_usd']:,.2f} ({results['potential_savings_percentage']}% ROI)")
    print("\nActionable Recommendations:")
    for rec in results["recommendations"]:
        print(f"   [{rec['id']}] {rec['provider']} | {rec['category']}: {rec['action']} -> Save ${rec['estimated_monthly_savings_usd']}/mo")

    print("\n✅ Rightsizing Recommendations execution completed successfully.")
    return results

if __name__ == "__main__":
    run_rightsizing_analysis()
