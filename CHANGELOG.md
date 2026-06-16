# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

## [1.0.1] - 2026-06-16

### Changed

- Upgraded `pytest` to `9.1.0` to address `GHSA-6w46-j5rx-g56g` / `CVE-2025-71176`.
- Removed PyPI-first release assumptions from the workflow and release documentation.

### Fixed

- Removed the known moderate Dependabot alert caused by `pytest < 9.0.3` in `poetry.lock`.

## [1.0.0] - 2026-06-16

### Added

- Stable public API contract covering MCP resources, tools, prompts, CLI commands, environment variables, and compatibility expectations.
- End-to-end integration coverage for stdio, Streamable HTTP, HTTP auth, and runnable example clients.
- Security model, deployment guide, and architecture overview for third-party use.
- Dataset-size, SQL-length, and SQL-timeout guardrails with clean user-facing error categories.

### Changed

- Promoted the project surface to a documented `v1.0.0` contract for local analytical workflows.
- Clarified operational boundaries and heuristic limitations across the documentation set.

### Known Limitations

- Leakage diagnostics and forecasting-readiness checks remain heuristic.
- HTTP authentication is still a shared-secret layer, not a full identity system.
- DuckDB timeout enforcement is best-effort interruption rather than a hard execution sandbox.

## [0.2.0] - 2026-06-15

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
- GitHub-tag-based release artifacts and release notes workflow.

## [0.1.0] - 2026-06-15

### Added

- Initial MCP server with safe CSV discovery, preview, profiling, issue detection, and dataset analysis prompt.
