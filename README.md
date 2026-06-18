# Data Science Workspace MCP Server

![CI](https://github.com/DiogoRibeiro7/ds-workspace-mcp/actions/workflows/ci.yml/badge.svg)

A small but practical **Model Context Protocol (MCP)** server for data science workflows.

It lets an MCP-compatible assistant safely inspect local CSV datasets through:

- **Resources** for dataset discovery.
- **Overview tools** for fast first-pass dataset understanding.
- **Tools** for CSV preview, profiling, SQL access, diagnostics, and baseline evaluation.
- **Report artifact tools** for saving, searching, comparing, extracting, and reusing modeling reports.
- **Prompts** for reusable dataset analysis instructions.

This project is designed as a clean portfolio-ready starter repo. It is intentionally focused, typed, tested, and safe by default.

## Current scope

Today the repository covers four practical workflows:

- Safe local dataset access for CSV and SQLite sources.
- Lightweight analytical diagnostics, including leakage review, correlations, and time-series checks.
- Baseline modeling planning and markdown report generation.
- Saved report lifecycle management, including cataloging, search, section extraction, section export, and section-aware diffs.

---

## Why this project exists

Many AI assistants can reason well, but they need controlled access to real data and real tools.

This MCP server exposes a local analytical workspace without giving the model arbitrary file-system access. The server only reads CSV files from a configured data directory.

Good use cases:

- quick dataset inspection;
- exploratory data analysis planning;
- data-quality checks;
- building a portfolio example around AI tooling and data science infrastructure.

---

## Project structure

```text
ds-workspace-mcp/
├── data/
├── docs/
├── examples/
├── notebooks/
├── src/
│   └── ds_workspace_mcp/
│       ├── cli.py
│       ├── config.py
│       ├── core.py
│       ├── diagnostics.py
│       ├── experiment_plan.py
│       ├── feature_selection.py
│       ├── modeling_readiness.py
│       ├── modeling_report.py
│       ├── overview.py
│       ├── profiling.py
│       ├── report_export.py
│       ├── server.py
│       ├── timeseries.py
│       ├── ml/
│       ├── sql/
│       └── synthetic/
├── tests/
├── .github/
├── docker-compose.yml
├── Dockerfile
├── README.md
└── pyproject.toml
```

---

## Requirements

- Python 3.11+
- Poetry
- Node.js, only if you want to use the MCP Inspector through `npx`

---

## Installation

```bash
poetry install
```

## Configuration

The server reads configuration from environment variables or a local `.env` file.

- `MCP_DATA_ROOT`: directory that contains readable datasets. Defaults to `data`.
- `MCP_TRANSPORT`: `stdio` or `streamable-http`. Defaults to `streamable-http`.
- `MCP_HOST`: bind host for HTTP mode. Defaults to `127.0.0.1`.
- `MCP_PORT`: bind port for HTTP mode. Defaults to `8000`.
- `MCP_MAX_PREVIEW_ROWS`: maximum allowed value for `preview_csv`. Defaults to `50`.
- `MCP_MAX_SQL_ROWS`: reserved maximum row limit for upcoming SQL tools. Defaults to `1000`.
- `MCP_MAX_SQL_QUERY_LENGTH`: maximum allowed SQL text length for query tools. Defaults to `20000`.
- `MCP_SQL_TIMEOUT_MS`: maximum SQL execution time before interruption. Defaults to `5000`.
- `MCP_MAX_CATEGORICAL_VALUES`: maximum top-value examples returned per categorical column in `profile_csv`. Defaults to `5`.
- `MCP_MAX_DATASET_BYTES`: maximum readable CSV dataset size in bytes. Defaults to `25000000`.
- `MCP_PROFILE_CACHE_ENABLED`: enable or disable in-memory profile caching. Defaults to `true`.
- `MCP_PROFILE_CACHE_MAX_ENTRIES`: maximum cached profile entries. Defaults to `128`.
- `MCP_LOG_LEVEL`: server log level. Defaults to `INFO`.
- `MCP_API_KEY`: optional shared bearer token for Streamable HTTP mode. Disabled by default.
- `MCP_TRACING_ENABLED`: enable optional OpenTelemetry spans. Defaults to `false`.
- `MCP_TRACING_SERVICE_NAME`: service name reported in traces. Defaults to `ds-workspace-mcp`.
- `MCP_TRACING_CONSOLE_EXPORTER`: print spans to stdout through the OpenTelemetry console exporter. Defaults to `false`.

Example:

```bash
MCP_DATA_ROOT=./data
MCP_TRANSPORT=streamable-http
MCP_HOST=127.0.0.1
MCP_PORT=8000
MCP_MAX_PREVIEW_ROWS=50
MCP_MAX_SQL_ROWS=1000
MCP_MAX_SQL_QUERY_LENGTH=20000
MCP_SQL_TIMEOUT_MS=5000
MCP_MAX_CATEGORICAL_VALUES=5
MCP_MAX_DATASET_BYTES=25000000
MCP_PROFILE_CACHE_ENABLED=true
MCP_PROFILE_CACHE_MAX_ENTRIES=128
MCP_LOG_LEVEL=INFO
MCP_API_KEY=
MCP_TRACING_ENABLED=false
MCP_TRACING_SERVICE_NAME=ds-workspace-mcp
MCP_TRACING_CONSOLE_EXPORTER=false
```

## Logging

The server emits structured logs with timestamp, level, module, and message.

- Tool and resource invocations are logged with dataset names and safe counts only.
- Validation failures are logged clearly.
- Full dataset contents and preview row payloads are intentionally not logged.

Set the log level with `MCP_LOG_LEVEL`, for example:

```bash
MCP_LOG_LEVEL=DEBUG
```

## Tracing

OpenTelemetry tracing is optional production polish.

Install the optional dependencies with:

```bash
poetry install --extras opentelemetry
```

To enable local tracing with console output:

```bash
MCP_TRACING_ENABLED=true
MCP_TRACING_CONSOLE_EXPORTER=true
poetry run ds-workspace-mcp serve
```

Current spans cover dataset resolution, CSV reads, profiling, SQL query execution, and MCP tool boundaries.

If tracing is enabled without the optional dependencies installed, the server continues to run and logs a warning instead of failing.

---

## Troubleshooting

- `Dataset not found: ...`: the file name must exist inside `MCP_DATA_ROOT`, and the server only sees files under that directory.
- `Only CSV files are supported.` or `Only SQLite files are supported.`: the requested file extension is not allowed for that tool.
- `Access outside the configured data directory is not allowed.`: the request attempted path traversal such as `../...`.
- `Could not profile dataset: ...`: the file could be opened but could not be profiled safely; validate the CSV structure and encoding.
- `Could not read dataset: ...`: the CSV could not be decoded or parsed safely.
- `Dataset exceeds the maximum allowed size ...`: the file is larger than the configured dataset-size guardrail.
- `Destructive or schema-changing SQL is not allowed.`: the SQL tool only accepts bounded read-only `SELECT` or `WITH` queries.
- `SQL query exceeded the timeout ...`: the query ran longer than the configured SQL timeout.

These errors intentionally avoid exposing absolute local paths in responses.

---

## Run with Streamable HTTP

```bash
MCP_TRANSPORT=streamable-http poetry run ds-workspace-mcp
```

By default, the server reads datasets from `./data`.

You can override that directory:

```bash
MCP_DATA_ROOT=/path/to/csv/files MCP_TRANSPORT=streamable-http poetry run ds-workspace-mcp
```

Then connect with the MCP Inspector:

```bash
npx -y @modelcontextprotocol/inspector
```

Use this URL:

```text
http://localhost:8000/mcp
```

---

## Run with stdio

```bash
MCP_TRANSPORT=stdio poetry run ds-workspace-mcp
```

This is useful when connecting the server directly to an MCP client that launches local servers.

## Synthetic Dataset

The repository also includes a reproducible healthcare operations dataset generator.

Generate a fresh sample into `data/`:

```bash
poetry run generate-sample-healthcare-data
```

Custom example:

```bash
poetry run generate-sample-healthcare-data --output data/custom_clinic_usage.csv --days 180 --clinics 6 --seed 7
```

Generated columns:

- `clinic_id`
- `date`
- `appointments_scheduled`
- `appointments_completed`
- `cancellations`
- `no_shows`
- `marketing_campaign`
- `local_holiday`
- `staff_available`
- `average_wait_time`
- `patient_satisfaction_score`

The generator includes weekday effects, seasonal demand, campaign lift, holiday effects, random noise, and light missingness in a couple of operational fields.

## CLI

The main console command now exposes a small local workflow CLI.

Serve the MCP server:

```bash
poetry run ds-workspace-mcp serve
```

`poetry run ds-workspace-mcp` also defaults to `serve`.

List available datasets:

```bash
poetry run ds-workspace-mcp list-datasets
```

Profile one dataset as JSON:

```bash
poetry run ds-workspace-mcp profile-dataset sample_clinic_usage.csv
```

Build a first-pass modeling plan as JSON:

```bash
poetry run ds-workspace-mcp plan-modeling sample_clinic_usage.csv --target-column appointments_completed
```

Build a markdown modeling report:

```bash
poetry run ds-workspace-mcp report-modeling sample_clinic_usage.csv --target-column appointments_completed
```

Save a markdown modeling report into `reports/`:

```bash
poetry run ds-workspace-mcp save-modeling-report sample_clinic_usage.csv --target-column appointments_completed --output-name clinic-usage-report.md
```

List saved modeling reports:

```bash
poetry run ds-workspace-mcp list-modeling-reports
```

Search saved modeling reports:

```bash
poetry run ds-workspace-mcp search-modeling-reports clinic
```

Search saved modeling report content:

```bash
poetry run ds-workspace-mcp search-modeling-report-content elevated
```

Search the latest saved modeling report content:

```bash
poetry run ds-workspace-mcp search-latest-modeling-report-content elevated
```

Search saved modeling report sections:

```bash
poetry run ds-workspace-mcp search-modeling-report-sections risk
```

Search section headings in the latest saved modeling report:

```bash
poetry run ds-workspace-mcp search-latest-modeling-report-sections risk
```

Summarize recurring modeling report sections:

```bash
poetry run ds-workspace-mcp summarize-modeling-report-sections
```

List the most recent modeling reports:

```bash
poetry run ds-workspace-mcp list-recent-modeling-reports --limit 3
```

Summarize saved modeling reports:

```bash
poetry run ds-workspace-mcp summarize-modeling-reports --limit 3
```

Read one saved modeling report:

```bash
poetry run ds-workspace-mcp read-modeling-report clinic-usage-report.md
```

List section headings from one saved modeling report:

```bash
poetry run ds-workspace-mcp list-modeling-report-sections clinic-usage-report.md
```

List section headings from the latest saved modeling report:

```bash
poetry run ds-workspace-mcp list-latest-modeling-report-sections
```

Read one section from a saved modeling report:

```bash
poetry run ds-workspace-mcp read-modeling-report-section clinic-usage-report.md "Summary"
```

Read one section from the latest saved modeling report:

```bash
poetry run ds-workspace-mcp read-latest-modeling-report-section "Summary"
```

Save one section from a saved modeling report:

```bash
poetry run ds-workspace-mcp save-modeling-report-section clinic-usage-report.md "Risks"
```

Save one section from the latest saved modeling report:

```bash
poetry run ds-workspace-mcp save-latest-modeling-report-section "Risks"
```

Compare one section across two saved modeling reports:

```bash
poetry run ds-workspace-mcp compare-modeling-report-sections clinic-usage-report.md clinic-usage-v2.md "Risks"
```

Compare one section across the two most recent saved modeling reports:

```bash
poetry run ds-workspace-mcp compare-latest-modeling-report-sections "Risks"
```

Read the latest saved modeling report:

```bash
poetry run ds-workspace-mcp read-latest-modeling-report
```

Delete one saved modeling report:

```bash
poetry run ds-workspace-mcp delete-modeling-report clinic-usage-report.md
```

Rename one saved modeling report:

```bash
poetry run ds-workspace-mcp rename-modeling-report clinic-usage-report.md clinic-usage-v2.md
```

Rename the latest saved modeling report:

```bash
poetry run ds-workspace-mcp rename-latest-modeling-report clinic-usage-latest.md
```

Copy one saved modeling report:

```bash
poetry run ds-workspace-mcp copy-modeling-report clinic-usage-report.md clinic-usage-snapshot.md
```

Copy the latest saved modeling report:

```bash
poetry run ds-workspace-mcp copy-latest-modeling-report latest-clinic-snapshot.md
```

Inspect one saved modeling report:

```bash
poetry run ds-workspace-mcp inspect-modeling-report clinic-usage-report.md
```

Inspect the latest saved modeling report:

```bash
poetry run ds-workspace-mcp inspect-latest-modeling-report
```

Preview one saved modeling report:

```bash
poetry run ds-workspace-mcp preview-modeling-report clinic-usage-report.md
```

Compare two saved modeling reports:

```bash
poetry run ds-workspace-mcp compare-modeling-reports clinic-usage-report.md clinic-usage-v2.md
```

Compare the two most recent modeling reports:

```bash
poetry run ds-workspace-mcp compare-latest-modeling-reports
```

Preview the latest saved modeling report:

```bash
poetry run ds-workspace-mcp preview-latest-modeling-report
```

Generate a synthetic dataset through the main CLI:

```bash
poetry run ds-workspace-mcp generate-sample-healthcare-data --days 120 --clinics 5
```

## Examples

The repository includes runnable MCP client examples in [`examples/`](examples/).

Use stdio against a locally launched process:

```bash
poetry run python examples/stdio_client.py
```

Expected output starts with:

```text
Resources:
{
  "resources": [
```

Use Streamable HTTP after starting the server:

```bash
poetry run ds-workspace-mcp serve
poetry run python examples/http_client.py
```

Expected output starts with:

```text
Tools:
{
  "tools": [
```

The examples show how to:

- initialize an MCP client session;
- list resources or tools;
- call `preview_csv`, `profile_csv`, `detect_csv_issues`, and `summarize_correlations`.
- exit with a non-zero status and a concise stderr message if the connection fails.

---

## Available MCP capabilities

### Resource

```text
datasets://catalog
```

Returns the list of CSV files available in the configured data directory.

```text
databases://sqlite
```

Returns the list of SQLite database files available in the configured data directory.

```text
reports://modeling
```

Returns the list of saved modeling report file names from the local `reports/` directory.

### Tools

#### `summarize_dataset`

Return a compact first-pass overview of a dataset, including shape, missingness highlights, identifier-like columns, strongest correlations, and recommended next tools.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv"
}
```

#### `suggest_target_columns`

Suggest plausible target columns for modeling, with task-type hints and reasoning.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv"
}
```

