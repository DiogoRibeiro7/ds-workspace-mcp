# Architecture Overview

## High-Level Structure

`ds-workspace-mcp` is a thin MCP server layer over a set of bounded dataset utilities. The design keeps transport, validation, and data operations separate enough that the public surface can stay stable while the implementation evolves.

## Main Components

### `server.py`

Responsibilities:

- configures logging and tracing at process startup
- creates the configured MCP server through `mcp/app.py`
- runs the selected transport

This file is the public MCP entrypoint and remains intentionally small. It re-exports
the existing wrapper names for import compatibility, while runtime startup and tests
create fresh server instances through the factory.

### `mcp/app.py`

Responsibilities:

- exposes `create_mcp_server(settings)` as the FastMCP application factory
- wires optional HTTP auth through public FastMCP constructor arguments
- records resource, tool, and prompt decorator registrations so each server instance
  receives the same public MCP surface

### `mcp/resources/`, `mcp/tools/`, and `mcp/prompts/`

Responsibilities:

- contain MCP-facing wrappers grouped by domain
- preserve logging and tracing at MCP boundaries
- delegate data access, modeling, SQL, report, and diagnostic behavior to domain modules
- avoid embedding business logic in transport registration code

### `cli.py`

Responsibilities:

- exposes the console workflow
- dispatches to `serve`
- provides local utilities such as dataset listing, JSON profiling, and synthetic dataset generation

### `config.py`

Responsibilities:

- defines validated runtime settings
- reads environment variables and `.env`
- enforces bounds for ports, preview limits, SQL limits, cache sizes, and tracing settings

This is the central configuration boundary for the application.

### `core.py`

Responsibilities:

- exposes CSV-compatible public helpers backed by the dataset registry
- builds dataset previews
- orchestrates profiling and issue detection

This is the current CSV workflow facade. Format-neutral path resolution and
dispatch live in `datasets/`.

### `datasets/`

Responsibilities:

- models dataset references as relative names under an approved data root
- centralizes path containment, format dispatch, file-size checks, metadata, and fingerprints
- exposes a small `DatasetReader` protocol for format-specific frame loading and metadata
- keeps CSV, Parquet, JSON, and Excel support behind format-specific readers
- inspects Parquet schema and row counts through DuckDB without materializing full files
- accepts JSON arrays of records and NDJSON records, rejecting nested structures instead of flattening silently
- supports `.xlsx` workbooks through `openpyxl`; multi-sheet workbooks require `file.xlsx#SheetName` after sheet discovery
- preserves existing CSV-specific APIs while exposing additive generalized dataset tools

### `profiling.py`

Responsibilities:

- converts a pandas `DataFrame` into a bounded structured profile
- summarizes numeric, categorical, boolean, and datetime-like columns
- records the runtime profiling limits applied to the result

### `aggregation.py`

Responsibilities:

- accepts typed aggregation requests rather than executable expressions
- validates group, metric, filter, and ordering columns against loaded dataset schema
- allowlists aggregation and filter operations
- bounds grouping cardinality and returned rows through configured SQL row limits
- normalizes result values for JSON output

### `drift.py`

Responsibilities:

- compares two approved datasets through the existing safe dataset-loading path
- separates structural schema differences from statistical drift diagnostics
- reports added/removed columns, dtype changes, null-rate shifts, analyzed row-count changes, and bounded categorical cardinality changes
- computes transparent numeric, categorical, and timestamp drift summaries without interpreting differences as causal effects
- bounds comparison work through the configured SQL row limit and reports whether each side was truncated

### `sql/duckdb_engine.py`

Responsibilities:

- applies DuckDB connection-level security policy before user SQL executes
- parses user SQL and validates base relation references against an explicit allowlist
- rejects external scan functions and destructive SQL as defense in depth
- registers the CSV as a temporary `dataset` table
- executes bounded read-only analytical queries
- normalizes tabular results into JSON-friendly rows

### `sql/sqlite_engine.py`

Responsibilities:

- resolves SQLite files safely
- lists databases and tables
- describes table schemas
- executes bounded read-only SQLite queries through read-only connections

### `diagnostics.py`

Responsibilities:

- computes bounded correlation summaries
- emits heuristic target-leakage warnings with severity and confidence
- treats high correlation and name overlap as review evidence rather than proof of leakage

These outputs are intentionally advisory rather than definitive.

### `timeseries.py`

Responsibilities:

