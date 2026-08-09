from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.core import (
    inspect_dataset,
    list_dataset_files,
    list_excel_sheets,
    preview_dataset,
)
from ds_workspace_mcp.datasets import DatasetFormat
from ds_workspace_mcp.exceptions import DatasetReadError, UnsupportedFileTypeError


def test_json_records_are_loaded_explicitly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    (tmp_path / "records.json").write_text(
        '[{"id": 1, "clinic": "north"}, {"id": 2, "clinic": "south"}]',
        encoding="utf-8",
    )

    metadata = inspect_dataset("records.json")
    preview = preview_dataset("records.json", rows=1)

    assert list_dataset_files() == ["records.json"]
    assert metadata.format is DatasetFormat.JSON
    assert metadata.row_count == 2
    assert metadata.format_metadata == {"structure": "records"}
    assert preview.rows == [{"id": 1, "clinic": "north"}]


def test_ndjson_records_are_loaded_explicitly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    (tmp_path / "records.ndjson").write_text(
        '{"id": 1, "clinic": "north"}\n{"id": 2, "clinic": "south"}\n',
        encoding="utf-8",
    )

    metadata = inspect_dataset("records.ndjson")

    assert metadata.format is DatasetFormat.JSON
    assert metadata.row_count == 2
    assert metadata.format_metadata == {"structure": "ndjson"}


def test_json_reader_rejects_nested_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    (tmp_path / "nested.json").write_text(
        '[{"id": 1, "details": {"clinic": "north"}}]',
        encoding="utf-8",
    )

    with pytest.raises(DatasetReadError, match="Nested JSON values are not supported"):
        inspect_dataset("nested.json")


def test_json_reader_rejects_ambiguous_top_level_structure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    (tmp_path / "object.json").write_text('{"id": 1}', encoding="utf-8")

    with pytest.raises(DatasetReadError, match="array of records"):
        inspect_dataset("object.json")


def test_excel_sheet_listing_and_explicit_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    workbook = tmp_path / "workbook.xlsx"
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        pd.DataFrame({"id": [1], "clinic": ["north"]}).to_excel(
            writer,
            sheet_name="North",
            index=False,
        )
        pd.DataFrame({"id": [2], "clinic": ["south"]}).to_excel(
            writer,
            sheet_name="South",
            index=False,
        )

    assert list_excel_sheets("workbook.xlsx") == ["North", "South"]
    with pytest.raises(DatasetReadError, match="sheet selection is ambiguous"):
        inspect_dataset("workbook.xlsx")

    metadata = inspect_dataset("workbook.xlsx#South")
    preview = preview_dataset("workbook.xlsx#South", rows=1)

    assert metadata.format is DatasetFormat.EXCEL
    assert metadata.format_metadata["sheet_name"] == "South"
    assert preview.rows == [{"id": 2, "clinic": "south"}]


def test_excel_rejects_missing_sheet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    workbook = tmp_path / "workbook.xlsx"
    pd.DataFrame({"id": [1]}).to_excel(workbook, sheet_name="Only", index=False)

    with pytest.raises(DatasetReadError, match="Excel sheet not found: Missing"):
        preview_dataset("workbook.xlsx#Missing", rows=1)


def test_excel_rejects_unsupported_extension(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    (tmp_path / "legacy.xls").write_text("not supported", encoding="utf-8")

    with pytest.raises(UnsupportedFileTypeError, match="Unsupported dataset format: .xls"):
        inspect_dataset("legacy.xls")


def test_excel_rejects_malformed_workbook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    (tmp_path / "broken.xlsx").write_text("not a workbook", encoding="utf-8")

    with pytest.raises(DatasetReadError, match="Could not read dataset: broken.xlsx"):
        list_excel_sheets("broken.xlsx")