#### `suggest_feature_columns`

Suggest which columns to include, review, or exclude for a supervised modeling target.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv",
  "target_column": "appointments_completed"
}
```

#### `assess_modeling_readiness`

Return a compact modeling-readiness summary that combines target suggestion, feature selection, leakage review, and next-step guidance.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv",
  "target_column": "appointments_completed"
}
```

#### `build_experiment_plan`

Build a concrete first-pass modeling plan with starter models, validation guidance, risks, metrics, and next steps.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv",
  "target_column": "appointments_completed"
}
```

#### `build_modeling_report`

Build a compact markdown report artifact for review or handoff.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv",
  "target_column": "appointments_completed"
}
```

#### `save_modeling_report`

Build and save a markdown report artifact inside the local `reports/` directory.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv",
  "target_column": "appointments_completed",
  "output_name": "clinic-usage-report.md"
}
```

#### `list_modeling_reports`

Return markdown modeling reports saved inside the local `reports/` directory.

#### `search_modeling_reports`

Return saved markdown modeling reports whose file names match a case-insensitive substring.

Arguments:

```json
{
  "query": "clinic"
}
```

#### `search_modeling_report_content`

Return saved markdown modeling reports whose content matches a case-insensitive text query.

Arguments:

```json
{
  "query": "elevated"
}
```

#### `search_latest_modeling_report_content`

Return content matches from the most recently modified saved modeling report.

Arguments:

```json
{
  "query": "elevated"
}
```

#### `search_modeling_report_sections`

Return saved modeling report sections whose headings match a case-insensitive text query.

Arguments:

```json
{
  "query": "risk"
}
```

#### `search_latest_modeling_report_sections`

Return section-heading matches from the most recently modified saved modeling report.

Arguments:

```json
{
  "query": "risk"
}
```

#### `summarize_modeling_report_sections`

Return a compact summary of recurring section headings across saved modeling reports.

#### `list_recent_modeling_reports`

Return the most recently modified saved markdown modeling reports.

Arguments:

```json
{
  "limit": 5
}
```

#### `summarize_modeling_report_catalog`

Return a compact summary of saved modeling reports, including total count, total size, and recent entries.

Arguments:

```json
{
  "limit": 5
}
```

#### `read_modeling_report`

Read one saved markdown modeling report from the local `reports/` directory.

Arguments:

```json
{
  "output_name": "clinic-usage-report.md"
}
```

#### `list_modeling_report_sections`

List markdown section headings discovered inside one saved modeling report.

Arguments:

```json
{
  "output_name": "clinic-usage-report.md"
}
```

#### `list_latest_modeling_report_sections`

List markdown section headings discovered inside the most recently modified saved modeling report.

#### `read_modeling_report_section`

Read one markdown section from a saved modeling report.

Arguments:

```json
{
  "output_name": "clinic-usage-report.md",
  "section_heading": "Summary"
}
```

#### `read_latest_modeling_report_section`

Read one markdown section from the most recently modified saved modeling report.

Arguments:

```json
{
  "section_heading": "Summary"
}
```

#### `save_modeling_report_section`

Save one markdown section from a saved modeling report as a new markdown artifact.

Arguments:

```json
{
  "output_name": "clinic-usage-report.md",
  "section_heading": "Risks",
  "new_output_name": "clinic-risks.md"
}
```

#### `save_latest_modeling_report_section`

Save one markdown section from the most recently modified saved modeling report as a new markdown artifact.

Arguments:

```json
{
  "section_heading": "Risks",
  "new_output_name": "latest-risks.md"
}
```

#### `compare_modeling_report_sections`

Return a bounded diff summary between matching sections in two saved modeling reports.

Arguments:

```json
{
  "output_name": "clinic-usage-report.md",
  "other_output_name": "clinic-usage-v2.md",
  "section_heading": "Risks"
}
```

#### `compare_latest_modeling_report_sections`

Return a bounded diff summary for one section across the two most recently modified saved modeling reports.

Arguments:

```json
{
  "section_heading": "Risks"
}
```

#### `read_latest_modeling_report`

Read the most recently modified saved markdown modeling report from the local `reports/` directory.

#### `delete_modeling_report`

Delete one saved markdown modeling report from the local `reports/` directory.

Arguments:

```json
{
  "output_name": "clinic-usage-report.md"
}
```

#### `rename_modeling_report`

Rename one saved markdown modeling report inside the local `reports/` directory.

Arguments:

```json
{
  "output_name": "clinic-usage-report.md",
  "new_output_name": "clinic-usage-v2.md"
}
```

#### `rename_latest_modeling_report`

Rename the most recently modified saved modeling report inside the local `reports/` directory.

Arguments:

```json
{
  "new_output_name": "clinic-usage-latest.md"
}
```

#### `copy_modeling_report`

Copy one saved markdown modeling report into a new artifact inside the local `reports/` directory.

Arguments:

```json
{
  "output_name": "clinic-usage-report.md",
  "new_output_name": "clinic-usage-snapshot.md"
}
```

#### `copy_latest_modeling_report`

Copy the most recently modified saved modeling report into a new artifact inside the local `reports/` directory.

Arguments:

```json
{
  "new_output_name": "latest-clinic-snapshot.md"
}
```

#### `inspect_modeling_report`

Return metadata for one saved markdown modeling report.

Arguments:

```json
{
  "output_name": "clinic-usage-report.md"
}
```

#### `inspect_latest_modeling_report`

Return metadata for the most recently modified saved modeling report.

#### `preview_modeling_report`

Return a bounded preview of one saved markdown modeling report.

Arguments:

```json
{
  "output_name": "clinic-usage-report.md"
}
```

#### `compare_modeling_reports`

Return a bounded unified diff summary between two saved markdown modeling reports.

Arguments:

```json
{
  "output_name": "clinic-usage-report.md",
  "other_output_name": "clinic-usage-v2.md"
}
```

#### `compare_latest_modeling_reports`

Return a bounded unified diff summary between the two most recently modified saved modeling reports.

#### `preview_latest_modeling_report`

Return a bounded preview of the most recently modified modeling report from the local `reports/` directory.

#### `preview_csv`

Preview the first rows of a CSV file.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv",
  "rows": 5
}
```

