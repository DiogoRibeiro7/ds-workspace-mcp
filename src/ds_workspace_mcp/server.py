from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from ds_workspace_mcp.config import Settings, Transport, get_settings
from ds_workspace_mcp.core import (
    DatasetIssue,
    DatasetPreview,
    detect_csv_dataset_issues,
    list_csv_files,
    preview_csv_dataset,
    profile_csv_dataset,
)
from ds_workspace_mcp.diagnostics import (
    CorrelationSummary,
    LeakageSummary,
    detect_possible_target_leakage_dataset,
    summarize_correlations_dataset,
)
from ds_workspace_mcp.logging_config import configure_logging
from ds_workspace_mcp.profiling import DatasetProfile
from ds_workspace_mcp.sql.duckdb_engine import DuckDBQueryResult, query_csv_with_duckdb_dataset
from ds_workspace_mcp.sql.sqlite_engine import (
    SQLiteDatabaseInfo,
    SQLiteQueryResult,
    SQLiteTableSchema,
    list_sqlite_files,
    query_sqlite_database,
)
from ds_workspace_mcp.sql.sqlite_engine import (
    describe_sqlite_table as describe_sqlite_table_dataset,
)
from ds_workspace_mcp.sql.sqlite_engine import (
    list_sqlite_tables as list_sqlite_tables_dataset,
)

logger = logging.getLogger(__name__)


def create_mcp(settings: Settings) -> FastMCP:
    """Create the MCP server with validated runtime settings."""

    return FastMCP(
        "Data Science Workspace MCP",
        json_response=True,
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level=settings.mcp_log_level,
    )


mcp = create_mcp(get_settings())


@mcp.resource("datasets://catalog")
def list_datasets() -> str:
    """
    List CSV datasets available to the assistant.

    Resources are useful for exposing data without side effects.
    """

    files = list_csv_files()
    logger.info("Resource request datasets://catalog returned %s files", len(files))

    if not files:
        return "No CSV datasets found in the configured data directory."

    return "\n".join(files)


@mcp.resource("databases://sqlite")
def list_sqlite_databases() -> str:
    """List SQLite databases available to the assistant."""

    files = list_sqlite_files()
    logger.info("Resource request databases://sqlite returned %s files", len(files))

    if not files:
        return "No SQLite databases found in the configured data directory."

    return "\n".join(files)


@mcp.tool()
def preview_csv(file_name: str, rows: int = 5) -> DatasetPreview:
    """
    Preview the first rows of a CSV dataset.

    Args:
        file_name: CSV file name inside the configured data directory.
        rows: Number of rows to return. Must be between 1 and 50.

    Returns:
        A structured preview of the dataset.
    """

    logger.info("Tool preview_csv invoked file_name=%s rows=%s", file_name, rows)
    return preview_csv_dataset(file_name=file_name, rows=rows)


@mcp.tool()
def profile_csv(file_name: str) -> DatasetProfile:
    """
    Profile a CSV dataset.

    Args:
        file_name: CSV file name inside the configured data directory.

    Returns:
        Dataset shape, column names, dtypes, and missing-value statistics.
    """

    logger.info("Tool profile_csv invoked file_name=%s", file_name)
    return profile_csv_dataset(file_name=file_name)


@mcp.tool()
def detect_csv_issues(file_name: str) -> list[DatasetIssue]:
    """
    Detect simple data-quality issues in a CSV dataset.

    This tool is intentionally conservative and does not modify the dataset.

    Args:
        file_name: CSV file name inside the configured data directory.

    Returns:
        A list of detected data-quality issues.
    """

    logger.info("Tool detect_csv_issues invoked file_name=%s", file_name)
    return detect_csv_dataset_issues(file_name=file_name)


