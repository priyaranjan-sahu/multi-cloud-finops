# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-08-19

### Added
- Domain exception hierarchy (`FinOpsError`, `ConnectorError`, `DataFetchError`)
- Mocked test suites for the AWS, GCP, and Azure connectors
- Full coverage reporting for all three live connectors

### Changed
- Bumped dependencies to current stable releases (Python 3.10 compatible):
  FastAPI, Pydantic, pandas, numpy, scipy, scikit-learn, boto3,
  google-cloud-bigquery, azure-mgmt-costmanagement, azure-identity,
  prometheus-client, and dev tooling (ruff, mypy, pytest, httpx)
- Removed unused dependencies (google-cloud-billing, google-cloud-storage,
  azure-storage-blob, requests, python-dateutil)
- Updated Terraform provider constraints (aws ~> 6.0, google ~> 7.0, azurerm ~> 4.0)
  and Docker image tags (Prometheus 3.x, Grafana 13.x, cAdvisor 0.60.x)
- Typed response models, pagination, env-gated mock mode, and API-key auth
- Fail-closed multi-provider gateway and timezone-aware timestamps
- Rightsizing engine and forecast prediction intervals rebuilt
- Slimmed the Docker runtime image to a non-root user

### Fixed
- Azure `QueryDefinition` now sends the required `type` and `datetime` time periods
- Azure/GCP malformed-row handlers no longer reference unbound variables
- Savings metrics summed per provider/category instead of overwritten
- Timing-safe API-key comparison and OpenAPI security scheme documentation

### Removed
- Duplicate CLI tooling consolidated into the `scripts` package

## [1.0.0] - 2025-03-16

Initial release with FOCUS-aligned cost aggregation, anomaly detection,
forecasting, rightsizing, and Prometheus/Grafana monitoring across AWS,
GCP, and Azure.