#### `profile_csv`

Return row count, column count, dtypes, missing values, missing percentages, and bounded column summaries for numeric, categorical, boolean, and datetime fields.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv"
}
```

Example response shape:

```json
{
  "file_name": "sample_clinic_usage.csv",
  "row_count": 120,
  "column_count": 6,
  "missing_values": {"wait_time": 4},
  "numeric_columns": [
    {
      "column": "appointments_completed",
      "count": 120,
      "mean": 83.2,
      "std": 9.4,
      "min": 61.0,
      "q25": 77.0,
      "median": 84.0,
      "q75": 90.0,
      "max": 103.0
    }
  ],
  "categorical_columns": [
    {
      "column": "clinic_id",
      "count": 120,
      "unique_count": 4,
      "top_value": "north",
      "top_value_frequency": 32,
      "top_values": [{"value": "north", "count": 32}]
    }
  ],
  "boolean_columns": [
    {
      "column": "local_holiday",
      "true_count": 8,
      "false_count": 112,
      "missing_count": 0
    }
  ],
  "datetime_columns": [
    {
      "column": "date",
      "count": 120,
      "min": "2024-01-01T00:00:00",
      "max": "2024-04-29T00:00:00"
    }
  ],
  "profiling_limits": {
    "max_categorical_values": 5
  }
}
```

Profiling limits:

- Categorical examples are intentionally bounded by `MCP_MAX_CATEGORICAL_VALUES`.
- The profiler returns summaries rather than raw wide-table payloads.
- Datetime detection is conservative to avoid misclassifying free-text columns.
- Profile results are cached in memory by file path, size, modified time, and profiling options.

#### `detect_csv_issues`

Detect simple data-quality issues, such as high missingness and likely identifier columns.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv"
}
```

