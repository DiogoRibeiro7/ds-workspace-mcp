from __future__ import annotations

from pathlib import Path

import pytest

from ds_workspace_mcp.core import inspect_dataset, preview_csv_dataset
from ds_workspace_mcp.exceptions import DatasetReadError


@pytest.mark.parametrize("raw_content", [b"", b"\n\n", b"  \n"])
def test_empty_csv_has_explicit_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw_content: bytes
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    (tmp_path / "empty.csv").write_bytes(raw_content)

    with pytest.raises(DatasetReadError, match="empty CSV or missing header"):
        preview_csv_dataset("empty.csv")


def test_csv_with_header_but_no_data_is_valid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    (tmp_path / "header-only.csv").write_text("clinic,visits\n", encoding="utf-8")

    assert preview_csv_dataset("header-only.csv").rows == []
    assert inspect_dataset("header-only.csv").column_count == 2


def test_csv_utf8_bom_is_supported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    (tmp_path / "bom.csv").write_bytes(b"\xef\xbb\xbfclinic,visits\nnorth,3\n")

    assert preview_csv_dataset("bom.csv").rows == [{"clinic": "north", "visits": 3}]
    assert [column.name for column in inspect_dataset("bom.csv").columns] == ["clinic", "visits"]


@pytest.mark.parametrize(
    "raw_content",
    [
        b"clinic,visits\nnorth,\xe9\n",  # Latin-1 byte in an otherwise UTF-8 CSV.
        b"clinic,visits\nnorth,1\nsouth,\xff\n",  # Mixed decodable and invalid lines.
        b"\xff\xfeclinic,visits\n",  # UTF-16-like invalid byte prefix.
    ],
)
def test_csv_mixed_or_invalid_encodings_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw_content: bytes
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    (tmp_path / "mixed.csv").write_bytes(raw_content)

    with pytest.raises(DatasetReadError, match="invalid or mixed UTF-8 encoding"):
        preview_csv_dataset("mixed.csv", rows=10)


@pytest.mark.parametrize(
    "content",
    [
        'clinic,visits\n"north,3\nsouth,4\n',  # Unterminated quoted field.
        "clinic,visits\nnorth,3,extra\n",  # Excess values are not an implicit index.
        "clinic,visits\nnorth,3\nsouth,4,extra\n",  # Inconsistent field counts.
    ],
)
def test_malformed_csv_does_not_drop_columns_or_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    (tmp_path / "malformed.csv").write_text(content, encoding="utf-8")

    with pytest.raises(DatasetReadError, match="malformed CSV"):
        preview_csv_dataset("malformed.csv", rows=10)
