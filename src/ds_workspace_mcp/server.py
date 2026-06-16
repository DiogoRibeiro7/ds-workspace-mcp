from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from ds_workspace_mcp.auth import build_http_auth
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
from ds_workspace_mcp.ml.baselines import (
    BaselineEvaluationResult,
    evaluate_baseline_model_dataset,
)
from ds_workspace_mcp.overview import DatasetOverview, summarize_dataset_overview
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
from ds_workspace_mcp.targeting import (
    TargetSuggestionResult,
    suggest_target_columns_dataset,
)
from ds_workspace_mcp.timeseries import TimeSeriesValidationResult, validate_time_series_dataset
from ds_workspace_mcp.tracing import configure_tracing, traced_operation

logger = logging.getLogger(__name__)


def create_mcp(settings: Settings) -> FastMCP:
    """Create the MCP server with validated runtime settings."""

    auth_settings, token_verifier = build_http_auth(settings)
    return FastMCP(
        "Data Science Workspace MCP",
        json_response=True,
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level=settings.mcp_log_level,
        auth=auth_settings,
        token_verifier=token_verifier,
    )


mcp = create_mcp(get_settings())


@mcp.resource("datasets://catalog")
def list_datasets() -> str:
    """
    List CSV datasets available to the assistant.

    Resources are useful for exposing data without side effects.
    """

    with traced_operation("resource.list_datasets"):
        files = list_csv_files()
        logger.info("Resource request datasets://catalog returned %s files", len(files))

        if not files:
            return "No CSV datasets found in the configured data directory."

        return "\n".join(files)


@mcp.resource("databases://sqlite")
def list_sqlite_databases() -> str:
    """List SQLite databases available to the assistant."""

    with traced_operation("resource.list_sqlite_databases"):
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

    with traced_operation(
        "tool.preview_csv",
        {"tool.name": "preview_csv", "dataset.file_name": file_name, "tool.rows": rows},
    ):
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

    with traced_operation(
        "tool.profile_csv",
        {"tool.name": "profile_csv", "dataset.file_name": file_name},
    ):
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

    with traced_operation(
        "tool.detect_csv_issues",
        {"tool.name": "detect_csv_issues", "dataset.file_name": file_name},
    ):
        logger.info("Tool detect_csv_issues invoked file_name=%s", file_name)
        return detect_csv_dataset_issues(file_name=file_name)


@mcp.tool()
def summarize_dataset(file_name: str) -> DatasetOverview:
    """
    Return a compact first-pass overview of a CSV dataset.

    Args:
        file_name: CSV file name inside the configured data directory.

    Returns:
        A concise overview with dataset shape, issue highlights, correlations, and next steps.
    """

    with traced_operation(
        "tool.summarize_dataset",
        {"tool.name": "summarize_dataset", "dataset.file_name": file_name},
    ):
        logger.info("Tool summarize_dataset invoked file_name=%s", file_name)
        return summarize_dataset_overview(file_name=file_name)


@mcp.tool()
def suggest_target_columns(file_name: str) -> TargetSuggestionResult:
    """
    Suggest plausible target columns for modeling.

    Args:
        file_name: CSV file name inside the configured data directory.

    Returns:
        Ranked target candidates with suggested task types and reasoning.
    """

    with traced_operation(
        "tool.suggest_target_columns",
        {"tool.name": "suggest_target_columns", "dataset.file_name": file_name},
    ):
        logger.info("Tool suggest_target_columns invoked file_name=%s", file_name)
        return suggest_target_columns_dataset(file_name=file_name)


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

    with traced_operation(
        "tool.query_csv_with_duckdb",
        {"tool.name": "query_csv_with_duckdb", "dataset.file_name": file_name, "tool.limit": limit},
    ):
        logger.info(
            "Tool query_csv_with_duckdb invoked file_name=%s limit=%s",
            file_name,
            limit,
        )
        return query_csv_with_duckdb_dataset(file_name=file_name, sql=sql, limit=limit)


@mcp.tool()
def list_sqlite_databases_tool() -> list[SQLiteDatabaseInfo]:
    """Return SQLite database files available in the configured data directory."""

    with traced_operation("tool.list_sqlite_databases", {"tool.name": "list_sqlite_databases"}):
        logger.info("Tool list_sqlite_databases_tool invoked")
        return [SQLiteDatabaseInfo(file_name=file_name) for file_name in list_sqlite_files()]


