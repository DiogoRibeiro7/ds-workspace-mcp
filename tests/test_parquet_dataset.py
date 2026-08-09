from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from ds_workspace_mcp.core import (
    inspect_dataset,
    list_dataset_files,
    preview_dataset,
    profile_dataset,
)
from ds_workspace_mcp.datasets import (
    DatasetFormat,
    DatasetRef,
    DatasetRegistry,
    ParquetDatasetReader,
)
from ds_workspace_mcp.exceptions import DatasetReadError, PathTraversalError
from ds_workspace_mcp.sql.duckdb_engine import query_dataset_with_duckdb


def write_parquet_dataset(root: Path, name: str = "sample.parquet") -> Path:
    path = root / name
    with duckdb.connect(database=":memory:") as connection:
        connection.execute(
            """
            CREATE TABLE sample AS
            SELECT *
            FROM (
                VALUES
                    (1, 'north', DATE '2026-01-01', NULL),
                    (2, 'south', DATE '2026-01-02', 12.5),
                    (3, 'north', DATE '2026-01-03', 14.0)
            ) AS rows(id, clinic, visit_date, score)
            """
        )
        connection.execute("COPY sample TO ? (FORMAT PARQUET)", [str(path)])
    return path


def test_parquet_dataset_is_discovered_and_inspected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_parquet_dataset(tmp_path)

    metadata = inspect_dataset("sample.parquet")

    assert list_dataset_files() == ["sample.parquet"]
    assert metadata.file_name == "sample.parquet"
    assert metadata.format is DatasetFormat.PARQUET
    assert metadata.can_query is True
    assert metadata.row_count == 3
    assert metadata.column_count == 4
    assert [column.name for column in metadata.columns] == [
        "id",
        "clinic",
        "visit_date",
        "score",
    ]
    assert str(tmp_path) not in metadata.model_dump_json()


def test_parquet_preview_uses_bounded_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_parquet_dataset(tmp_path)

    preview = preview_dataset("sample.parquet", rows=2)

    assert preview.file_name == "sample.parquet"
    assert len(preview.rows) == 2
    assert preview.rows[0]["clinic"] == "north"


def test_parquet_profile_uses_generalized_dataset_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_parquet_dataset(tmp_path)

    profile = profile_dataset("sample.parquet")

    assert profile.file_name == "sample.parquet"
    assert profile.row_count == 3
    assert profile.column_count == 4
    assert "clinic" in profile.columns


def test_parquet_duckdb_query_uses_registered_dataset_relation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_parquet_dataset(tmp_path)

    result = query_dataset_with_duckdb(
        file_name="sample.parquet",
        sql="""
            SELECT clinic, COUNT(*) AS rows
            FROM dataset
            GROUP BY clinic
            ORDER BY clinic
        """,
        limit=10,
    )

    assert result.columns == ["clinic", "rows"]
    assert result.rows == [{"clinic": "north", "rows": 2}, {"clinic": "south", "rows": 1}]


def test_parquet_registry_rejects_traversal(tmp_path: Path) -> None:
    registry = DatasetRegistry(
        tmp_path,
        readers=(ParquetDatasetReader(),),
        max_dataset_bytes=1_000_000,
    )

    with pytest.raises(PathTraversalError, match="outside the configured data directory"):
        registry.resolve(DatasetRef("../sample.parquet"))


def test_parquet_reader_rejects_malformed_file(tmp_path: Path) -> None:
    malformed = tmp_path / "broken.parquet"
    malformed.write_text("not parquet", encoding="utf-8")
    reader = ParquetDatasetReader()

    with pytest.raises(DatasetReadError, match="Could not read dataset: broken.parquet"):
        reader.inspect(DatasetRef("broken.parquet"), malformed)
