# Deployment Guide

## Supported Modes

`ds-workspace-mcp` supports two deployment modes:

- local process launch over `stdio`
- long-running server over Streamable HTTP

For most local assistant integrations, `stdio` is the simplest and safest default. Use HTTP when multiple local tools need to connect to the same running process or when containerization is preferred.

## Runtime Requirements

- Python `3.11` or `3.12`
- Poetry for local installs
- a readable dataset directory for `MCP_DATA_ROOT`
- a writable report directory for `MCP_REPORTS_ROOT` when saving modeling reports

Optional:

- Docker for container deployment
- OpenTelemetry dependencies if tracing is required

## Local Python Deployment

Install dependencies:

```bash
poetry install
```

Run over stdio:

```bash
MCP_TRANSPORT=stdio poetry run ds-workspace-mcp serve
```

Run over HTTP:

```bash
MCP_TRANSPORT=streamable-http \
MCP_HOST=127.0.0.1 \
MCP_PORT=8000 \
poetry run ds-workspace-mcp serve
```

## Environment Variables

Primary settings:

- `MCP_DATA_ROOT`
- `MCP_REPORTS_ROOT`
- `MCP_TRANSPORT`
- `MCP_HOST`
- `MCP_PORT`
- `MCP_API_KEY`
- `MCP_LOG_LEVEL`
- `MCP_MAX_PREVIEW_ROWS`
- `MCP_MAX_SQL_ROWS`
- `MCP_MAX_SQL_QUERY_LENGTH`
- `MCP_SQL_TIMEOUT_MS`
- `MCP_MAX_CATEGORICAL_VALUES`
- `MCP_MAX_DATASET_BYTES`
- `MCP_PROFILE_CACHE_ENABLED`
- `MCP_PROFILE_CACHE_MAX_ENTRIES`
- `MCP_TRACING_ENABLED`
- `MCP_TRACING_SERVICE_NAME`
- `MCP_TRACING_CONSOLE_EXPORTER`

Recommended baseline for localhost HTTP:

```bash
MCP_TRANSPORT=streamable-http
MCP_HOST=127.0.0.1
MCP_PORT=8000
MCP_DATA_ROOT=./data
MCP_REPORTS_ROOT=./reports
MCP_LOG_LEVEL=INFO
MCP_API_KEY=
```

Recommended baseline for exposed HTTP behind a reverse proxy:

```bash
MCP_TRANSPORT=streamable-http
MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_DATA_ROOT=/app/data
MCP_REPORTS_ROOT=/app/reports
MCP_LOG_LEVEL=INFO
MCP_API_KEY=<shared-secret>
```

## Docker

Build the image:

```bash
docker build -t ds-workspace-mcp .
```

Run it directly:

```bash
docker run --rm \
  -p 8000:8000 \
  -e MCP_TRANSPORT=streamable-http \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=8000 \
  -e MCP_REPORTS_ROOT=/app/reports \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/reports:/app/reports" \
  ds-workspace-mcp
```

Notes:

- the image defaults `MCP_DATA_ROOT` to `/app/data`
- the image defaults `MCP_REPORTS_ROOT` to `/app/reports`
- the image installs only main dependencies
- the image installs dependency versions from `poetry.lock`
- the runtime process runs as a non-root `app` user
- the container exposes port `8000`

## Docker Compose

Start the stack:

```bash
docker compose up --build
```

Stop it:

```bash
docker compose down
```

Compose behavior:

- reads `.env.example` when present
- applies `.env` overrides when present
- binds the app to `0.0.0.0`
- mounts local `./data` into `/app/data`
- mounts local `./reports` into `/app/reports`
- publishes `${MCP_PORT:-8000}`

If you run Docker on Linux with bind-mounted host directories, ensure `./reports` is writable
by the container runtime user so saved modeling reports can persist.

## Health and Verification

Minimum verification after startup:

1. Confirm the process started without config validation errors.
2. If using HTTP, open `http://127.0.0.1:8000/mcp` or the configured host and port through an MCP client.
3. Run one core call such as `preview_csv` or `profile_csv`.
4. If HTTP auth is enabled, confirm unauthenticated requests fail and authenticated requests succeed.

Repo-level verification commands:

```bash
poetry run ruff check .
poetry run mypy
poetry run pytest
bash scripts/docker-smoke-test.sh
```

## Reverse Proxy Guidance

If exposing the HTTP server beyond localhost:

- terminate TLS at the proxy or ingress layer
- keep the app on a private network
- inject `MCP_API_KEY` through the runtime environment, not source control
- restrict upstream access to trusted clients where possible

This project does not currently set proxy headers, enforce HTTPS redirects, or manage certificates itself.

## Logging and Tracing

Logging:

- configure with `MCP_LOG_LEVEL`
- default is `INFO`
- logs go to process stdout/stderr

Tracing:

- install the Poetry `opentelemetry` extra first
- enable with `MCP_TRACING_ENABLED=true`
- for local debugging, optionally set `MCP_TRACING_CONSOLE_EXPORTER=true`

If tracing dependencies are missing, the server logs a warning and continues to run.

## Failure Modes

Common startup or runtime failures:

- invalid `MCP_PORT` or other settings validation errors
- missing datasets inside `MCP_DATA_ROOT`
- unsupported file suffixes
- malformed or incompatible CSV content causing profiling failures
- malformed or incompatible CSV content causing clean dataset read failures
- CSV files larger than `MCP_MAX_DATASET_BYTES`
- rejected SQL because the query is not read-only or exceeds limits
- SQL queries interrupted after `MCP_SQL_TIMEOUT_MS`

## Deployment Boundaries

Supported for `v1.0`:

- single-process local development
- local Docker usage
- simple self-hosted HTTP behind a trusted network or reverse proxy

Not a target for `v1.0`:

- horizontally scaled multi-instance serving
- multi-tenant SaaS deployments
- internet-exposed unauthenticated endpoints
