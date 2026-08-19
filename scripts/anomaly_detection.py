"""
Standalone AI Anomaly Detection CLI
Executes the Isolation Forest + Z-Score detector on FOCUS multi-cloud telemetry.
"""

import argparse

from finops_engine.ai import AnomalyDetector
from finops_engine.connectors import MockTelemetryConnector


def run_anomaly_detection(days: int = 90, contamination: float = 0.05, z_threshold: float = 2.0) -> list:
    print(f"🔍 Fetching {days}-day multi-cloud telemetry for AI anomaly detection...")
    connector = MockTelemetryConnector(days=days)
    records = connector.fetch_cost_data()

    print("🤖 Executing Isolation Forest & Z-Score anomaly detection model...")
    detector = AnomalyDetector(contamination=contamination, z_threshold=z_threshold)
    anomalies = detector.detect_anomalies(records)

    print(f"\n🚨 Detected {len(anomalies)} Cost Anomalies:")
    for idx, anomaly in enumerate(anomalies, 1):
        print(
            f"   [{idx}] {anomaly['date']} | {anomaly['provider']} - {anomaly['service']}: "
            f"Actual ${anomaly['actual_cost_usd']} vs Expected ${anomaly['expected_baseline_usd']} "
            f"(Spike: +${anomaly['anomaly_excess_usd']}) [{anomaly['severity']}]"
        )

    print("\n✅ Anomaly Detection execution completed successfully.")
    return anomalies


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run FinOps anomaly detection")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--contamination", type=float, default=0.05)
    parser.add_argument("--z-threshold", type=float, default=2.0)
    args = parser.parse_args()
    run_anomaly_detection(days=args.days, contamination=args.contamination, z_threshold=args.z_threshold)
