# API Contract

## Purpose

This document defines the versioned public surface for `ds-workspace-mcp`.

Starting with `v1.0.0`, the names and high-level result shapes listed here are treated as the public contract. Internal modules, helper functions, log messages, and undocumented implementation details are not part of that contract.

## Versioning Rules

The project follows semantic versioning.

- Patch releases may fix bugs, tighten validation, improve documentation, and add non-breaking fields to structured responses.
- Minor releases may add new MCP tools, resources, prompts, CLI commands, environment variables, and optional response fields.
- Major releases may rename or remove public capabilities, change required arguments, or change existing response semantics.

The following are considered breaking changes and require a major release:

- Renaming or removing a documented MCP tool, resource, prompt, CLI command, or environment variable.
- Changing a response field name or removing a documented field.
- Changing an argument name, making an optional argument required, or narrowing accepted values incompatibly.
- Changing a result from structured data to plain text, or vice versa, for an existing capability.

The following are considered non-breaking:

- Adding a new tool, resource, prompt, CLI command, or optional environment variable.
- Adding optional fields to structured responses.
- Improving wording inside heuristic warning descriptions.
- Tightening invalid-input validation where previously undefined behavior existed.

## Public MCP Surface

### Resources

#### `datasets://catalog`

- Stable name: `datasets://catalog`
- Return type: text payload
- Stable behavior: returns newline-separated CSV file names visible under `MCP_DATA_ROOT`
- Empty-state behavior: returns the sentence `No CSV datasets found in the configured data directory.`

#### `databases://sqlite`

- Stable name: `databases://sqlite`
- Return type: text payload
- Stable behavior: returns newline-separated SQLite database file names visible under `MCP_DATA_ROOT`
- Empty-state behavior: returns the sentence `No SQLite databases found in the configured data directory.`

### Tools

#### `preview_csv(file_name: str, rows: int = 5)`

- Stable name: `preview_csv`
- Purpose: preview the first rows of a CSV file inside `MCP_DATA_ROOT`
- Stable result fields:
  - `file_name: str`
  - `columns: list[str]`
  - `rows: list[dict[str, object | null]]`
  - `row_count: int`
- Stable behavior:
  - `rows` is bounded by the validated `rows` argument and runtime limits
  - scalar values are returned in JSON-friendly form

#### `profile_csv(file_name: str)`

- Stable name: `profile_csv`
- Purpose: return a bounded structural profile for one CSV dataset
- Stable result fields:
  - `file_name: str`
  - `row_count: int`
  - `column_count: int`
  - `columns: list[str]`
  - `dtypes: dict[str, str]`
  - `missing_values: dict[str, int]`
  - `missing_percentage: dict[str, float]`
  - `numeric_columns: list[NumericColumnProfile]`
  - `categorical_columns: list[CategoricalColumnProfile]`
  - `boolean_columns: list[BooleanColumnProfile]`
  - `datetime_columns: list[DatetimeColumnProfile]`
  - `profiling_limits.max_categorical_values: int`
- Stable profile item fields:
  - `NumericColumnProfile`: `column`, `count`, `mean`, `std`, `min`, `q25`, `median`, `q75`, `max`
  - `CategoricalColumnProfile`: `column`, `count`, `unique_count`, `top_value`, `top_value_frequency`, `top_values`
  - `ValueFrequency`: `value`, `count`
  - `BooleanColumnProfile`: `column`, `true_count`, `false_count`, `missing_count`
  - `DatetimeColumnProfile`: `column`, `count`, `min`, `max`
- Heuristic notes:
  - categorical top values are intentionally bounded
  - datetime detection is conservative and may leave ambiguous text columns in categorical output

#### `detect_csv_issues(file_name: str)`

- Stable name: `detect_csv_issues`
- Purpose: return simple data-quality issues for a CSV dataset
- Stable result shape: `list[DatasetIssue]`
- Stable item fields:
  - `column: str`
  - `issue_type: str`
  - `description: str`
- Heuristic notes:
  - issue detection is intentionally conservative
  - warnings are review signals, not proof of unusable data

