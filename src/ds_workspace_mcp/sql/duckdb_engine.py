from __future__ import annotations

import logging
import math
import re
import threading
import time
from typing import cast

import duckdb
import pandas as pd
import sqlglot
from pydantic import BaseModel, Field
from sqlglot import exp
from sqlglot.errors import ParseError

from ds_workspace_mcp.config import get_settings
from ds_workspace_mcp.core import get_dataset_registry
from ds_workspace_mcp.datasets import DatasetFormat, DatasetRef
from ds_workspace_mcp.exceptions import InvalidSQLError, QueryTimeoutError
from ds_workspace_mcp.tracing import traced_operation

logger = logging.getLogger(__name__)

SAFE_DATASET_TABLE = "dataset"
ALLOWED_BASE_RELATIONS = frozenset({SAFE_DATASET_TABLE})
DESTRUCTIVE_SQL_PATTERN = re.compile(
    r"\b(drop|delete|update|insert|alter|create|copy|attach|install|load|export|call)\b",
    re.IGNORECASE,
)
EXTERNAL_ACCESS_PATTERN = re.compile(
    r"\b("
    r"read_blob|read_csv|read_csv_auto|read_json|read_json_auto|read_parquet|"
    r"read_text|glob|sniff_csv|parquet_scan|query|query_table|httpfs|read_xlsx"
    r")\b",
    re.IGNORECASE,
)
BLOCKED_TABLE_FUNCTIONS = frozenset(
    {
        "glob",
        "parquet_scan",
        "query",
        "query_table",
        "read_blob",
        "read_csv",
        "read_csv_auto",
        "read_json",
        "read_json_auto",
        "read_parquet",
        "read_text",
        "read_xlsx",
        "sniff_csv",
    }
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

    return query_dataset_with_duckdb(
        file_name=file_name,
        sql=sql,
        limit=limit,
        expected_format=DatasetFormat.CSV,
        unsupported_message="Only CSV files are supported.",
    )


def query_dataset_with_duckdb(
    file_name: str,
    sql: str,
    limit: int | None = None,
    *,
    expected_format: DatasetFormat | None = None,
    unsupported_message: str | None = None,
) -> DuckDBQueryResult:
    """Run a bounded read-only DuckDB query against a resolved dataset."""

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
    resolved = get_dataset_registry().resolve(
        DatasetRef(file_name=file_name),
        expected_format=expected_format,
        unsupported_message=unsupported_message,
    )
    df = resolved.reader.load_frame(resolved.ref, resolved.path)

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
                "sql.engine": "duckdb",
                "sql.limit": safe_limit,
                "sql.timeout_ms": settings.mcp_sql_timeout_ms,
            },
        ) as trace,
        duckdb.connect(database=":memory:") as connection,
    ):
        _configure_duckdb_security_policy(connection)
        connection.register(SAFE_DATASET_TABLE, df)
        query = f"SELECT * FROM ({normalized_sql}) AS safe_query LIMIT {safe_limit}"
        query_started_at = time.monotonic()
        try:
            result_frame = _execute_query_with_timeout(
                connection=connection,
                query=query,
                timeout_ms=settings.mcp_sql_timeout_ms,
            )
        except QueryTimeoutError:
            trace.set_attribute("sql.cancelled", True)
            trace.set_attribute("sql.elapsed_ms", _elapsed_ms(query_started_at))
            raise
        trace.set_attribute("sql.cancelled", False)
        trace.set_attribute("sql.elapsed_ms", _elapsed_ms(query_started_at))
        trace.set_attribute("sql.result_row_count", len(result_frame))

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
        "Completed DuckDB query for file_name=%s result_rows=%s columns=%s timeout_ms=%s",
        file_name,
        result.row_count,
        len(result.columns),
        settings.mcp_sql_timeout_ms,
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

    if not normalized_sql:
        raise InvalidSQLError("sql must be a non-empty string.")

    if len(normalized_sql) > max_sql_query_length:
        logger.warning("Rejected DuckDB query because it exceeded the configured length limit.")
        raise InvalidSQLError(f"sql must not exceed {max_sql_query_length} characters.")

    statements = _parse_single_statement(normalized_sql)
    if len(statements) != 1:
        logger.warning("Rejected DuckDB query because multiple statements were detected.")
        raise InvalidSQLError("Only a single SQL statement is allowed.")
    parsed = statements[0]
    normalized_sql = parsed.sql(dialect="duckdb")

    if DESTRUCTIVE_SQL_PATTERN.search(normalized_sql):
        logger.warning("Rejected DuckDB query because it contained blocked SQL keywords.")
        raise InvalidSQLError("Destructive or schema-changing SQL is not allowed.")

    if not isinstance(parsed, exp.Select):
        logger.warning("Rejected DuckDB query because it was not a SELECT or WITH statement.")
        raise InvalidSQLError("Only SELECT and WITH queries are allowed.")

    if EXTERNAL_ACCESS_PATTERN.search(normalized_sql):
        logger.warning("Rejected DuckDB query because it attempted external data access.")
        raise InvalidSQLError("SQL cannot access external files or DuckDB scanning functions.")

    _validate_relation_access(parsed, allowed_relations=ALLOWED_BASE_RELATIONS)

    return normalized_sql


