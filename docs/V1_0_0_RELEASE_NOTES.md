# v1.0.0 Release Notes

`ds-workspace-mcp` `v1.0.0` marks the first stable release of the project as a local analytical MCP server with a documented compatibility contract and end-to-end transport coverage.

## Highlights

- stable MCP, CLI, and environment-variable contract in `docs/API_CONTRACT.md`
- tested stdio, Streamable HTTP, and HTTP auth transport flows
- runnable example clients covered by integration smoke tests
- safe DuckDB and SQLite querying with row, size, query-length, and timeout guardrails
- operational documentation for security, deployment, and architecture

## Operational Hardening

- malformed CSV, invalid encoding, and oversized dataset handling now fail with explicit user-facing errors
- SQL query text is bounded by `MCP_MAX_SQL_QUERY_LENGTH`
- SQL execution time is bounded by `MCP_SQL_TIMEOUT_MS`
- SQLite uses native progress-handler interruption for query timeout enforcement
- DuckDB uses best-effort interruption through connection-level cancellation

## User-Facing Surface

The `v1.0.0` contract now treats these as versioned public surface:

- MCP resource names
- MCP tool names and high-level result shapes
- MCP prompt names
- CLI commands
- documented environment variables
- stable error categories

Breaking changes to that surface now require an explicit major version bump.

## Known Limitations

- leakage warnings and forecasting-readiness checks are heuristic
- HTTP auth remains a shared bearer-token model
- DuckDB timeout behavior is best-effort, not a formal sandbox
- the project is intended for local or controlled self-hosted use, not multi-tenant SaaS deployment

## Validation Summary

The release candidate state was validated with:

- `poetry run ruff check .`
- `poetry run mypy`
- `poetry run pytest`
- `poetry build`
- stdio and HTTP example smoke paths
