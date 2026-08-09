from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.core import list_csv_files, read_csv_dataset, resolve_dataset_path
from ds_workspace_mcp.datasets import (
    CsvDatasetReader,
    DatasetFingerprint,
    DatasetFormat,
    DatasetMetadata,
    DatasetRef,
    DatasetRegistry,
)
from ds_workspace_mcp.exceptions import PathTraversalError, UnsupportedFileTypeError


class JsonDatasetReader:
    format: DatasetFormat = DatasetFormat.JSON
    extensions: tuple[str, ...] = (".json",)
    can_query: bool = False

    def load_frame(self, path: Path, *, nrows: int | None = None) -> pd.DataFrame:
        frame = pd.read_json(path)
        return frame.head(nrows) if nrows is not None else frame

    def fingerprint(self, path: Path) -> DatasetFingerprint:
        stat = path.stat()
        return DatasetFingerprint(size_bytes=stat.st_size, modified_time_ns=stat.st_mtime_ns)

    def inspect(self, ref: DatasetRef, path: Path) -> DatasetMetadata:
        fingerprint = self.fingerprint(path)
        return DatasetMetadata(
            file_name=ref.file_name,
            format=self.format,
            size_bytes=fingerprint.size_bytes,
            modified_time_ns=fingerprint.modified_time_ns,
            fingerprint=fingerprint.cache_token,
            can_query=self.can_query,
        )


def test_dataset_registry_rejects_path_traversal(tmp_path: Path) -> None:
    registry = DatasetRegistry(
        tmp_path,
        readers=(CsvDatasetReader(),),
        max_dataset_bytes=1_000_000,
    )

    with pytest.raises(PathTraversalError, match="outside the configured data directory"):
        registry.resolve(DatasetRef("../secret.csv"))

    with pytest.raises(PathTraversalError, match="outside the configured data directory"):
        DatasetRef(str((tmp_path / "absolute.csv").resolve()))


def test_dataset_registry_dispatches_by_format(tmp_path: Path) -> None:
    (tmp_path / "sample.csv").write_text("value\n1\n", encoding="utf-8")
    (tmp_path / "sample.json").write_text('[{"value": 2}]', encoding="utf-8")
    registry = DatasetRegistry(
        tmp_path,
        readers=(CsvDatasetReader(), JsonDatasetReader()),
        max_dataset_bytes=1_000_000,
    )

    csv_metadata = registry.inspect(DatasetRef("sample.csv"))
    json_metadata = registry.inspect(DatasetRef("sample.json"))

    assert csv_metadata.format is DatasetFormat.CSV
    assert csv_metadata.can_query is True
    assert json_metadata.format is DatasetFormat.JSON
    assert json_metadata.can_query is False
    assert registry.load_frame(DatasetRef("sample.json"), nrows=1).to_dict("records") == [
        {"value": 2}
    ]


def test_dataset_registry_rejects_unsupported_format(tmp_path: Path) -> None:
    (tmp_path / "sample.txt").write_text("value\n1\n", encoding="utf-8")
    registry = DatasetRegistry(
        tmp_path,
        readers=(CsvDatasetReader(),),
        max_dataset_bytes=1_000_000,
    )

    with pytest.raises(UnsupportedFileTypeError, match="Unsupported dataset format: .txt"):
        registry.resolve(DatasetRef("sample.txt"))


def test_dataset_registry_fingerprint_changes_when_file_changes(tmp_path: Path) -> None:
    dataset_path = tmp_path / "sample.csv"
    dataset_path.write_text("value\n1\n", encoding="utf-8")
    registry = DatasetRegistry(
        tmp_path,
        readers=(CsvDatasetReader(),),
        max_dataset_bytes=1_000_000,
    )

    first = registry.fingerprint(DatasetRef("sample.csv"))
    dataset_path.write_text("value\n1\n2\n", encoding="utf-8")
    second = registry.fingerprint(DatasetRef("sample.csv"))

    assert second.cache_token != first.cache_token


def test_existing_csv_core_functions_use_dataset_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    (tmp_path / "sample.csv").write_text("value\n1\n2\n", encoding="utf-8")

    assert list_csv_files() == ["sample.csv"]
    assert resolve_dataset_path("sample.csv") == (tmp_path / "sample.csv").resolve()
    assert read_csv_dataset("sample.csv", nrows=1).to_dict("records") == [{"value": 1}]