#### `query_csv_with_duckdb`

Run a safe read-only DuckDB query against the CSV loaded as a temporary table named `dataset`.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv",
  "sql": "SELECT clinic_id, AVG(appointments_completed) AS avg_completed FROM dataset GROUP BY clinic_id ORDER BY avg_completed DESC",
  "limit": 10
}
```

#### `list_sqlite_databases_tool`

Return the SQLite database files available in the configured data directory.

#### `list_sqlite_tables`

List user tables from a SQLite database.

Arguments:

```json
{
  "file_name": "clinic_metrics.sqlite"
}
```

#### `describe_sqlite_table`

Describe the columns for a SQLite table.

Arguments:

```json
{
  "file_name": "clinic_metrics.sqlite",
  "table_name": "visits"
}
```

#### `query_sqlite`

Run a safe read-only SQLite query against a database inside the configured data directory.

Arguments:

```json
{
  "file_name": "clinic_metrics.sqlite",
  "sql": "SELECT clinic, SUM(appointments) AS total_appointments FROM visits GROUP BY clinic ORDER BY total_appointments DESC",
  "limit": 10
}
```

Example response shape:

```json
{
  "file_name": "clinic_metrics.sqlite",
  "columns": ["clinic", "total_appointments"],
  "rows": [
    {"clinic": "north", "total_appointments": 22}
  ],
  "row_count": 1,
  "limit_applied": 10
}
```

#### `summarize_correlations`

Rank the top absolute correlations among numeric columns.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv",
  "method": "pearson"
}
```

