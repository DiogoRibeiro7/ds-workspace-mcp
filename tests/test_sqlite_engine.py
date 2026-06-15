from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ds_workspace_mcp.sql.sqlite_engine import (
    describe_sqlite_table,
    list_sqlite_files,
    list_sqlite_tables,
    query_sqlite_database,
)


def write_sqlite_database(root: Path, name: str = "sample.sqlite") -> Path:
    """Create a small SQLite database for tests."""

    path = root / name
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            CREATE TABLE visits (
                visit_id INTEGER PRIMARY KEY,
                clinic TEXT NOT NULL,
                appointments INTEGER,
                is_holiday INTEGER
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO visits (clinic, appointments, is_holiday)
            VALUES (?, ?, ?)
            """,
            [
                ("north", 10, 0),
                ("north", 12, 1),
                ("south", 6, 0),
            ],
        )
        connection.commit()
    finally:
        connection.close()
    return path


def test_list_sqlite_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_sqlite_database(tmp_path, "b.sqlite3")
    write_sqlite_database(tmp_path, "a.db")
    (tmp_path / "notes.txt").write_text("ignore me", encoding="utf-8")

    assert list_sqlite_files() == ["a.db", "b.sqlite3"]


def test_list_sqlite_tables(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_sqlite_database(tmp_path)

    assert list_sqlite_tables("sample.sqlite") == ["visits"]


def test_describe_sqlite_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_sqlite_database(tmp_path)

    schema = describe_sqlite_table("sample.sqlite", "visits")

    assert schema.table_name == "visits"
    assert schema.columns[0].name == "visit_id"
    assert schema.columns[0].is_primary_key is True


def test_query_sqlite_database_runs_valid_select(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_sqlite_database(tmp_path)

    result = query_sqlite_database(
        file_name="sample.sqlite",
        sql="""
            SELECT clinic, SUM(appointments) AS total_appointments
            FROM visits
            GROUP BY clinic
            ORDER BY clinic
        """,
        limit=10,
    )

    assert result.columns == ["clinic", "total_appointments"]
    assert result.row_count == 2
    assert result.rows[0]["clinic"] == "north"
    assert result.rows[0]["total_appointments"] == 22


def test_query_sqlite_database_rejects_destructive_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_sqlite_database(tmp_path)

    with pytest.raises(ValueError, match="Destructive"):
        query_sqlite_database(
            file_name="sample.sqlite",
            sql="DROP TABLE visits",
            limit=5,
        )


def test_query_sqlite_database_rejects_path_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_sqlite_database(tmp_path)

    with pytest.raises(ValueError, match="outside"):
        query_sqlite_database(
            file_name="../secret.sqlite",
            sql="SELECT * FROM visits",
            limit=5,
        )
