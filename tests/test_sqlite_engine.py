from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, cast

import pytest

from ds_workspace_mcp.exceptions import InvalidSQLError, PathTraversalError, QueryTimeoutError
from ds_workspace_mcp.sql.sqlite_engine import (
    _execute_query_with_timeout,
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

    with pytest.raises(InvalidSQLError, match="Destructive"):
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

    with pytest.raises(PathTraversalError, match="outside"):
        query_sqlite_database(
            file_name="../secret.sqlite",
            sql="SELECT * FROM visits",
            limit=5,
        )


def test_query_sqlite_database_rejects_overlong_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_MAX_SQL_QUERY_LENGTH", "100")
    write_sqlite_database(tmp_path)
    sql_values = ", ".join(f"'{index}'" for index in range(30))
    sql = f"SELECT * FROM visits WHERE clinic IN ({sql_values})"

    with pytest.raises(InvalidSQLError, match="must not exceed 100 characters"):
        query_sqlite_database(
            file_name="sample.sqlite",
            sql=sql,
            limit=5,
        )


def test_execute_query_with_timeout_interrupts_sqlite_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeCursor:
        description = (("value", None, None, None, None, None, None),)

        def fetchall(self) -> list[tuple[int]]:
            return [(1,)]

    class FakeConnection:
        def __init__(self) -> None:
            self.progress_handler: Any = None

        def set_progress_handler(self, handler: Any, instructions: int) -> None:
            self.progress_handler = handler

        def execute(self, query: str, parameters: tuple[object, ...]) -> sqlite3.Cursor:
            assert self.progress_handler is not None
            if self.progress_handler() == 1:
                raise sqlite3.OperationalError("interrupted")
            return cast(sqlite3.Cursor, FakeCursor())

    monotonic_values = iter([0.0, 0.0, 1.0, 1.0])
    monkeypatch.setattr(
        "ds_workspace_mcp.sql.sqlite_engine.time.monotonic",
        lambda: next(monotonic_values),
    )

    with pytest.raises(QueryTimeoutError, match="timeout of 100 ms"):
        _execute_query_with_timeout(
            connection=cast(Any, FakeConnection()),
            query="SELECT 1",
            parameters=(),
            timeout_ms=100,
        )


def test_execute_query_with_timeout_keeps_sqlite_timeout_active_during_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeCursor:
        description = (("value", None, None, None, None, None, None),)

        def __init__(self, connection: FakeConnection) -> None:
            self.connection = connection

        def fetchall(self) -> list[tuple[int]]:
            assert self.connection.progress_handler is not None
            if self.connection.progress_handler() == 1:
                raise sqlite3.OperationalError("interrupted")
            return [(1,)]

    class FakeConnection:
        def __init__(self) -> None:
            self.progress_handler: Any = None
            self.cleared = False

        def set_progress_handler(self, handler: Any, instructions: int) -> None:
            self.progress_handler = handler
            if handler is None and instructions == 0:
                self.cleared = True

        def execute(self, query: str, parameters: tuple[object, ...]) -> sqlite3.Cursor:
            return cast(sqlite3.Cursor, FakeCursor(self))

    monotonic_values = iter([0.0, 0.0, 1.0, 1.0])
    monkeypatch.setattr(
        "ds_workspace_mcp.sql.sqlite_engine.time.monotonic",
        lambda: next(monotonic_values),
    )
    connection = FakeConnection()

    with pytest.raises(QueryTimeoutError, match="timeout of 100 ms"):
        _execute_query_with_timeout(
            connection=cast(Any, connection),
            query="SELECT 1",
            parameters=(),
            timeout_ms=100,
        )

    assert connection.cleared is True