#### `query_csv_with_duckdb(file_name: str, sql: str, limit: int | None = None)`

- Stable name: `query_csv_with_duckdb`
- Purpose: run one bounded read-only DuckDB query against the temporary table `dataset`
- Stable result fields:
  - `file_name: str`
  - `columns: list[str]`
  - `rows: list[dict[str, object | null]]`
  - `row_count: int`
  - `limit_applied: int`
- Stable behavior:
  - only a single `SELECT` or `WITH` statement is accepted
  - queries must reference the table name `dataset`
  - external file-access and schema-changing SQL are rejected

#### `list_sqlite_databases()`

- Stable name: `list_sqlite_databases`
- Implementation note: the Python function is named `list_sqlite_databases_tool`, but the MCP tool name exposed to clients is `list_sqlite_databases`
- Stable result shape: `list[SQLiteDatabaseInfo]`
- Stable item fields:
  - `file_name: str`

#### `list_sqlite_tables(file_name: str)`

- Stable name: `list_sqlite_tables`
- Stable result shape: `list[str]`

#### `describe_sqlite_table(file_name: str, table_name: str)`

- Stable name: `describe_sqlite_table`
- Stable result fields:
  - `file_name: str`
  - `table_name: str`
  - `columns: list[SQLiteColumnInfo]`
- Stable column fields:
  - `cid: int`
  - `name: str`
  - `data_type: str`
  - `not_null: bool`
  - `default_value: str | null`
  - `is_primary_key: bool`

#### `query_sqlite(file_name: str, sql: str, limit: int | None = None)`

- Stable name: `query_sqlite`
- Stable result fields:
  - `file_name: str`
  - `columns: list[str]`
  - `rows: list[dict[str, object | null]]`
  - `row_count: int`
  - `limit_applied: int`
- Stable behavior:
  - only a single `SELECT` or `WITH` statement is accepted
  - database access is read-only
  - schema-changing SQL is rejected

#### `summarize_correlations(file_name: str, method: str = "pearson")`

- Stable name: `summarize_correlations`
- Supported `method` values:
  - `pearson`
  - `spearman`
  - `kendall`
- Stable result fields:
  - `file_name: str`
  - `method: str`
  - `numeric_columns: list[str]`
  - `top_correlations: list[CorrelationPair]`
- Stable pair fields:
  - `left_column: str`
  - `right_column: str`
  - `correlation: float`
  - `absolute_correlation: float`
- Heuristic notes:
  - results are capped to the top ranked pairs
  - the ranking is descriptive only and does not imply causality

#### `detect_possible_target_leakage(file_name: str, target_column: str)`

- Stable name: `detect_possible_target_leakage`
- Stable result fields:
  - `file_name: str`
  - `target_column: str`
  - `warnings: list[LeakageWarning]`
- Stable warning fields:
  - `column: str`
  - `warning_type: str`
  - `description: str`
- Heuristic notes:
  - warnings such as `target_name_overlap`, `identifier_like`, `high_correlation`, `duplicate_values`, and `datetime_review` are review signals
  - warning descriptions may evolve without changing the contract
  - absence of warnings is not proof that leakage is impossible

#### `validate_time_series_dataset(file_name: str, time_column: str, target_column: str | None = None, group_column: str | None = None)`

- Stable MCP name: `validate_time_series_dataset`
- Implementation note: the Python function is named `validate_time_series_dataset_tool`
- Stable result fields:
  - `file_name: str`
  - `time_column: str`
  - `target_column: str | null`
  - `group_column: str | null`
  - `row_count: int`
  - `parsed_timestamp_count: int`
  - `duplicate_timestamps: int`
  - `is_sorted: bool`
  - `inferred_frequency: str | null`
  - `missing_intervals: int`
  - `missing_target_values: int | null`
  - `group_summaries: list[GroupTimeSeriesSummary]`
  - `warnings: list[TimeSeriesWarning]`