@mcp.tool()
def query_csv_with_duckdb(
    file_name: str,
    sql: str,
    limit: int | None = None,
) -> DuckDBQueryResult:
    """
    Run a safe read-only DuckDB query against a CSV dataset.

    Args:
        file_name: CSV file name inside the configured data directory.
        sql: A single SELECT or WITH query against the `dataset` table.
        limit: Optional maximum number of rows to return.

    Returns:
        Structured query results with bounded rows and column names.
    """

    logger.info(
        "Tool query_csv_with_duckdb invoked file_name=%s limit=%s",
        file_name,
        limit,
    )
    return query_csv_with_duckdb_dataset(file_name=file_name, sql=sql, limit=limit)


@mcp.tool()
def list_sqlite_databases_tool() -> list[SQLiteDatabaseInfo]:
    """Return SQLite database files available in the configured data directory."""

    logger.info("Tool list_sqlite_databases_tool invoked")
    return [SQLiteDatabaseInfo(file_name=file_name) for file_name in list_sqlite_files()]


@mcp.tool()
def list_sqlite_tables(file_name: str) -> list[str]:
    """List user tables from a SQLite database."""

    logger.info("Tool list_sqlite_tables invoked file_name=%s", file_name)
    return list_sqlite_tables_dataset(file_name=file_name)


@mcp.tool()
def describe_sqlite_table(file_name: str, table_name: str) -> SQLiteTableSchema:
    """Describe a SQLite table schema."""

    logger.info(
        "Tool describe_sqlite_table invoked file_name=%s table_name=%s",
        file_name,
        table_name,
    )
    return describe_sqlite_table_dataset(file_name=file_name, table_name=table_name)


@mcp.tool()
def query_sqlite(
    file_name: str,
    sql: str,
    limit: int | None = None,
) -> SQLiteQueryResult:
    """Run a safe read-only SQLite query against a database in the data directory."""

    logger.info("Tool query_sqlite invoked file_name=%s limit=%s", file_name, limit)
    return query_sqlite_database(file_name=file_name, sql=sql, limit=limit)


@mcp.tool()
def summarize_correlations(file_name: str, method: str = "pearson") -> CorrelationSummary:
    """Summarize the top absolute correlations among numeric columns."""

    logger.info(
        "Tool summarize_correlations invoked file_name=%s method=%s",
        file_name,
        method,
    )
    return summarize_correlations_dataset(file_name=file_name, method=method)


@mcp.tool()
def detect_possible_target_leakage(file_name: str, target_column: str) -> LeakageSummary:
    """Return heuristic warnings about possible target leakage."""

    logger.info(
        "Tool detect_possible_target_leakage invoked file_name=%s target_column=%s",
        file_name,
        target_column,
    )
    return detect_possible_target_leakage_dataset(
        file_name=file_name,
        target_column=target_column,
    )


@mcp.prompt()
def dataset_analysis_prompt(file_name: str, objective: str = "exploratory analysis") -> str:
    """
    Create a reusable analysis prompt for a dataset.

    Args:
        file_name: Dataset file name.
        objective: Analysis objective.

    Returns:
        A prompt that an MCP-compatible assistant can use.
    """

    logger.info(
        "Prompt dataset_analysis_prompt created file_name=%s objective_length=%s",
        file_name,
        len(objective),
    )
    return f"""
You are analysing the dataset `{file_name}`.

Objective:
{objective}

Start by:
1. Inspecting the dataset schema.
2. Checking missing values and suspicious columns.
3. Suggesting useful target variables.
4. Proposing baseline statistical and machine learning approaches.
5. Explaining risks, assumptions, and validation strategy.

Keep the analysis practical and reproducible.
""".strip()


def get_transport() -> Transport:
    """
    Read and validate the MCP transport from the environment.

    Returns:
        Either `stdio` or `streamable-http`.
    """

    return get_settings().mcp_transport


def main() -> None:
    """Run the MCP server."""

    settings = get_settings()
    configure_logging(settings)
    logger.info(
        "Starting MCP server transport=%s host=%s port=%s",
        settings.mcp_transport,
        settings.mcp_host,
        settings.mcp_port,
    )
    mcp.run(transport=get_transport())


if __name__ == "__main__":
    main()
