from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.core import list_csv_files, preview_csv_dataset
from ds_workspace_mcp.exceptions import DatasetExportError, InvalidSQLError
from ds_workspace_mcp.sql.csv_export import export_query_result_to_csv_dataset


def _write_source(root: Path) -> None:
    pd.DataFrame({"clinic": ["north", "north", "south"], "visits": [2, 3, 5]}).to_csv(
        root / "source.csv", index=False
    )


def test_export_is_disabled_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    _write_source(tmp_path)

    with pytest.raises(DatasetExportError, match="MCP_QUERY_EXPORT_ENABLED"):
        export_query_result_to_csv_dataset("source.csv", "SELECT * FROM dataset", "output.csv")
    assert not (tmp_path / "output.csv").exists()


def test_export_writes_bounded_csv_and_exposes_no_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_QUERY_EXPORT_ENABLED", "true")
    _write_source(tmp_path)

    result = export_query_result_to_csv_dataset(
        "source.csv",
        "SELECT clinic, SUM(visits) AS total FROM dataset GROUP BY clinic ORDER BY clinic",
        "totals.csv",
        limit=2,
    )

    assert result.row_count == 2
    assert result.column_count == 2
    assert result.limit_applied == 2
    assert result.bytes_written == (tmp_path / "totals.csv").stat().st_size
    assert str(tmp_path) not in result.model_dump_json()
    assert list_csv_files() == ["source.csv", "totals.csv"]
    assert preview_csv_dataset("totals.csv", rows=2).rows == [
        {"clinic": "north", "total": 5},
        {"clinic": "south", "total": 5},
    ]
    assert not list(tmp_path.glob(".ds-workspace-export-*.tmp"))


@pytest.mark.parametrize(
    "output_name",
    [
        "../outside.csv",
        "nested/output.csv",
        r"nested\output.csv",
        "/tmp/secret.csv",
        ".hidden.csv",
        "output.json",
        "workbook.xlsx#Sheet1",
        "",
        3,
    ],
)
def test_export_rejects_unsafe_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output_name: str
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_QUERY_EXPORT_ENABLED", "true")
    _write_source(tmp_path)

    with pytest.raises(DatasetExportError, match="output_name"):
        export_query_result_to_csv_dataset("source.csv", "SELECT * FROM dataset", output_name)


def test_export_never_overwrites_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_QUERY_EXPORT_ENABLED", "true")
    _write_source(tmp_path)
    (tmp_path / "out.csv").write_text("original", encoding="utf-8")

    with pytest.raises(DatasetExportError, match="already exists"):
        export_query_result_to_csv_dataset("source.csv", "SELECT * FROM dataset", "out.csv")

    assert (tmp_path / "out.csv").read_text(encoding="utf-8") == "original"


def test_export_rejects_unsafe_sql_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_QUERY_EXPORT_ENABLED", "true")
    _write_source(tmp_path)

    with pytest.raises(InvalidSQLError, match="Destructive"):
        export_query_result_to_csv_dataset("source.csv", "DELETE FROM dataset", "out.csv")
    assert not (tmp_path / "out.csv").exists()


def test_export_enforces_rows_columns_and_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_QUERY_EXPORT_ENABLED", "true")
    monkeypatch.setenv("MCP_MAX_EXPORT_ROWS", "2")
    monkeypatch.setenv("MCP_MAX_EXPORT_COLUMNS", "1")
    monkeypatch.setenv("MCP_MAX_EXPORT_BYTES", "5")
    _write_source(tmp_path)

    with pytest.raises(DatasetExportError, match="MCP_MAX_EXPORT_ROWS"):
        export_query_result_to_csv_dataset(
            "source.csv", "SELECT * FROM dataset", "too-many-rows.csv", limit=3
        )
    with pytest.raises(DatasetExportError, match="MCP_MAX_EXPORT_COLUMNS"):
        export_query_result_to_csv_dataset(
            "source.csv", "SELECT * FROM dataset", "too-many-columns.csv"
        )
    with pytest.raises(DatasetExportError, match="MCP_MAX_EXPORT_BYTES"):
        export_query_result_to_csv_dataset(
            "source.csv", "SELECT clinic FROM dataset", "too-many-bytes.csv"
        )
    assert list_csv_files() == ["source.csv"]


def test_export_rejects_concurrent_write_collisions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_QUERY_EXPORT_ENABLED", "true")
    _write_source(tmp_path)

    def export_once(_: int) -> bool:
        try:
            export_query_result_to_csv_dataset(
                "source.csv", "SELECT clinic FROM dataset", "shared.csv"
            )
        except DatasetExportError as exc:
            assert "already exists" in str(exc)
            return False
        return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(export_once, range(2)))

    assert outcomes.count(True) == 1
    assert outcomes.count(False) == 1
    assert not list(tmp_path.glob(".ds-workspace-export-*.tmp"))