- validates timestamp parsing
- inspects sorting, duplicates, structured frequency confidence, and missing intervals
- classifies time series as regular, approximately regular, irregular, insufficient, or grouped heterogeneous before counting missing intervals
- emits baseline-readiness warnings for time-series workflows

### `ml/baselines.py`

Responsibilities:

- evaluates dummy regression and classification baselines
- resolves explicit validation strategies for random, stratified, chronological, and grouped train/test splits
- checks classification class support before splitting and train/test class representation before reporting metrics
- validates split-specific arguments and reports metadata explaining how metrics were produced
- returns structured metrics for comparison against future models

### `reports/`

Responsibilities:

- keeps report Pydantic models in `reports/models.py`, separate from filesystem I/O
- stores and resolves markdown artifacts through `reports/storage.py` and `reports/paths.py`
- parses markdown sections in `reports/parsing.py`, including repeated headings, nested sections, empty sections, and fenced code blocks
- compares reports and extracted sections through pure diff helpers in `reports/diff.py`
- keeps report rendering in `reports/rendering.py`, while catalog and section workflows live in `reports/catalog.py` and `reports/sections.py`

`report_export.py` and `report_storage.py` remain compatibility facades for existing imports.

### Supporting modules

- `auth.py`: optional shared-token auth for HTTP mode
- `logging_config.py`: process logging setup
- `tracing.py`: optional OpenTelemetry integration
- `cache.py`: typed, thread-safe in-memory profile caching with path-free metrics
- `exceptions.py`: stable application error categories
- `synthetic/`: reproducible sample dataset generators

## Request Flow

### CSV tool flow

1. An MCP client invokes a tool such as `profile_csv`.
2. `server.py` logs and traces the tool boundary.
3. `core.py` resolves `file_name` under `MCP_DATA_ROOT`.
4. The relevant subsystem runs:
   - `datasets/` and `profiling.py` for safe CSV loading and summaries
   - `diagnostics.py` for heuristics
   - `sql/duckdb_engine.py` for SQL
   - `timeseries.py` for forecasting-readiness checks
   - `ml/baselines.py` for dummy model evaluation
5. Structured results are returned through FastMCP as JSON.

### SQLite tool flow

1. An MCP client invokes a SQLite tool.
2. `sqlite_engine.py` resolves the database path under `MCP_DATA_ROOT`.
3. The database is opened in read-only mode.
4. Schema or query results are normalized into structured responses.

## Data Flow Principles

- all public operations start from validated names rather than arbitrary paths
- dataset references are resolved through the format-neutral registry boundary
- file reads happen only after data-root resolution
- SQL results are normalized to JSON-friendly scalar values
- expensive or verbose outputs are bounded before returning to the client
- heuristics are labeled as heuristics rather than hidden behind deterministic wording

## Runtime Modes

### `stdio`

- best for local single-client launches
- no HTTP listener
- no app-layer auth

### `streamable-http`

- best for long-running local or containerized use
- can be protected with `MCP_API_KEY`
- exposes the MCP endpoint at `/mcp`

## Cross-Cutting Concerns

### Validation

- environment validation happens in `config.py`
- path and file-type validation happen in `core.py` and `sqlite_engine.py`
- DuckDB SQL validation combines engine settings, parsed relation allowlisting, and defense-in-depth statement/function rejection before query execution
- SQLite SQL validation happens before query execution and SQLite databases are opened read-only
- SQL timeout guards cover execution and result materialization, and timeout/cancellation metadata is logged and attached to tracing spans when tracing is enabled
- baseline validation split configuration rejects incoherent strategy, time-column, group-column, and shuffle combinations before model evaluation

### Observability

- logs capture operational metadata
- tracing is optional and non-fatal if dependencies are missing

### Caching

- profile results can be cached in memory
- cache keys include file path, size, modified time, and profiling options
- cache configuration is applied through public methods rather than private field mutation
- cache metrics report hits, misses, evictions, and current entry count without exposing local paths

## Design Tradeoffs

- pandas-first CSV handling keeps the implementation simple, but very large files may still be expensive
- Parquet metadata and preview use DuckDB-backed bounded reads; generalized SQL still registers a safe in-memory `dataset` relation before user SQL executes
- DuckDB SQL validation uses structural parsing for relation access, but query complexity and resource exhaustion still require operational limits and cancellation handling
- auth is intentionally minimal to support local and small self-hosted use without introducing a full identity layer
- heuristics are exposed because analytical guidance is useful, but they are documented as non-authoritative
