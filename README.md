# Data Science Workspace MCP Server

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

Return row count, column count, dtypes, missing values, and missing percentages.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv"
}
```

#### `detect_csv_issues`

Detect simple data-quality issues, such as high missingness and likely identifier columns.

Arguments:

```json
{
  "file_name": "sample_clinic_usage.csv"
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

---

## Suggested portfolio positioning

> An MCP server that lets AI assistants safely inspect, profile, and reason over local analytical datasets.

This demonstrates AI engineering, data tooling, typed Python, MCP integration, and safe tool design.
