"""Export rightsizing recommendations to a JSON file."""

import argparse
import json
import os

from finops_engine.ai import RightsizingEngine
from finops_engine.connectors import MockTelemetryConnector


def export_rightsizing_recommendations(
    output_path: str = "output/rightsizing_recommendations.json", days: int = 30
) -> str:
    connector = MockTelemetryConnector(days=days)
    records = connector.fetch_cost_data()
    engine = RightsizingEngine()
    results = engine.generate_recommendations(records)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Rightsizing recommendations exported to {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export rightsizing recommendations to JSON")
    parser.add_argument("--output", type=str, default="output/rightsizing_recommendations.json")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    export_rightsizing_recommendations(output_path=args.output, days=args.days)