#### `detect_possible_target_leakage`

Return heuristic warnings about columns that may leak the target.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv",
  "target_column": "appointments_completed"
}
```

#### `validate_time_series_dataset_tool`

Validate whether a dataset looks ready for forecasting or time-series modeling.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv",
  "time_column": "date",
  "target_column": "appointments_completed",
  "group_column": "clinic_id"
}
```

#### `evaluate_baseline_model`

Evaluate a dummy baseline model for regression, binary classification, or multiclass classification.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv",
  "target_column": "appointments_completed",
  "task_type": "regression",
  "test_size": 0.2,
  "random_state": 42
}
```

### Prompt

#### `dataset_analysis_prompt`

Creates a reusable analysis prompt for a dataset.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv",
  "objective": "forecast clinic usage and staffing demand"
}
```

#### `modeling_report_review_prompt`

Creates a reusable review prompt for a saved modeling report.

Arguments:

```json
{
  "output_name": "clinic-usage-report.md",
  "focus": "decide whether the report is ready for stakeholder review"
}
```

Use `"latest"` for `output_name` to target the most recently modified saved modeling report.

---

## Test

```bash
poetry run pytest
```

Run static checks:

```bash
poetry run ruff check .
poetry run mypy
```

## Development Workflow

Local development uses the same quality gate as CI:

