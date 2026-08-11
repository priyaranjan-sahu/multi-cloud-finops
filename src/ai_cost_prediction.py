"""
Standalone AI Cost Forecasting Script
Executes time-series predictive modeling on multi-cloud spend trends.
"""

from finops_engine.connectors import MockTelemetryConnector
from finops_engine.ai import CostForecaster

def run_cost_prediction(forecast_days: int = 30):
    print(f"📊 Fetching historical cost data and running {forecast_days}-day AI forecast...")
    connector = MockTelemetryConnector(days=60)
    records = connector.fetch_cost_data()

    forecaster = CostForecaster(forecast_days=forecast_days)
    result = forecaster.predict_future_cost(records)

    print(f"\n🔮 Projected Total Spend (Next {forecast_days} Days): ${result['total_projected_spend_usd']:,.2f}")
    print(f"📈 Daily Projected Average: ${result['average_daily_projected_usd']:,.2f}")
    print("\nSample Forecast Highlights:")
    for f in result["forecast"][:5]:
        print(f"   📅 {f['date']}: Projected ${f['predicted_cost_usd']} (95% CI: ${f['confidence_lower_usd']} - ${f['confidence_upper_usd']})")

    print("\n✅ AI Cost Prediction execution completed successfully.")
    return result

if __name__ == "__main__":
    run_cost_prediction(30)
