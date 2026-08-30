"""Anomaly detection over FOCUS cost telemetry.

Flags days whose spend deviates sharply from a provider/service baseline,
using Isolation Forest combined with a rolling z-score check.
"""

from typing import Any

from sklearn.ensemble import IsolationForest

from finops_engine.schema.focus_spec import FocusRecord, normalize_to_focus_dataframe


class AnomalyDetector:
    """Statistical and unsupervised machine learning detector for cloud spend anomalies."""

    def __init__(self, contamination: float = 0.05, z_threshold: float = 2.5):
        self.contamination = contamination
        self.z_threshold = z_threshold

    def detect_anomalies(self, records: list[FocusRecord]) -> list[dict[str, Any]]:
        """Analyzes FOCUS records for spend anomalies and returns detailed root-cause insights."""
        df = normalize_to_focus_dataframe(records)
        if df.empty:
            return []

        df["date"] = df["billing_period_start"].dt.date
        daily = df.groupby(["date", "provider_name", "service_name"])["billed_cost"].sum().reset_index()
        daily = daily.sort_values(["provider_name", "service_name", "date"]).reset_index(drop=True)

        if len(daily) < 5:
            return []

        # ── Per-group Isolation Forest ──────────────────────────────────────
        # Training on the full dataset mixes cost scales across providers and
        # services, making the outlier threshold meaningless.  Instead we fit
        # a fresh model for each (provider, service) pair so that anomaly
        # detection operates within a homogeneous cost population.
        iforest_flags: list[int] = []
        for (_provider, _service), grp in daily.groupby(["provider_name", "service_name"]):
            if len(grp) < 5:
                # Not enough observations for Isolation Forest; mark as normal.
                iforest_flags.extend([1] * len(grp))
                continue
            model = IsolationForest(contamination=self.contamination, random_state=42)
            flags = model.fit_predict(grp[["billed_cost"]].values)
            iforest_flags.extend(flags.tolist())

        daily["iforest_score"] = iforest_flags

        daily["mean"] = daily.groupby(["provider_name", "service_name"])["billed_cost"].transform(
            lambda x: x.shift(1).rolling(7, min_periods=3).mean()
        )
        daily["std"] = daily.groupby(["provider_name", "service_name"])["billed_cost"].transform(
            lambda x: x.shift(1).rolling(7, min_periods=3).std()
        )

        import numpy as np

        std_safe = daily["std"].fillna(0)
        daily["z_score"] = np.where(
            std_safe == 0,
            0.0,
            (daily["billed_cost"] - daily["mean"]) / daily["std"].replace(0, np.nan),
        )

        anomalies_df = daily[
            daily["mean"].notna() & (daily["iforest_score"] == -1) & (daily["z_score"] >= self.z_threshold)
        ].copy()

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
