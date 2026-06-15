from __future__ import annotations

import logging
import math
import re
import sqlite3
from pathlib import Path

from pydantic import BaseModel, Field

from ds_workspace_mcp.config import get_settings
from ds_workspace_mcp.core import get_data_root
from ds_workspace_mcp.exceptions import (
    DatasetNotFoundError,
    InvalidDatasetNameError,
    InvalidSQLError,
    PathTraversalError,
    UnsupportedFileTypeError,
)
from ds_workspace_mcp.tracing import traced_operation

logger = logging.getLogger(__name__)

SQLITE_SUFFIXES = {".sqlite", ".sqlite3", ".db"}
DESTRUCTIVE_SQL_PATTERN = re.compile(
    r"\b(drop|delete|update|insert|alter|create|attach|detach|pragma|vacuum|replace|reindex)\b",
    re.IGNORECASE,
)


class SQLiteDatabaseInfo(BaseModel):
    """Basic metadata for an available SQLite database."""

    file_name: str


class SQLiteColumnInfo(BaseModel):
    """Schema description for a SQLite column."""

    cid: int = Field(ge=0)
    name: str
    data_type: str
    not_null: bool
    default_value: str | None
    is_primary_key: bool


class SQLiteTableSchema(BaseModel):
    """Schema description for a SQLite table."""

    file_name: str
    table_name: str
    columns: list[SQLiteColumnInfo]


class SQLiteQueryResult(BaseModel):
    """Structured result for a safe SQLite query."""

    file_name: str
    columns: list[str]
    rows: list[dict[str, object]]
    row_count: int = Field(ge=0)
    limit_applied: int = Field(ge=1)


def list_sqlite_files() -> list[str]:
    """List SQLite database files in the configured data root."""

    data_root = get_data_root()
    files = sorted(
        path.name
        for path in data_root.iterdir()
        if path.is_file() and path.suffix.lower() in SQLITE_SUFFIXES
    )
    logger.info("Listed %s SQLite databases from configured data root", len(files))
    return files


def resolve_sqlite_path(file_name: str) -> Path:
    """Resolve a SQLite file path safely inside the configured data root."""

    if not isinstance(file_name, str):
        logger.warning("Rejected SQLite path resolution because file_name was not a string.")
        raise InvalidDatasetNameError("file_name must be a string.")

    if not file_name.strip():
        logger.warning("Rejected SQLite path resolution because file_name was empty.")
        raise InvalidDatasetNameError("file_name must be a non-empty string.")

    data_root = get_data_root()
    path = (data_root / file_name).resolve()

    if path != data_root and data_root not in path.parents:
        logger.warning("Rejected SQLite path outside data root for file_name=%s", file_name)
        raise PathTraversalError("Access outside the configured data directory is not allowed.")

    if path.suffix.lower() not in SQLITE_SUFFIXES:
        logger.warning("Rejected non-SQLite file for file_name=%s", file_name)
        raise UnsupportedFileTypeError("Only SQLite files are supported.")

    if not path.exists():
        logger.warning("SQLite database not found for file_name=%s", file_name)
        raise DatasetNotFoundError(f"Database not found: {file_name}")

    logger.info("Resolved SQLite database path for file_name=%s", file_name)
    return path


def list_sqlite_tables(file_name: str) -> list[str]:
    """List user tables from a SQLite database."""

    path = resolve_sqlite_path(file_name)
    with _connect_read_only(path) as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

    tables = [str(row[0]) for row in rows]
    logger.info("Listed %s SQLite tables for file_name=%s", len(tables), file_name)
    return tables


def describe_sqlite_table(file_name: str, table_name: str) -> SQLiteTableSchema:
    """Describe a SQLite table using PRAGMA table_info."""

    if not isinstance(table_name, str):
        raise InvalidDatasetNameError("table_name must be a string.")
    if not table_name.strip():
        raise InvalidDatasetNameError("table_name must be a non-empty string.")

    path = resolve_sqlite_path(file_name)
    validated_table_name = _validate_table_name(file_name, table_name)
    quoted_table_name = _quote_identifier(validated_table_name)

    with _connect_read_only(path) as connection:
        rows = connection.execute(f"PRAGMA table_info({quoted_table_name})").fetchall()

    columns = [
        SQLiteColumnInfo(
            cid=int(row[0]),
            name=str(row[1]),
            data_type=str(row[2]),
            not_null=bool(row[3]),
            default_value=None if row[4] is None else str(row[4]),
            is_primary_key=bool(row[5]),
        )
        for row in rows
    ]
    logger.info(
        "Described SQLite table file_name=%s table_name=%s columns=%s",
        file_name,
        validated_table_name,
        len(columns),
    )
    return SQLiteTableSchema(
        file_name=file_name,
        table_name=validated_table_name,
        columns=columns,
    )


