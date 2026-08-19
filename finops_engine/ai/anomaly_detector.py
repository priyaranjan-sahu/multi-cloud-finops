"""Anomaly detection over FOCUS cost telemetry.

Flags days whose spend deviates sharply from a provider/service baseline,
using Isolation Forest combined with a rolling z-score check.
"""

from typing import Any

from sklearn.ensemble import IsolationForest

from finops_engine.schema.focus_spec import FocusRecord, normalize_to_focus_dataframe


class AnomalyDetector:
    def __init__(self, contamination: float = 0.05, z_threshold: float = 2.5):
        self.contamination = contamination
        self.z_threshold = z_threshold
        self.model = IsolationForest(contamination=self.contamination, random_state=42)

    def detect_anomalies(self, records: list[FocusRecord]) -> list[dict[str, Any]]:
        """Analyzes FOCUS records for spend anomalies and returns detailed root-cause insights."""
        df = normalize_to_focus_dataframe(records)
        if df.empty:
            return []

        df["date"] = df["billing_period_start"].dt.date
        daily = df.groupby(["date", "provider_name", "service_name"])["billed_cost"].sum().reset_index()

        if len(daily) < 5:
            return []

        X = daily[["billed_cost"]].values
        self.model.fit(X)
        daily["iforest_score"] = self.model.predict(X)

        daily["mean"] = daily.groupby(["provider_name", "service_name"])["billed_cost"].transform(
            lambda x: x.rolling(7, min_periods=1).mean()
        )
        daily["std"] = daily.groupby(["provider_name", "service_name"])["billed_cost"].transform(
            lambda x: x.rolling(7, min_periods=1).std().fillna(1.0)
        )
        daily["z_score"] = (daily["billed_cost"] - daily["mean"]) / daily["std"].replace(0, 1.0)

        anomalies_df = daily[(daily["iforest_score"] == -1) & (daily["z_score"] >= self.z_threshold)].copy()

        results = []
        for _, row in anomalies_df.iterrows():
            expected_cost = float(row["mean"])
            actual_cost = float(row["billed_cost"])
            excess_cost = round(actual_cost - expected_cost, 2)

            results.append(
                {
                    "date": str(row["date"]),
                    "provider": str(row["provider_name"]),
                    "service": str(row["service_name"]),
                    "actual_cost_usd": round(actual_cost, 2),
                    "expected_baseline_usd": round(expected_cost, 2),
                    "anomaly_excess_usd": excess_cost,
                    "z_score": round(float(row["z_score"]), 2),
                    "severity": "HIGH" if excess_cost > 200 else ("MEDIUM" if excess_cost > 50 else "LOW"),
                    "root_cause": f"{row['provider_name']} {row['service_name']} spent ${excess_cost} above baseline",
                }
            )

        return sorted(results, key=lambda x: x["anomaly_excess_usd"], reverse=True)