def _parse_single_statement(sql: str) -> list[exp.Expression]:
    """Parse a DuckDB SQL string into one or more statements."""

    try:
        statements = sqlglot.parse(sql, read="duckdb")
    except ParseError as exc:
        logger.warning("Rejected DuckDB query because parsing failed.")
        raise InvalidSQLError("SQL query could not be parsed.") from exc

    return cast(
        list[exp.Expression], [statement for statement in statements if statement is not None]
    )


def _validate_relation_access(
    statement: exp.Expression,
    allowed_relations: frozenset[str],
) -> None:
    """Ensure a parsed statement references only explicitly allowed base relations."""

    cte_names = {
        _normalize_identifier(cte.alias)
        for cte in statement.find_all(exp.CTE)
        if _normalize_identifier(cte.alias)
    }
    if cte_names & allowed_relations:
        logger.warning("Rejected DuckDB query because a CTE shadowed an allowed relation.")
        raise InvalidSQLError("SQL cannot shadow the allowed in-memory relation `dataset`.")

    permitted_references = allowed_relations | cte_names
    referenced_allowed_relation = False

    for function in statement.find_all(exp.Func):
        function_name = _normalize_identifier(function.sql_name())
        if function_name in BLOCKED_TABLE_FUNCTIONS:
            logger.warning("Rejected DuckDB query because it used a blocked table function.")
            raise InvalidSQLError("SQL cannot access external files or DuckDB scanning functions.")

    for table in statement.find_all(exp.Table):
        if table.catalog or table.db:
            logger.warning("Rejected DuckDB query because it used a qualified table reference.")
            raise InvalidSQLError("SQL may only reference explicitly allowed in-memory relations.")

        table_name = _normalize_identifier(table.name)
        if not table_name:
            logger.warning("Rejected DuckDB query because it used a table-valued function.")
            raise InvalidSQLError("SQL may only reference explicitly allowed in-memory relations.")

        if table_name not in permitted_references:
            logger.warning("Rejected DuckDB query because it referenced a disallowed relation.")
            raise InvalidSQLError("SQL may only reference explicitly allowed in-memory relations.")

        if table_name in allowed_relations and table_name not in cte_names:
            referenced_allowed_relation = True

    if not referenced_allowed_relation:
        logger.warning("Rejected DuckDB query because it did not reference an allowed relation.")
        raise InvalidSQLError("Queries must reference the allowed in-memory relation `dataset`.")


def _normalize_identifier(identifier: str) -> str:
    """Normalize SQL identifiers for allowlist checks."""

    return identifier.strip().strip('"').lower()


def _configure_duckdb_security_policy(connection: duckdb.DuckDBPyConnection) -> None:
    """Apply DuckDB's built-in read-only and external-access restrictions."""

    security_statements = (
        "SET enable_external_access=false",
        "SET autoinstall_known_extensions=false",
        "SET autoload_known_extensions=false",
        "SET allow_community_extensions=false",
        "SET allow_persistent_secrets=false",
        "SET lock_configuration=true",
    )
    for statement in security_statements:
        connection.execute(statement)


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
    started_at = time.monotonic()

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
        elapsed_ms = _elapsed_ms(started_at)
        logger.warning(
            "Interrupted DuckDB query timeout_ms=%s elapsed_ms=%s cancelled=true",
            timeout_ms,
            elapsed_ms,
        )
        connection.interrupt()
        worker.join(timeout=min(max(timeout_ms / 1000, 0.1), 1.0))
        if worker.is_alive():
            logger.error(
                "DuckDB worker did not stop promptly after cancellation timeout_ms=%s "
                "elapsed_ms=%s",
                timeout_ms,
                _elapsed_ms(started_at),
            )
        raise QueryTimeoutError(f"SQL query exceeded the timeout of {timeout_ms} ms.")

    worker.join()
    if captured_error is not None:
        raise captured_error
    if result_frame is None:
        raise RuntimeError("DuckDB query finished without a result frame.")
    logger.debug(
        "DuckDB query completed timeout_ms=%s elapsed_ms=%s result_rows=%s cancelled=false",
        timeout_ms,
        _elapsed_ms(started_at),
        len(result_frame),
    )
    return result_frame


def _elapsed_ms(started_at: float) -> int:
    """Return elapsed monotonic time in milliseconds."""

    return int((time.monotonic() - started_at) * 1000)
