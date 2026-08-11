"""
Standalone AI Anomaly Detection Script
Executes Isolation Forest + Z-Score detector on FOCUS 1.0 multi-cloud telemetry.
"""

from finops_engine.connectors import MockTelemetryConnector
from finops_engine.ai import AnomalyDetector

def run_anomaly_detection():
    print("🔍 Fetching multi-cloud telemetry for AI anomaly detection...")
    connector = MockTelemetryConnector(days=90)
    records = connector.fetch_cost_data()

    print("🤖 Executing Isolation Forest & Z-Score anomaly detection model...")
    detector = AnomalyDetector(contamination=0.05, z_threshold=2.0)
    anomalies = detector.detect_anomalies(records)

    print(f"\n🚨 Detected {len(anomalies)} Cost Anomalies:")
    for idx, a in enumerate(anomalies, 1):
        print(f"   [{idx}] {a['date']} | {a['provider']} - {a['service']}: Actual ${a['actual_cost_usd']} vs Expected ${a['expected_baseline_usd']} (Spike: +${a['anomaly_excess_usd']}) [{a['severity']}]")

    print("\n✅ Anomaly Detection execution completed successfully.")
    return anomalies

if __name__ == "__main__":
    run_anomaly_detection()