```bash
poetry run ruff check .
poetry run mypy
poetry run pytest
```

GitHub Actions runs those checks on pushes to `main` and `develop`, and on pull requests, across Python 3.11 and 3.12.

## Documentation Rule

README maintenance is part of the definition of done for this repository.

- Any user-facing capability change should update `README.md` in the same change.
- CLI, MCP tool, workflow, and setup documentation should stay aligned with the implemented repo state.
- We use the same rule as a default for other repositories unless there is a stronger repo-specific convention.

## Security

For local-only work, the default configuration keeps HTTP auth disabled.

If you set `MCP_API_KEY`, Streamable HTTP mode requires:

```text
Authorization: Bearer <your-key>
```

Limitations of this approach:

- it is a simple shared secret, not a full user or OAuth system;
- it does not apply to `stdio` transport;
- it should be paired with HTTPS and normal secret management if exposed beyond local development.

## Packaging and Release

Build local release artifacts with:

```bash
poetry build
```

This produces both a wheel and a source distribution in `dist/`.

GitHub Actions also includes a release workflow in `.github/workflows/release.yml`:

- `workflow_dispatch` builds artifacts for a manual release dry run.
- pushing a tag such as `v1.0.0` builds release artifacts from the tagged repository state.

This repository treats Git tags and GitHub releases as the primary release mechanism. Package indexes are optional and are not part of the core product workflow.

