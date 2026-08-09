from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, cast

import pandas as pd
import pytest

from ds_workspace_mcp.exceptions import InvalidSQLError, PathTraversalError, QueryTimeoutError
from ds_workspace_mcp.sql.duckdb_engine import (
    _execute_query_with_timeout,
    _validate_and_normalize_sql,
    query_csv_with_duckdb_dataset,
)


def write_query_dataset(root: Path, name: str = "query.csv") -> Path:
    """Create a dataset that exercises DuckDB queries."""

    path = root / name
    df = pd.DataFrame(
        {
            "clinic": ["north", "north", "south", "south"],
            "appointments": [10, 12, 6, 9],
            "is_holiday": [False, True, False, False],
        }
    )
    df.to_csv(path, index=False)
    return path


def test_query_csv_with_duckdb_dataset_runs_valid_aggregate_query(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_query_dataset(tmp_path)

    result = query_csv_with_duckdb_dataset(
        file_name="query.csv",
        sql="""
            SELECT clinic, SUM(appointments) AS total_appointments
            FROM dataset
            GROUP BY clinic
            ORDER BY clinic
        """,
        limit=10,
    )

    assert result.columns == ["clinic", "total_appointments"]
    assert result.row_count == 2
    assert result.rows[0]["clinic"] == "north"
    assert result.rows[0]["total_appointments"] == 22


def test_query_csv_with_duckdb_dataset_enforces_row_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_MAX_SQL_ROWS", "2")
    write_query_dataset(tmp_path)

    result = query_csv_with_duckdb_dataset(
        file_name="query.csv",
        sql="SELECT clinic, appointments FROM dataset ORDER BY appointments DESC",
    )

    assert result.limit_applied == 2
    assert result.row_count == 2


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT clinic FROM dataset WHERE appointments > 8 ORDER BY clinic",
        "SELECT clinic, appointments FROM dataset ORDER BY appointments DESC",
        """
        SELECT clinic, SUM(appointments) AS total
        FROM dataset
        GROUP BY clinic
        ORDER BY total DESC
        """,
        """
        WITH clinic_totals AS (
            SELECT clinic, SUM(appointments) AS total
            FROM dataset
            GROUP BY clinic
        )
        SELECT clinic, total
        FROM clinic_totals
        ORDER BY clinic
        """,
        """
        WITH base AS (
            WITH filtered AS (
                SELECT * FROM dataset WHERE appointments > 6
            )
            SELECT clinic, appointments FROM filtered
        )
        SELECT clinic, appointments
        FROM base
        ORDER BY appointments
        """,
        """
        SELECT
            clinic,
            appointments,
            ROW_NUMBER() OVER (PARTITION BY clinic ORDER BY appointments) AS clinic_rank
        FROM dataset
        ORDER BY clinic, clinic_rank
        """,
        """
        SELECT left_dataset.clinic, right_dataset.appointments
        FROM dataset AS left_dataset
        JOIN dataset AS right_dataset
            ON left_dataset.clinic = right_dataset.clinic
        ORDER BY left_dataset.clinic, right_dataset.appointments
        """,
        'SELECT "clinic", "appointments" FROM "dataset" ORDER BY "appointments"',
    ],
)
def test_query_csv_with_duckdb_dataset_allows_safe_analytical_patterns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sql: str,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_query_dataset(tmp_path)

    result = query_csv_with_duckdb_dataset(
        file_name="query.csv",
        sql=sql,
        limit=10,
    )

    assert result.row_count > 0


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM read_blob('secret.bin')",
        "SELECT * FROM read_csv('secret.csv')",
        "SELECT * FROM read_csv_auto('secret.csv')",
        "SELECT * FROM read_json('secret.json')",
        "SELECT * FROM read_json_auto('secret.json')",
        "SELECT * FROM read_parquet('secret.parquet')",
        "SELECT * FROM parquet_scan('secret.parquet')",
        "SELECT * FROM read_text('secret.txt')",
        "SELECT * FROM glob('*.csv')",
        "SELECT * FROM sniff_csv('secret.csv')",
        "SELECT * FROM query('main', 'SELECT * FROM secret')",
        "SELECT * FROM query_table('secret')",
        "ATTACH 'secret.db' AS secret",
        "COPY dataset TO 'secret.csv'",
        "INSTALL httpfs",
        "LOAD httpfs",
        "SELECT * FROM read_csv('https://example.com/secret.csv')",
        "SELECT * FROM read_csv('http://example.com/secret.csv')",
        "SELECT * FROM read_csv('file:///etc/passwd')",
        "SELECT * FROM read_csv('C:/Users/diogo/secret.csv')",
        "SELECT * FROM read_csv('../secret.csv')",
        "SELECT * FROM 'C:/Users/diogo/secret.csv'",
        "SELECT * FROM '../secret.csv'",
    ],
)
def test_query_csv_with_duckdb_dataset_rejects_external_access_attempts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sql: str,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_query_dataset(tmp_path)

    with pytest.raises(InvalidSQLError, match="not allowed|allowed|external|SELECT"):
        query_csv_with_duckdb_dataset(
            file_name="query.csv",
            sql=sql,
            limit=5,
        )


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 'dataset' AS mentioned_only",
        "-- dataset\nSELECT * FROM secret_table",
        "SELECT * FROM read_csv('secret.csv') AS dataset",
        """
        WITH dataset AS (
            SELECT * FROM secret_table
        )
        SELECT * FROM dataset
        """,
        """
        WITH dataset AS (
            SELECT 1 AS value
        )
        SELECT * FROM dataset
        """,
    ],
)
def test_query_csv_with_duckdb_dataset_rejects_dataset_name_bypass_attempts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sql: str,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_query_dataset(tmp_path)

    with pytest.raises(InvalidSQLError, match="allowed|external|dataset"):
        query_csv_with_duckdb_dataset(
            file_name="query.csv",
            sql=sql,
            limit=5,
        )


