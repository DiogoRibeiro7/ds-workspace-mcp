# Implementation Plan

## Current State Audit

### Current MCP surface

- Resource: `datasets://catalog` lists CSV files from the configured data directory.
- Tool: `preview_csv` returns a small row preview from a CSV file.
- Tool: `profile_csv` returns row count, columns, dtypes, and missingness metrics.
- Tool: `detect_csv_issues` flags high missingness and likely identifier columns.
- Prompt: `dataset_analysis_prompt` creates a reusable analysis prompt for a dataset.

### Current safety boundaries

- Dataset resolution is restricted to the configured data directory.
- Path traversal attempts are rejected during dataset path resolution.
- Only `.csv` files are currently supported.
- Preview size is bounded.
- The current server exposes read-only analytical capabilities only.

### Current gaps

- Configuration was previously spread across direct environment reads.
- Server configuration validation was missing.
- Tool outputs for richer profiling and future SQL access are not yet modeled.
- No CI workflow exists.
- README configuration coverage is thin.
- No implementation planning document existed.

### Current test coverage

- Safe CSV listing.
- Safe dataset resolution and traversal rejection.
- Preview row validation.
- Baseline dataset profiling.
- Basic issue detection.

### Missing tests

- Settings validation and cache behavior.
- Transport, port, host, and row-limit validation paths.
- Error handling behavior for non-string inputs and missing datasets.
- Future SQL safety enforcement.
- Future richer profiling output edge cases.

### Technical risks

- Import-time configuration can become brittle as the server gains more runtime options.
- SQL support will expand the attack surface if query validation is weak.
- Profiling payloads may become too large without explicit output limits.
- Repeated full-file reads will become expensive without caching.

## Milestone Plan

## v0.2

### 1. Configuration validation

- [x] Add `src/ds_workspace_mcp/config.py`.
- [x] Centralize environment-backed settings in a typed model.
- [x] Validate transport, paths, row limits, host, port, and log level.
- [x] Add tests for defaults and invalid settings.
- [x] Document runtime configuration.

Acceptance criteria:
- The codebase stops reading environment variables directly outside the configuration layer.
- Invalid configuration fails fast with clear validation errors.
- Tests cover defaults and invalid settings.

### 2. Richer profiling

- [x] Add `src/ds_workspace_mcp/profiling.py`.
- [x] Add numeric, categorical, boolean, and datetime summaries.
- [x] Keep output size bounded and deterministic.
- [x] Add Pydantic response models for richer summaries.
- [x] Add focused unit tests.

Acceptance criteria:
- `profile_csv` keeps backward compatibility while returning richer structured data.
- Profiling remains safe and does not emit oversized payloads.
- Numeric, categorical, boolean, and datetime summaries are covered by tests.

### 3. Structured logging

- [x] Add `src/ds_workspace_mcp/logging_config.py`.
- [x] Configure logging from validated settings.
- [x] Log tool invocations and validation failures without leaking dataset contents.
- [x] Document logging configuration.

Acceptance criteria:
- Logs include level, timestamp, module, and message.
- Full dataset payloads are not logged.
- Default local behavior remains simple.

### 4. GitHub Actions CI

- [x] Add `.github/workflows/ci.yml`.
- [x] Run `ruff`, `mypy`, and `pytest` on pushes and pull requests.
- [x] Use supported Python versions from the package metadata.

Acceptance criteria:
- Pull requests and pushes trigger automated checks.
- CI runs the same commands expected locally.

### 5. DuckDB query support

- [x] Add DuckDB as a dependency.
- [x] Create `src/ds_workspace_mcp/sql/duckdb_engine.py`.
- [x] Add a safe `query_csv_with_duckdb` tool.
- [x] Enforce read-only behavior, statement restrictions, and row limits.
- [x] Add tests for valid queries and blocked SQL.

Acceptance criteria:
- Only safe read-only queries against datasets inside the data root are allowed.
- Final row limits are always enforced.
- Query validation paths are tested.

## v0.3

### 1. SQLite support

- [x] Create `src/ds_workspace_mcp/sql/sqlite_engine.py`.
- [x] Add database discovery, table listing, schema description, and safe querying.
- [x] Reuse current path safety patterns.
- [x] Add SQLite fixtures and tests.

Acceptance criteria:
- SQLite databases inside the configured data directory are queryable in read-only mode.
- Destructive and schema-changing queries are rejected.

### 2. Metadata caching

- [x] Create `src/ds_workspace_mcp/cache.py`.
- [x] Cache profile results by path, size, mtime, and options.
- [x] Add cache enable/disable and max-entry settings.
- [x] Add tests for invalidation and disabled mode.

Acceptance criteria:
- Repeated profiling uses valid cached metadata.
- Stale cache entries are invalidated when files change.

### 3. Correlation and leakage diagnostics

- [x] Add correlation summarization for numeric columns.
- [x] Add heuristic leakage warnings tied to a target column.
- [x] Keep results concise and assistant-friendly.
- [x] Add tests for edge cases and false-positive-prone heuristics.

Acceptance criteria:
- Correlation output is ranked and bounded.
- Leakage diagnostics are clearly framed as heuristics.

### 4. Time-series validation

- [x] Create `src/ds_workspace_mcp/timeseries.py`.
- [x] Validate timestamp parsing, sorting, duplicates, gaps, and inferred frequency.
- [x] Support grouped series checks.
- [x] Add tests for regular and irregular series.

Acceptance criteria:
- Forecasting-readiness issues are surfaced in a structured result.
- Validation handles grouped and irregular datasets safely.

## Recommended Next Sequence

1. Land the configuration layer.
2. Expand profiling with bounded structured outputs.
3. Add structured logging.
4. Add CI.
5. Add DuckDB support.
6. Add SQLite and cache support.
7. Add ML-oriented diagnostics after the core data-access layer is stable.

## Additional Features

### Baseline model evaluation

- [x] Add `src/ds_workspace_mcp/ml/baselines.py`.
- [x] Add regression, binary classification, and multiclass baseline evaluation.
- [x] Keep the implementation limited to dummy baselines.
- [x] Add tests for supported tasks and validation failures.

Acceptance criteria:
- Dummy baselines run for supported supervised tasks.
- Missing target columns and insufficient data fail clearly.
- Returned metrics are structured and bounded.

### Synthetic healthcare dataset generation

- [x] Add `src/ds_workspace_mcp/synthetic/healthcare.py`.
- [x] Generate realistic clinic operations columns with reproducible randomness.
- [x] Add a console command for writing datasets into `data/` or a custom path.
- [x] Add tests for schema, reproducibility, row counts, and date ranges.

Acceptance criteria:
- The generator produces a stable schema with realistic operational fields.
- Generation is reproducible for a fixed seed.
- The console command writes a CSV dataset successfully.

### Local CLI

- [x] Add `src/ds_workspace_mcp/cli.py`.
- [x] Support `serve`, `list-datasets`, `profile-dataset`, and `generate-sample-healthcare-data`.
- [x] Keep `ds-workspace-mcp` as the main console entrypoint.
- [x] Add CLI tests for successful and invalid commands.

Acceptance criteria:
- The CLI can serve the MCP server and run common local development tasks.
- Invalid options return a non-zero exit code.
- Dataset listing and profiling work against the configured data root.