## Notebooks

The repository includes two walkthrough notebooks in `notebooks/`:

- `01_mcp_dataset_inspection.ipynb`: dataset discovery, preview, profiling, issue detection, and correlation inspection on the bundled sample CSV.
- `02_forecasting_readiness_workflow.ipynb`: synthetic healthcare dataset generation, time-series validation, leakage review, and baseline regression evaluation.

To run them locally, start Jupyter from the project environment:

```bash
poetry run jupyter notebook
```

If Jupyter is not installed in your Poetry environment yet, install it in that environment first with your preferred tool.

## Project Docs

- `CHANGELOG.md`: user-facing change history
- `CONTRIBUTING.md`: local development and PR expectations
- `SECURITY.md`: security reporting and hardening expectations
- `docs/API_CONTRACT.md`: versioned public MCP, CLI, and configuration contract
- `docs/SECURITY_MODEL.md`: trust boundaries, controls, and known security gaps
- `docs/DEPLOYMENT.md`: supported local, HTTP, Docker, and Compose deployment paths
- `docs/ARCHITECTURE.md`: component responsibilities and request flow
- `docs/RELEASE_CHECKLIST.md`: release prep checklist

---

## Docker

Build:

```bash
docker build -t ds-workspace-mcp .
```

Run:

```bash
docker run --rm -p 8000:8000 ds-workspace-mcp
```

