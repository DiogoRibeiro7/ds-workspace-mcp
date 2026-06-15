# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

### Added

- Configuration validation with typed settings and documented environment variables.
- Richer dataset profiling with numeric, categorical, boolean, and datetime summaries.
- Structured logging for tool calls and validation failures.
- GitHub Actions CI for linting, typing, and tests.
- Safe DuckDB query support for CSV datasets.
- Safe SQLite discovery, schema inspection, and query tooling.
- In-memory profile metadata caching with invalidation by path, size, mtime, and options.
- Correlation ranking and heuristic leakage diagnostics.
- Time-series dataset validation for forecasting readiness.
- Dummy baseline model evaluation for regression and classification tasks.
- Synthetic healthcare dataset generation.
- Local workflow CLI commands.
- Runnable MCP client examples for stdio and Streamable HTTP.
- Release packaging metadata and a GitHub Actions publishing workflow.
- Optional bearer-token authentication for Streamable HTTP deployments.
- Optional OpenTelemetry tracing hooks for core dataset and tool operations.
- Project-specific exceptions with clearer, safer user-facing error messages.

## [0.1.0] - 2026-06-15

### Added

- Initial MCP server with safe CSV discovery, preview, profiling, issue detection, and dataset analysis prompt.
