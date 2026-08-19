"""
Standalone AI Cost Forecasting CLI
Executes time-series predictive modeling on multi-cloud spend trends.
"""

import argparse

from finops_engine.ai import CostForecaster
from finops_engine.connectors import MockTelemetryConnector


def run_cost_prediction(forecast_days: int = 30, history_days: int = 60) -> dict:
    print(f"📊 Fetching {history_days} days of historical cost data for a {forecast_days}-day AI forecast...")
    connector = MockTelemetryConnector(days=history_days)
    records = connector.fetch_cost_data()

    forecaster = CostForecaster(forecast_days=forecast_days)
    result = forecaster.predict_future_cost(records)

    print(f"\n🔮 Projected Total Spend (Next {forecast_days} Days): ${result['total_projected_spend_usd']:,.2f}")
    print(f"📈 Daily Projected Average: ${result['average_daily_projected_usd']:,.2f}")
    print("\nSample Forecast Highlights:")
    for item in result["forecast"][:5]:
        print(
            f"   📅 {item['date']}: Projected ${item['predicted_cost_usd']} "
            f"(95% CI: ${item['confidence_lower_usd']} - ${item['confidence_upper_usd']})"
        )

    print("\n✅ AI Cost Prediction execution completed successfully.")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forecast future multi-cloud cost with confidence intervals")
    parser.add_argument("--forecast-days", type=int, default=30)
    parser.add_argument("--history-days", type=int, default=60)
    args = parser.parse_args()
    run_cost_prediction(forecast_days=args.forecast_days, history_days=args.history_days)
