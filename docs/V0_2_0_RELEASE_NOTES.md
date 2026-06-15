# v0.2.0 Release Notes

`ds-workspace-mcp` v0.2.0 turns the initial safe CSV MCP server into a broader analytical workspace for local data science workflows.

Highlights:

- richer profiling for numeric, categorical, boolean, and datetime columns;
- safe DuckDB and SQLite querying with bounded read-only execution;
- metadata caching, correlation summaries, leakage diagnostics, and time-series validation;
- baseline model evaluation and synthetic healthcare dataset generation;
- local CLI commands, runnable MCP client examples, notebook demos, Docker Compose support, HTTP API-key auth, and optional tracing.

Operational polish:

- typed configuration and structured logging;
- CI, release packaging workflow, and release checklist;
- safer project-specific exceptions with troubleshooting guidance.

Known limitations:

- leakage detection and forecasting-readiness warnings are heuristic;
- HTTP authentication is a simple shared-secret layer, not a full auth system;
- optional tracing requires the OpenTelemetry extra to be installed.
