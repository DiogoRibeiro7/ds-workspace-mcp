# Data Science Workspace MCP Server

![CI](https://github.com/DiogoRibeiro7/ds-workspace-mcp/actions/workflows/ci.yml/badge.svg)

A small but practical **Model Context Protocol (MCP)** server for data science workflows.

It lets an MCP-compatible assistant safely inspect local CSV datasets through:

- **Resources** for dataset discovery.
- **Tools** for CSV preview, profiling, and simple data-quality checks.
- **Prompts** for reusable dataset analysis instructions.

This project is designed as a clean portfolio-ready starter repo. It is intentionally focused, typed, tested, and safe by default.

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
│   └── sample_clinic_usage.csv
├── src/
│   └── ds_workspace_mcp/
│       ├── __init__.py
│       ├── core.py
│       └── server.py
├── tests/
│   └── test_core.py
├── .env.example
├── .gitignore
├── AGENTS.md
├── Dockerfile
├── README.md
├── ROADMAP.md
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
- `MCP_MAX_CATEGORICAL_VALUES`: maximum top-value examples returned per categorical column in `profile_csv`. Defaults to `5`.
- `MCP_PROFILE_CACHE_ENABLED`: enable or disable in-memory profile caching. Defaults to `true`.
- `MCP_PROFILE_CACHE_MAX_ENTRIES`: maximum cached profile entries. Defaults to `128`.
- `MCP_LOG_LEVEL`: server log level. Defaults to `INFO`.

Example:

```bash
MCP_DATA_ROOT=./data
MCP_TRANSPORT=streamable-http
MCP_HOST=127.0.0.1
MCP_PORT=8000
MCP_MAX_PREVIEW_ROWS=50
MCP_MAX_SQL_ROWS=1000
MCP_MAX_CATEGORICAL_VALUES=5
MCP_PROFILE_CACHE_ENABLED=true
MCP_PROFILE_CACHE_MAX_ENTRIES=128
MCP_LOG_LEVEL=INFO
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

### Tools

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

Example response shape:

```json
{
  "file_name": "sample_clinic_usage.csv",
  "columns": ["clinic_id", "avg_completed"],
  "rows": [
    {"clinic_id": "north", "avg_completed": 82.5}
  ],
  "row_count": 1,
  "limit_applied": 10
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

SQLite safety notes:

- Only `.sqlite`, `.sqlite3`, and `.db` files inside `MCP_DATA_ROOT` are allowed.
- SQLite connections are opened in read-only mode.
- Schema-changing and destructive SQL is rejected.
- Query execution is limited to a single `SELECT` or `WITH` statement.
- A final row limit is always applied, with `MCP_MAX_SQL_ROWS` acting as the upper bound.

---

## Suggested portfolio positioning

> An MCP server that lets AI assistants safely inspect, profile, and reason over local analytical datasets.

This demonstrates AI engineering, data tooling, typed Python, MCP integration, and safe tool design.
