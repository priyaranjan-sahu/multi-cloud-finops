"""Daily spend forecast built from linear regression on historical telemetry.

Returns point predictions with t-based 95% prediction intervals that widen
with the forecast horizon.
"""

from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression

from finops_engine.schema.focus_spec import FocusRecord, normalize_to_focus_dataframe


class CostForecaster:
    """Predictive spend model using linear trend estimation and parametric confidence intervals."""

    def __init__(self, forecast_days: int = 30):
        self.forecast_days = forecast_days
        self.model = LinearRegression()

    def predict_future_cost(self, records: list[FocusRecord]) -> dict[str, Any]:
        """Projects future spend trend with widening 95% prediction intervals."""
        empty_result = {
            "forecast_days": self.forecast_days,
            "total_projected_spend_usd": 0.0,
            "average_daily_projected_usd": 0.0,
            "confidence_level": "95%",
            "forecast": [],
        }

        df = normalize_to_focus_dataframe(records)
        if df.empty:
            return empty_result

        df["date"] = pd.to_datetime(df["billing_period_start"]).dt.date
        daily_total = df.groupby("date")["billed_cost"].sum().reset_index()

        if len(daily_total) < 3:
            return empty_result

        daily_total["day_idx"] = np.arange(len(daily_total))
        X = daily_total[["day_idx"]].values
        y = daily_total["billed_cost"].values
        n = len(y)

        self.model.fit(X, y)
        y_pred_hist = self.model.predict(X)
        residuals = y - y_pred_hist

        # Residual variance with degrees of freedom penalty for the fitted slope.
        dof = n - 2
        mse = float(np.sum(residuals**2)) / dof if dof > 0 else 0.0

        last_day_idx = n - 1
        last_date = daily_total["date"].max()
        future_indices = np.arange(last_day_idx + 1, last_day_idx + 1 + self.forecast_days)

        x_mean = float(np.mean(X))
        x_var = float(np.sum((X - x_mean) ** 2))
        t_crit = float(stats.t.ppf(0.975, df=dof))

        predictions = self.model.predict(future_indices.reshape(-1, 1))

        forecast_list: list[dict[str, Any]] = []
        total_projected = 0.0

        for idx, (day_idx, pred) in enumerate(zip(future_indices, predictions, strict=False)):
            # Prediction interval for the mean response at a given horizon.
            leverage = 1.0 / n + ((day_idx - x_mean) ** 2) / x_var if x_var > 0 else 0.0
            margin = t_crit * np.sqrt(mse * (1.0 + leverage))

            future_date = (last_date + timedelta(days=idx + 1)).isoformat()
            pred_cost = max(0.0, round(float(pred), 2))
            upper_bound = round(pred_cost + margin, 2)
            lower_bound = max(0.0, round(pred_cost - margin, 2))

            total_projected += pred_cost
            forecast_list.append(
                {
                    "date": future_date,
                    "predicted_cost_usd": pred_cost,
                    "confidence_upper_usd": upper_bound,
                    "confidence_lower_usd": lower_bound,
                }
            )

        return {
            "forecast_days": self.forecast_days,
            "total_projected_spend_usd": round(total_projected, 2),
            "average_daily_projected_usd": round(total_projected / self.forecast_days, 2)
            if self.forecast_days > 0
            else 0.0,
            "confidence_level": "95%",
            "forecast": forecast_list,
        }