- Stable group summary fields:
  - `group: str`
  - `row_count: int`
  - `duplicate_timestamps: int`
  - `missing_intervals: int`
  - `inferred_frequency: str | null`
- Stable warning fields:
  - `warning_type: str`
  - `description: str`
  - `group: str | null`
- Heuristic notes:
  - inferred frequency and missing-interval counts are best-effort summaries
  - history sufficiency warnings are baseline-readiness guidance, not modeling guarantees

#### `evaluate_baseline_model(file_name: str, target_column: str, task_type: str, test_size: float = 0.2, random_state: int = 42)`

- Stable name: `evaluate_baseline_model`
- Supported `task_type` values:
  - `regression`
  - `binary_classification`
  - `multiclass_classification`
- Stable result fields:
  - `file_name: str`
  - `target_column: str`
  - `task_type: str`
  - `train_rows: int`
  - `test_rows: int`
  - `regression_metrics: RegressionMetrics | null`
  - `classification_metrics: ClassificationMetrics | null`
- Stable regression metric fields:
  - `mae: float`
  - `rmse: float`
  - `r2: float`
- Stable classification metric fields:
  - `accuracy: float`
  - `balanced_accuracy: float`
  - `macro_f1: float`
- Heuristic notes:
  - this tool uses dummy baselines only
  - metric values are comparison baselines, not target production quality thresholds

### Prompts

#### `dataset_analysis_prompt(file_name: str, objective: str = "exploratory analysis")`

- Stable name: `dataset_analysis_prompt`
- Stable return type: text prompt
- Stable behavior:
  - references the requested `file_name`
  - includes the requested `objective`
  - instructs the client to inspect schema, missingness, suspicious columns, target ideas, baseline approaches, and validation concerns
- Contract note:
  - exact prose may change across patch and minor releases
  - the prompt remains a reusable analysis scaffold, not a machine-parseable schema

## CLI Contract

The `ds-workspace-mcp` console script is public.

### Commands

- `ds-workspace-mcp`
  - default behavior: equivalent to `ds-workspace-mcp serve`
- `ds-workspace-mcp serve`
  - starts the MCP server using configured transport settings
- `ds-workspace-mcp list-datasets`
  - prints CSV file names, one per line
- `ds-workspace-mcp profile-dataset <file_name>`
  - prints the `profile_csv` result as JSON
- `ds-workspace-mcp generate-sample-healthcare-data [--output] [--start-date] [--days] [--clinics] [--seed]`
  - writes a synthetic healthcare CSV and prints the output path

## Environment Variable Contract

These runtime settings are public and documented:

- `MCP_DATA_ROOT`
- `MCP_TRANSPORT`
- `MCP_HOST`
- `MCP_PORT`
- `MCP_MAX_PREVIEW_ROWS`
- `MCP_MAX_SQL_ROWS`
- `MCP_MAX_CATEGORICAL_VALUES`
- `MCP_PROFILE_CACHE_ENABLED`
- `MCP_PROFILE_CACHE_MAX_ENTRIES`
- `MCP_LOG_LEVEL`
- `MCP_API_KEY`
- `MCP_TRACING_ENABLED`
- `MCP_TRACING_SERVICE_NAME`
- `MCP_TRACING_CONSOLE_EXPORTER`

Stable expectations:

- blank `MCP_API_KEY` disables HTTP bearer-token auth
- `MCP_TRANSPORT` supports `stdio` and `streamable-http`
- validation bounds on numeric settings may reject invalid values but will not silently reinterpret them

## Error Contract

User-facing failures may surface through these stable exception categories:

- `InvalidDatasetNameError`
- `UnsupportedFileTypeError`
- `PathTraversalError`
- `DatasetNotFoundError`
- `InvalidSQLError`
- `ProfilingError`
- `InsufficientDataError`

Exact wording may change. Error category meaning is stable.

## Out of Scope

The following are not part of the versioned public contract:

- internal module layout
- helper function names not exposed through MCP or CLI
- log record structure and message wording
- trace span names and attributes
- exact ordering of heuristic warnings unless explicitly documented above