def query_sqlite_database(
    file_name: str,
    sql: str,
    limit: int | None = None,
) -> SQLiteQueryResult:
    """Run a bounded read-only SQLite query against a resolved database."""

    if not isinstance(sql, str):
        logger.warning("Rejected SQLite query because sql was not a string.")
        raise TypeError("sql must be a string.")

    if not sql.strip():
        logger.warning("Rejected SQLite query because sql was empty.")
        raise ValueError("sql must be a non-empty string.")

    settings = get_settings()
    safe_limit = _resolve_limit(limit=limit, max_sql_rows=settings.mcp_max_sql_rows)
    normalized_sql = _validate_and_normalize_sql(
        sql,
        max_sql_query_length=settings.mcp_max_sql_query_length,
    )
    path = resolve_sqlite_path(file_name)

    logger.info(
        "Executing SQLite query for file_name=%s requested_limit=%s applied_limit=%s",
        file_name,
        limit,
        safe_limit,
    )

    with (
        traced_operation(
            "sql.sqlite.query",
            {
                "dataset.file_name": file_name,
                "sql.limit": safe_limit,
            },
        ),
        _connect_read_only(path) as connection,
    ):
        cursor = connection.execute(
            f"SELECT * FROM ({normalized_sql}) AS safe_query LIMIT ?",
            (safe_limit,),
        )
        rows = cursor.fetchall()
        columns = [str(description[0]) for description in cursor.description or []]

    clean_rows = [
        {column: _normalize_scalar(value) for column, value in zip(columns, row, strict=True)}
        for row in rows
    ]

    result = SQLiteQueryResult(
        file_name=file_name,
        columns=columns,
        rows=clean_rows,
        row_count=len(clean_rows),
        limit_applied=safe_limit,
    )
    logger.info(
        "Completed SQLite query for file_name=%s result_rows=%s columns=%s",
        file_name,
        result.row_count,
        len(result.columns),
    )
    return result


def _connect_read_only(path: Path) -> sqlite3.Connection:
    """Open a SQLite database in read-only mode."""

    uri = f"file:{path.as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _validate_table_name(file_name: str, table_name: str) -> str:
    """Ensure the requested table exists in the database."""

    available_tables = list_sqlite_tables(file_name)
    if table_name not in available_tables:
        raise ValueError(f"Unknown table: {table_name}")
    return table_name


def _quote_identifier(identifier: str) -> str:
    """Safely quote a SQLite identifier."""

    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def _resolve_limit(limit: int | None, max_sql_rows: int) -> int:
    """Validate and normalize the requested row limit."""

    if limit is None:
        return max_sql_rows
    if not isinstance(limit, int):
        raise InvalidSQLError("limit must be an integer.")
    if limit < 1 or limit > max_sql_rows:
        raise InvalidSQLError(f"limit must be between 1 and {max_sql_rows}.")
    return limit


def _validate_and_normalize_sql(sql: str, max_sql_query_length: int) -> str:
    """Validate SQLite query safety and return a normalized statement."""

    normalized_sql = sql.strip()
    while normalized_sql.endswith(";"):
        normalized_sql = normalized_sql[:-1].rstrip()

    if not normalized_sql:
        raise InvalidSQLError("sql must be a non-empty string.")

    if len(normalized_sql) > max_sql_query_length:
        logger.warning("Rejected SQLite query because it exceeded the configured length limit.")
        raise InvalidSQLError(
            f"sql must not exceed {max_sql_query_length} characters."
        )

    if ";" in normalized_sql:
        logger.warning("Rejected SQLite query because multiple statements were detected.")
        raise InvalidSQLError("Only a single SQL statement is allowed.")

    if DESTRUCTIVE_SQL_PATTERN.search(normalized_sql):
        logger.warning("Rejected SQLite query because it contained blocked SQL keywords.")
        raise InvalidSQLError("Destructive or schema-changing SQL is not allowed.")

    if not normalized_sql.lower().startswith(("select", "with")):
        logger.warning("Rejected SQLite query because it was not a SELECT or WITH statement.")
        raise InvalidSQLError("Only SELECT and WITH queries are allowed.")

    return normalized_sql


def _normalize_scalar(value: object) -> object:
    """Convert SQLite scalars into JSON-friendly values."""

    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value
