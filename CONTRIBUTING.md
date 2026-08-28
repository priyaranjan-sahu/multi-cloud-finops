# Contributing

Thanks for taking the time to contribute. This project follows a fairly
standard workflow: branch, commit, test, open a pull request.

## Getting started

```bash
git clone https://github.com/priyaranjan-sahu/multi-cloud-finops.git
cd multi-cloud-finops
pip install -r requirements-dev.txt
```

## Making changes

1. Create a branch off `main`:

   ```bash
   git checkout -b feat/your-change
   ```

2. Make your changes. Keep commits focused and use conventional commit
   messages (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`).

3. Run the checks before opening a PR:

   ```bash
   ruff check .
   ruff format --check .
   mypy finops_engine
   pytest tests/
   ```

   The `Makefile` has shortcuts: `make lint`, `make typecheck`, `make test`,
   and `make check` runs all of them.

4. Push and open a pull request. The CI pipeline runs the same checks on
   Python 3.10, 3.11, and 3.12, so they must pass there too.

## Adding a test

New behavior should come with tests. Look at the existing suites in `tests/`
for conventions:

- `test_focus_spec.py` - schema creation, credits, normalization
- `test_ai_engines.py` - anomaly detection, forecasting, rightsizing
- `test_connectors.py` - multi-provider gateway and fail-closed behavior
- `test_api.py` - endpoint responses, pagination, auth, mock gating
- `test_aws_connector.py` / `test_gcp_connector.py` / `test_azure_connector.py` -
  live connector mapping with mocked SDKs

Live connector tests patch the cloud SDKs; they do not need credentials and
must not make network calls.

## Documentation

If a change affects user-facing behavior (endpoints, config variables, CLI
flags), update the README and, where relevant, the CHANGELOG.
