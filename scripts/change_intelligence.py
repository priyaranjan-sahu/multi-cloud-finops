"""CLI tool for Change Intelligence and deployment-to-cost attribution."""

import argparse

from finops_engine.ai import ChangeIntelligenceEngine
from finops_engine.connectors import MockTelemetryConnector
from finops_engine.license import verify_pro_license


def run_change_intelligence_analysis(days: int = 30, window_days: int = 7) -> list[dict]:
    """Runs change-to-cost attribution analysis from the command line."""
    verify_pro_license("CLI Change Intelligence")
    print(f"Running {days}-day Change Intelligence analysis (correlation window: {window_days} days)...")

    connector = MockTelemetryConnector(days=days)
    records = connector.fetch_cost_data()
    events = connector.fetch_deployment_events()

    engine = ChangeIntelligenceEngine(correlation_window_days=window_days)
    attributions = engine.attribute_cost_changes(records, events)

    total_impact = sum(item["estimated_monthly_impact_usd"] for item in attributions)
    print(f"\nAttributed Changes Found: {len(attributions)}")
    print(f"Total Monthly Cost Impact: ${total_impact:,.2f}\n")

    for attr in attributions:
        print(f"[{attr['attribution_id']}] Confidence: {attr['confidence']}")
        print(f"  Resource: {attr['resource_id']} ({attr['provider']} - {attr['service']})")
        print(f"  Monthly Impact: +${attr['estimated_monthly_impact_usd']:,.2f}")
        print(f"  Root Cause: {attr['root_cause_narrative']}")
        print(f"  Action: {attr['actionable_remediation']}\n")

    return attributions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Change Intelligence and deployment attribution")
    parser.add_argument("--days", type=int, default=30, help="Number of telemetry days to analyze")
    parser.add_argument("--window-days", type=int, default=7, help="Deployment event correlation window (days)")
    args = parser.parse_args()
    run_change_intelligence_analysis(days=args.days, window_days=args.window_days)