@mcp.tool()
def list_sqlite_tables(file_name: str) -> list[str]:
    """List user tables from a SQLite database."""

    with traced_operation(
        "tool.list_sqlite_tables",
        {"tool.name": "list_sqlite_tables", "dataset.file_name": file_name},
    ):
        logger.info("Tool list_sqlite_tables invoked file_name=%s", file_name)
        return list_sqlite_tables_dataset(file_name=file_name)


@mcp.tool()
def describe_sqlite_table(file_name: str, table_name: str) -> SQLiteTableSchema:
    """Describe a SQLite table schema."""

    with traced_operation(
        "tool.describe_sqlite_table",
        {
            "tool.name": "describe_sqlite_table",
            "dataset.file_name": file_name,
            "sqlite.table_name": table_name,
        },
    ):
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

    with traced_operation(
        "tool.query_sqlite",
        {"tool.name": "query_sqlite", "dataset.file_name": file_name, "tool.limit": limit},
    ):
        logger.info("Tool query_sqlite invoked file_name=%s limit=%s", file_name, limit)
        return query_sqlite_database(file_name=file_name, sql=sql, limit=limit)


@mcp.tool()
def summarize_correlations(file_name: str, method: str = "pearson") -> CorrelationSummary:
    """Summarize the top absolute correlations among numeric columns."""

    with traced_operation(
        "tool.summarize_correlations",
        {
            "tool.name": "summarize_correlations",
            "dataset.file_name": file_name,
            "tool.method": method,
        },
    ):
        logger.info(
            "Tool summarize_correlations invoked file_name=%s method=%s",
            file_name,
            method,
        )
        return summarize_correlations_dataset(file_name=file_name, method=method)


@mcp.tool()
def detect_possible_target_leakage(file_name: str, target_column: str) -> LeakageSummary:
    """Return heuristic warnings about possible target leakage."""

    with traced_operation(
        "tool.detect_possible_target_leakage",
        {
            "tool.name": "detect_possible_target_leakage",
            "dataset.file_name": file_name,
            "tool.target_column": target_column,
        },
    ):
        logger.info(
            "Tool detect_possible_target_leakage invoked file_name=%s target_column=%s",
            file_name,
            target_column,
        )
        return detect_possible_target_leakage_dataset(
            file_name=file_name,
            target_column=target_column,
        )


@mcp.tool()
def validate_time_series_dataset_tool(
    file_name: str,
    time_column: str,
    target_column: str | None = None,
    group_column: str | None = None,
) -> TimeSeriesValidationResult:
    """Validate whether a dataset looks suitable for time-series modeling."""

    with traced_operation(
        "tool.validate_time_series_dataset",
        {
            "tool.name": "validate_time_series_dataset",
            "dataset.file_name": file_name,
            "tool.time_column": time_column,
            "tool.target_column": target_column,
            "tool.group_column": group_column,
        },
    ):
        logger.info(
            "Tool validate_time_series_dataset_tool invoked "
            "file_name=%s time_column=%s target_column=%s group_column=%s",
            file_name,
            time_column,
            target_column,
            group_column,
        )
        return validate_time_series_dataset(
            file_name=file_name,
            time_column=time_column,
            target_column=target_column,
            group_column=group_column,
        )


@mcp.tool()
def evaluate_baseline_model(
    file_name: str,
    target_column: str,
    task_type: str,
    test_size: float = 0.2,
    random_state: int = 42,
) -> BaselineEvaluationResult:
    """Evaluate a dummy baseline model for a supervised learning task."""

    with traced_operation(
        "tool.evaluate_baseline_model",
        {
            "tool.name": "evaluate_baseline_model",
            "dataset.file_name": file_name,
            "tool.target_column": target_column,
            "tool.task_type": task_type,
        },
    ):
        logger.info(
            "Tool evaluate_baseline_model invoked file_name=%s target_column=%s task_type=%s",
            file_name,
            target_column,
            task_type,
        )
        return evaluate_baseline_model_dataset(
            file_name=file_name,
            target_column=target_column,
            task_type=task_type,
            test_size=test_size,
            random_state=random_state,
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

    with traced_operation(
        "prompt.dataset_analysis_prompt",
        {
            "prompt.name": "dataset_analysis_prompt",
            "dataset.file_name": file_name,
            "prompt.objective_length": len(objective),
        },
    ):
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
    configure_tracing(settings)
    logger.info(
        "Starting MCP server transport=%s host=%s port=%s auth_enabled=%s",
        settings.mcp_transport,
        settings.mcp_host,
        settings.mcp_port,
        settings.mcp_transport == "streamable-http" and settings.mcp_api_key is not None,
    )
    mcp.run(transport=get_transport())


if __name__ == "__main__":
    main()
