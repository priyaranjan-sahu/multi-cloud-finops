"""
Automated Rightsizing Export Script
Executes waste analysis and writes recommendations to output JSON file.
"""

import json
import os
from finops_engine.connectors import MockTelemetryConnector
from finops_engine.ai import RightsizingEngine

def export_rightsizing_recommendations(output_path: str = "output/rightsizing_recommendations.json"):
    connector = MockTelemetryConnector(days=30)
    records = connector.fetch_cost_data()
    engine = RightsizingEngine()
    results = engine.generate_recommendations(records)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"✅ Rightsizing recommendations exported to {output_path}")

if __name__ == "__main__":
    export_rightsizing_recommendations()
