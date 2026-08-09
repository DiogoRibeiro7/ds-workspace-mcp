# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

### Added

- Added structural DuckDB SQL relation validation with explicit in-memory relation allowlisting.
- Added adversarial DuckDB tests for external file, URL, extension, attachment, and relation-name bypass attempts.
- Added typed baseline validation split support for random, stratified, chronological, and grouped holdouts.
- Added classification baseline class-count metadata and weighted F1.
- Added structured time-series frequency inference with regularity kind, confidence, support ratio, and missing-interval metadata.
- Added severity and confidence metadata to leakage warnings.
- Added Docker report persistence wiring and a container smoke test.
- Added transactional report storage with explicit overwrite controls and report content hashes.
- Added a FastMCP application factory for isolated server construction.
- Added domain-specific MCP registration modules for resources, tools, and prompts.
- Added dataset schema diff and drift diagnostics across CSV, Parquet, JSON, JSONL, Excel, and SQLite datasets.
- Added richer bounded profiling diagnostics for numeric distributions, categorical quality, duplicate rows, identifiers, free-text columns, and candidate keys.
- Added chronological forecast baseline evaluation with last-value, seasonal-naive, and drift baselines plus documented MAE, RMSE, MASE, and sMAPE metrics.
- Added reproducible evaluation manifests to experiment plans, modeling reports, dummy baselines, and forecast baselines.

### Changed

- Hardened DuckDB query connections by disabling external access, extension autoload/autoinstall, community extensions, persistent secrets, and runtime configuration changes before user SQL executes.
- Strengthened SQL timeout handling so SQLite timeout protection remains active during result fetching and both SQL engines log/trace timeout, cancellation, elapsed-time, and result-row metadata.
- Modeling readiness and experiment plans now return executable validation recommendations for baseline evaluation.
- Classification baselines now reject unsupported or unrepresentative train/test splits instead of returning misleading metrics.
- Time-series validation now reports irregular gap patterns without fabricating a dominant frequency or missing-interval count.
- Feature selection now treats high correlation and target-name overlap as review evidence instead of automatic exclusion.
- Docker builds now install from `poetry.lock`, run as a non-root user, and persist reports through `/app/reports`.
- Saved, copied, and renamed modeling reports now fail on target collisions unless overwrite is explicitly requested.
- Server startup now configures FastMCP through public constructor arguments instead of mutating private runtime state.
- `server.py` is now a thin startup/composition module with MCP wrappers split by domain.

## [1.0.2] - 2026-08-09

### Added

- Added Zenodo and GitHub citation metadata.
- Added GitHub issue templates, a pull request template, and Dependabot configuration.
- Added a Makefile with repeatable development, quality, test, build, and cleanup commands.
- Added editor and Git attributes for consistent formatting and line endings.

### Changed

- Documented the repository quality gate and aligned pull request expectations with CI.
- Migrated package metadata to PEP 621 `[project]` fields to remove Poetry 2 deprecation warnings.
- Refreshed dependency lock metadata after Dependabot maintenance updates.

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
