from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.sql.duckdb_engine import (
    DuckDBQueryResult,
    query_cache,
    query_dataset_with_duckdb,
)
from ds_workspace_mcp.sql.query_cache import QueryCache, QueryCacheKey


def _write_dataset(path: Path, values: list[int]) -> None:
    """Persist a dataset that can change between identical SQL requests."""

    pd.DataFrame({"value": values}).to_csv(path, index=False)


def _key(path: Path, *, row_limit: int = 10) -> QueryCacheKey:
    return QueryCacheKey(
        path=path,
        file_name=path.name,
        file_size=10,
        modified_time_ns=1,
        normalized_sql="SELECT value FROM dataset",
        row_limit=row_limit,
    )


def _result() -> DuckDBQueryResult:
    return DuckDBQueryResult(
        file_name="sample.csv",
        columns=["value"],
        rows=[{"value": 1}],
        row_count=1,
        limit_applied=10,
    )


def test_query_cache_reuses_normalized_equivalent_sql(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    _write_dataset(tmp_path / "sample.csv", [1, 2, 3])

    first = query_dataset_with_duckdb("sample.csv", "SELECT value FROM dataset", limit=2)
    second = query_dataset_with_duckdb("sample.csv", " SELECT   value  FROM dataset; ", limit=2)

    assert first.rows == second.rows
    assert query_cache.stats().hits == 1
    assert query_cache.stats().misses == 1
    assert query_cache.stats().current_entries == 1


def test_query_cache_invalidates_on_fingerprint_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    path = tmp_path / "sample.csv"
    _write_dataset(path, [1, 2])
    first = query_dataset_with_duckdb("sample.csv", "SELECT SUM(value) AS total FROM dataset")

    _write_dataset(path, [10, 20, 30])
    second = query_dataset_with_duckdb("sample.csv", "SELECT SUM(value) AS total FROM dataset")

    assert first.rows == [{"total": 3.0}]
    assert second.rows == [{"total": 60.0}]
    assert query_cache.stats().misses == 2


def test_query_cache_includes_row_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    _write_dataset(tmp_path / "sample.csv", [1, 2, 3])
    sql = "SELECT value FROM dataset ORDER BY value"

    short = query_dataset_with_duckdb("sample.csv", sql, limit=1)
    long = query_dataset_with_duckdb("sample.csv", sql, limit=3)

    assert short.row_count == 1
    assert long.row_count == 3
    assert query_cache.stats().misses == 2


def test_query_cache_separates_excel_sheet_selectors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    with pd.ExcelWriter(tmp_path / "workbook.xlsx", engine="openpyxl") as writer:
        pd.DataFrame({"value": [11]}).to_excel(writer, sheet_name="North", index=False)
        pd.DataFrame({"value": [22]}).to_excel(writer, sheet_name="South", index=False)

    north = query_dataset_with_duckdb("workbook.xlsx#North", "SELECT value FROM dataset")
    south = query_dataset_with_duckdb("workbook.xlsx#South", "SELECT value FROM dataset")

    assert north.rows == [{"value": 11}]
    assert south.rows == [{"value": 22}]
    assert query_cache.stats().misses == 2


def test_query_cache_can_be_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_QUERY_CACHE_ENABLED", "false")
    _write_dataset(tmp_path / "sample.csv", [1])

    for _ in range(2):
        query_dataset_with_duckdb("sample.csv", "SELECT value FROM dataset")

    assert query_cache.stats().hits == 0
    assert query_cache.stats().misses == 2
    assert query_cache.stats().current_entries == 0


def test_query_cache_lru_and_defensive_copies(tmp_path: Path) -> None:
    cache: QueryCache[DuckDBQueryResult] = QueryCache(max_entries=2)
    first_key = _key(tmp_path / "first.csv")
    second_key = _key(tmp_path / "second.csv")
    third_key = _key(tmp_path / "third.csv")
    original = _result()
    cache.set(first_key, original)
    original.rows[0]["value"] = 999

    cached = cache.get(first_key)
    assert cached is not None
    assert cached.rows[0]["value"] == 1
    cached.rows[0]["value"] = -1
    assert cache.get(first_key).rows[0]["value"] == 1  # type: ignore[union-attr]

    cache.set(second_key, _result())
    cache.set(third_key, _result())
    assert cache.get(first_key) is None
    assert cache.stats().evictions == 1
    assert str(tmp_path) not in repr(cache.stats())


def test_query_cache_trims_entries_and_rejects_invalid_configuration(tmp_path: Path) -> None:
    cache: QueryCache[DuckDBQueryResult] = QueryCache(max_entries=3)
    for index in range(3):
        cache.set(_key(tmp_path / f"{index}.csv"), _result())

    cache.configure(enabled=True, max_entries=1)
    assert len(cache) == 1
    assert cache.stats().evictions == 2
    cache.configure(enabled=False, max_entries=1)
    assert len(cache) == 0

    with pytest.raises(ValueError, match="positive integer"):
        cache.configure(enabled=True, max_entries=0)
    with pytest.raises(TypeError, match="boolean"):
        cache.configure(enabled=1, max_entries=1)  # type: ignore[arg-type]


def test_query_cache_invalidates_on_modified_time_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    path = tmp_path / "sample.csv"
    _write_dataset(path, [1, 2])
    query_dataset_with_duckdb("sample.csv", "SELECT value FROM dataset")
    old_stat = path.stat()
    os.utime(path, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns + 1_000_000_000))
    query_dataset_with_duckdb("sample.csv", "SELECT value FROM dataset")

    assert query_cache.stats().misses == 2
