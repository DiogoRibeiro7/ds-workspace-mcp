from __future__ import annotations

import logging

from ds_workspace_mcp.mcp.app import _mcp_tool
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
from ds_workspace_mcp.tracing import traced_operation

logger = logging.getLogger(__name__)


@_mcp_tool()
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


@_mcp_tool()
def list_sqlite_databases_tool() -> list[SQLiteDatabaseInfo]:
    """Return SQLite database files available in the configured data directory."""

    with traced_operation("tool.list_sqlite_databases", {"tool.name": "list_sqlite_databases"}):
        logger.info("Tool list_sqlite_databases_tool invoked")
        return [SQLiteDatabaseInfo(file_name=file_name) for file_name in list_sqlite_files()]


@_mcp_tool()
def list_sqlite_tables(file_name: str) -> list[str]:
    """List user tables from a SQLite database."""

    with traced_operation(
        "tool.list_sqlite_tables",
        {"tool.name": "list_sqlite_tables", "dataset.file_name": file_name},
    ):
        logger.info("Tool list_sqlite_tables invoked file_name=%s", file_name)
        return list_sqlite_tables_dataset(file_name=file_name)


@_mcp_tool()
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


@_mcp_tool()
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
