from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.sql.duckdb_engine import query_csv_with_duckdb_dataset


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


def test_query_csv_with_duckdb_dataset_rejects_destructive_statements(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_query_dataset(tmp_path)

    with pytest.raises(ValueError, match="Destructive"):
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

    with pytest.raises(ValueError, match="single SQL statement"):
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

    with pytest.raises(ValueError, match="outside"):
        query_csv_with_duckdb_dataset(
            file_name="../secret.csv",
            sql="SELECT * FROM dataset",
            limit=5,
        )