def test_validate_and_normalize_sql_allows_semicolons_inside_literals() -> None:
    normalized_sql = _validate_and_normalize_sql(
        "SELECT 'dataset; still literal' AS value FROM dataset",
        max_sql_query_length=200,
    )

    assert "still literal" in normalized_sql


def test_query_csv_with_duckdb_dataset_rejects_destructive_statements(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_query_dataset(tmp_path)

    with pytest.raises(InvalidSQLError, match="Destructive"):
        query_csv_with_duckdb_dataset(
            file_name="query.csv",
            sql="DELETE FROM dataset WHERE appointments > 10",
            limit=5,
        )


def test_query_csv_with_duckdb_dataset_rejects_multiple_statements(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_query_dataset(tmp_path)

    with pytest.raises(InvalidSQLError, match="single SQL statement"):
        query_csv_with_duckdb_dataset(
            file_name="query.csv",
            sql="SELECT * FROM dataset; SELECT * FROM dataset",
            limit=5,
        )


def test_query_csv_with_duckdb_dataset_rejects_path_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_query_dataset(tmp_path)

    with pytest.raises(PathTraversalError, match="outside"):
        query_csv_with_duckdb_dataset(
            file_name="../secret.csv",
            sql="SELECT * FROM dataset",
            limit=5,
        )


def test_query_csv_with_duckdb_dataset_rejects_overlong_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_MAX_SQL_QUERY_LENGTH", "100")
    write_query_dataset(tmp_path)
    sql_values = ", ".join(f"'{index}'" for index in range(30))
    sql = f"SELECT * FROM dataset WHERE clinic IN ({sql_values})"

    with pytest.raises(InvalidSQLError, match="must not exceed 100 characters"):
        query_csv_with_duckdb_dataset(
            file_name="query.csv",
            sql=sql,
            limit=5,
        )


def test_execute_query_with_timeout_interrupts_duckdb_connection() -> None:
    class FakeCursor:
        def fetch_df(self) -> pd.DataFrame:
            return pd.DataFrame([{"value": 1}])

    class FakeConnection:
        def __init__(self) -> None:
            self.released = threading.Event()
            self.interrupted = False

        def execute(self, query: str) -> FakeCursor:
            self.released.wait(timeout=1.0)
            if self.interrupted:
                raise RuntimeError("interrupted")
            return FakeCursor()

        def interrupt(self) -> None:
            self.interrupted = True
            self.released.set()

    with pytest.raises(QueryTimeoutError, match="timeout of 100 ms"):
        _execute_query_with_timeout(
            connection=cast(Any, FakeConnection()),
            query="SELECT 1",
            timeout_ms=100,
        )