Mount your own datasets:

```bash
docker run --rm \
  -p 8000:8000 \
  -v "$(pwd)/data:/app/data" \
  ds-workspace-mcp
```

Run with Docker Compose:

```bash
docker compose up --build
```

The Compose setup reads defaults from `.env.example`, overrides from `.env` when present, binds the server to `0.0.0.0`, publishes `MCP_PORT`, and mounts the local `data/` directory into the container at `/app/data`.

To inspect the running HTTP server with MCP Inspector:

```bash
npx -y @modelcontextprotocol/inspector
```

To stop the stack:

```bash
docker compose down
```

---

## Safety design

The server does not read arbitrary files.

All dataset paths are resolved inside `MCP_DATA_ROOT`, which defaults to `./data`. Path traversal attempts such as `../secret.csv` are rejected.

Only `.csv` files are supported in this first version.

DuckDB query safety notes:

- CSV files are resolved through the existing safe data-root checks before DuckDB sees any data.
- Queries must be a single `SELECT` or `WITH` statement against the temporary `dataset` table.
- Destructive or schema-changing SQL is rejected.
- External file-reading functions such as `read_csv(...)` are rejected.
- A final row limit is always applied, with `MCP_MAX_SQL_ROWS` acting as the upper bound.
- SQL text is bounded by `MCP_MAX_SQL_QUERY_LENGTH`.
- Best-effort interruption is attempted when execution exceeds `MCP_SQL_TIMEOUT_MS`.

SQLite safety notes:

- Only `.sqlite`, `.sqlite3`, and `.db` files inside `MCP_DATA_ROOT` are allowed.
- SQLite connections are opened in read-only mode.
- Schema-changing and destructive SQL is rejected.
- Query execution is limited to a single `SELECT` or `WITH` statement.
- A final row limit is always applied, with `MCP_MAX_SQL_ROWS` acting as the upper bound.
- SQL text is bounded by `MCP_MAX_SQL_QUERY_LENGTH`.
- Long-running queries are interrupted via SQLite progress handlers when they exceed `MCP_SQL_TIMEOUT_MS`.

Diagnostics notes:

- Correlation summaries are limited to numeric columns and return only the top ranked pairs.
- Leakage warnings are heuristic, not proof of leakage.
- Name overlap, strong numeric correlation, identifier-like columns, duplicate values, and datetime-like columns are treated as review signals.

Time-series validation notes:

- Timestamp parsing is conservative and fails if the declared time column cannot be parsed at all.
- The validator checks sorting, duplicate timestamps, inferred frequency, missing intervals, grouped gaps, and missing target values.
- History-length warnings are heuristic and intended for baseline forecasting readiness, not strict modeling requirements.

Baseline model notes:

- Only scikit-learn dummy baselines are used.
- `regression`, `binary_classification`, and `multiclass_classification` are supported.
- These metrics are reference baselines for comparison, not final model quality targets.

---

## Suggested portfolio positioning

> An MCP server that lets AI assistants safely inspect, profile, and reason over local analytical datasets.

This demonstrates AI engineering, data tooling, typed Python, MCP integration, and safe tool design.
