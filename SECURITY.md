# Security

This project reads cloud billing telemetry and, in live mode, needs
credentials for AWS, GCP, and Azure. Take the usual precautions.

## Reporting a vulnerability

Do not open a public issue for security problems. Report them privately by
emailing the maintainer (see the GitHub profile for contact details) or
opening a security advisory through GitHub.

Please include:

- the affected version and endpoint or module
- a description of the issue and the impact
- a minimal reproducer if possible

You can expect an acknowledgement within a few days and a fix timeline once
the issue is understood.

## Operational guidance

- The default is live mode (`FINOP_MOCK_MODE=false`) and it fails closed when no provider is configured. Use `FINOP_MOCK_MODE=true` only for local demos or tests.
  billing data.
- Never commit credentials. Cloud SDK credentials come from the standard
  environment/credential chains, never from code.
- When `FINOP_API_KEY` is set, all `/api/*` routes require an `X-API-Key`
  header. Put the API behind TLS in production and rotate the key.
- Keep dependencies current. `dependabot` is enabled and opens PRs for
  outdated Python dependencies; review and merge them.
- The Docker image runs as a non-root user; keep any custom image builds
  on top of it non-root as well.
