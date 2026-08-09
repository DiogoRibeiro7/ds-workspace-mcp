from __future__ import annotations

import logging
import math
import re
import threading
from typing import cast

import duckdb
import pandas as pd
from pydantic import BaseModel, Field

from ds_workspace_mcp.config import get_settings
from ds_workspace_mcp.core import read_csv_dataset
from ds_workspace_mcp.exceptions import InvalidSQLError, QueryTimeoutError
from ds_workspace_mcp.tracing import traced_operation

logger = logging.getLogger(__name__)

SAFE_DATASET_TABLE = "dataset"
DESTRUCTIVE_SQL_PATTERN = re.compile(
    r"\b(drop|delete|update|insert|alter|create|copy|attach|install|load|export|call)\b",
    re.IGNORECASE,
)
EXTERNAL_ACCESS_PATTERN = re.compile(
    r"\b(read_csv|read_parquet|parquet_scan|glob|httpfs|read_json|read_xlsx|read_text)\b",
    re.IGNORECASE,
)


class DuckDBQueryResult(BaseModel):
    """Structured result for a safe DuckDB query."""

    file_name: str
    columns: list[str]
    rows: list[dict[str, object]]
    row_count: int = Field(ge=0)
    limit_applied: int = Field(ge=1)


def query_csv_with_duckdb_dataset(
    file_name: str,
    sql: str,
    limit: int | None = None,
) -> DuckDBQueryResult:
    """Run a bounded read-only DuckDB query against a resolved CSV dataset."""

    if not isinstance(sql, str):
        logger.warning("Rejected DuckDB query because sql was not a string.")
        raise InvalidSQLError("sql must be a string.")

    if not sql.strip():
        logger.warning("Rejected DuckDB query because sql was empty.")
        raise InvalidSQLError("sql must be a non-empty string.")

    settings = get_settings()
    safe_limit = _resolve_limit(limit=limit, max_sql_rows=settings.mcp_max_sql_rows)
    normalized_sql = _validate_and_normalize_sql(
        sql,
        max_sql_query_length=settings.mcp_max_sql_query_length,
    )
    df = read_csv_dataset(file_name=file_name)

    logger.info(
        "Executing DuckDB query for file_name=%s requested_limit=%s applied_limit=%s",
        file_name,
        limit,
        safe_limit,
    )

    with (
        traced_operation(
            "sql.duckdb.query",
            {
                "dataset.file_name": file_name,
                "sql.limit": safe_limit,
            },
        ),
        duckdb.connect(database=":memory:") as connection,
    ):
        connection.register(SAFE_DATASET_TABLE, df)
        query = f"SELECT * FROM ({normalized_sql}) AS safe_query LIMIT {safe_limit}"
        result_frame = _execute_query_with_timeout(
            connection=connection,
            query=query,
            timeout_ms=settings.mcp_sql_timeout_ms,
        )

    records = cast(list[dict[str, object]], result_frame.astype(object).to_dict(orient="records"))
    clean_rows = [
        {column: _normalize_scalar(value) for column, value in row.items()} for row in records
    ]

    result = DuckDBQueryResult(
        file_name=file_name,
        columns=[str(column) for column in result_frame.columns],
        rows=clean_rows,
        row_count=len(clean_rows),
        limit_applied=safe_limit,
    )
    logger.info(
        "Completed DuckDB query for file_name=%s result_rows=%s columns=%s",
        file_name,
        result.row_count,
        len(result.columns),
    )
    return result


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
    """Validate query safety and return a normalized single statement."""

    normalized_sql = sql.strip()
    while normalized_sql.endswith(";"):
        normalized_sql = normalized_sql[:-1].rstrip()

    if not normalized_sql:
        raise InvalidSQLError("sql must be a non-empty string.")

    if len(normalized_sql) > max_sql_query_length:
        logger.warning("Rejected DuckDB query because it exceeded the configured length limit.")
        raise InvalidSQLError(f"sql must not exceed {max_sql_query_length} characters.")

    if ";" in normalized_sql:
        logger.warning("Rejected DuckDB query because multiple statements were detected.")
        raise InvalidSQLError("Only a single SQL statement is allowed.")

    if DESTRUCTIVE_SQL_PATTERN.search(normalized_sql):
        logger.warning("Rejected DuckDB query because it contained blocked SQL keywords.")
        raise InvalidSQLError("Destructive or schema-changing SQL is not allowed.")

    if not normalized_sql.lower().startswith(("select", "with")):
        logger.warning("Rejected DuckDB query because it was not a SELECT or WITH statement.")
        raise InvalidSQLError("Only SELECT and WITH queries are allowed.")

    if EXTERNAL_ACCESS_PATTERN.search(normalized_sql):
        logger.warning("Rejected DuckDB query because it attempted external data access.")
        raise InvalidSQLError("SQL cannot access external files or DuckDB scanning functions.")

    if SAFE_DATASET_TABLE.lower() not in normalized_sql.lower():
        logger.warning("Rejected DuckDB query because it did not reference the dataset table.")
        raise InvalidSQLError("Queries must reference the dataset table named `dataset`.")

    return normalized_sql


def _normalize_scalar(value: object) -> object:
    """Convert dataframe scalars into JSON-friendly values."""

    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "isoformat"):
        try:
            return cast(object, value.isoformat())
        except TypeError:
            return value
    return value


def _execute_query_with_timeout(
    connection: duckdb.DuckDBPyConnection,
    query: str,
    timeout_ms: int,
) -> pd.DataFrame:
    """Execute a DuckDB query with best-effort interruption on timeout."""

    result_frame: pd.DataFrame | None = None
    captured_error: BaseException | None = None
    completed = threading.Event()

    def run_query() -> None:
        nonlocal result_frame, captured_error
        try:
            result_frame = connection.execute(query).fetch_df()
        except BaseException as exc:  # pragma: no cover - exercised via timeout behavior
            captured_error = exc
        finally:
            completed.set()

    worker = threading.Thread(target=run_query, daemon=True)
    worker.start()

    if not completed.wait(timeout_ms / 1000):
        logger.warning("Interrupted DuckDB query after timeout_ms=%s", timeout_ms)
        connection.interrupt()
        worker.join(timeout=1.0)
        raise QueryTimeoutError(f"SQL query exceeded the timeout of {timeout_ms} ms.")

    worker.join()
    if captured_error is not None:
        raise captured_error
    if result_frame is None:
        raise RuntimeError("DuckDB query finished without a result frame.")
    return result_frame
