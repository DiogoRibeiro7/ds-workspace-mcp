from __future__ import annotations

import json
from collections.abc import Iterable
from json import JSONDecodeError
from pathlib import Path

import pandas as pd

from ds_workspace_mcp.exceptions import DatasetReadError

from .models import (
    DatasetColumnMetadata,
    DatasetFingerprint,
    DatasetFormat,
    DatasetMetadata,
    DatasetRef,
)


class JsonDatasetReader:
    """JSON implementation with explicit bounded import policies."""

    format: DatasetFormat = DatasetFormat.JSON
    extensions: tuple[str, ...] = (".json", ".jsonl", ".ndjson")
    can_query: bool = True

    def load_frame(
        self,
        ref: DatasetRef,
        path: Path,
        *,
        nrows: int | None = None,
    ) -> pd.DataFrame:
        """Load supported JSON records into a pandas frame."""

        records, _structure = self._load_records(path)
        if nrows is not None:
            records = records[:nrows]
        return pd.DataFrame.from_records(records)

    def fingerprint(self, path: Path) -> DatasetFingerprint:
        """Return a path-free fingerprint for one JSON file."""

        stat = path.stat()
        return DatasetFingerprint(size_bytes=stat.st_size, modified_time_ns=stat.st_mtime_ns)

    def inspect(self, ref: DatasetRef, path: Path) -> DatasetMetadata:
        """Return path-free metadata for one supported JSON file."""

        records, structure = self._load_records(path)
        frame = pd.DataFrame.from_records(records)
        fingerprint = self.fingerprint(path)
        return DatasetMetadata(
            file_name=ref.file_name,
            format=self.format,
            size_bytes=fingerprint.size_bytes,
            modified_time_ns=fingerprint.modified_time_ns,
            fingerprint=fingerprint.cache_token,
            can_query=self.can_query,
            row_count=len(frame),
            column_count=len(frame.columns),
            columns=[
                DatasetColumnMetadata(name=str(column), data_type=str(dtype))
                for column, dtype in frame.dtypes.items()
            ],
            format_metadata={"structure": structure},
        )

    def _load_records(self, path: Path) -> tuple[list[dict[str, object]], str]:
        try:
            if path.suffix.lower() in {".jsonl", ".ndjson"}:
                return self._load_ndjson_records(path), "ndjson"
            return self._load_array_records(path), "records"
        except (OSError, JSONDecodeError) as exc:
            raise DatasetReadError(f"Could not read dataset: {path.name}") from exc

    def _load_array_records(self, path: Path) -> list[dict[str, object]]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise DatasetReadError("JSON dataset must be an array of records.")
        return self._validate_records(payload)

    def _load_ndjson_records(self, path: Path) -> list[dict[str, object]]:
        records: list[object] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            records.append(json.loads(line))
        return self._validate_records(records)

    def _validate_records(self, records: Iterable[object]) -> list[dict[str, object]]:
        validated_records: list[dict[str, object]] = []
        for record in records:
            if not isinstance(record, dict):
                raise DatasetReadError("JSON dataset records must be objects.")
            if any(isinstance(value, dict | list) for value in record.values()):
                raise DatasetReadError("Nested JSON values are not supported.")
            validated_records.append(dict(record))
        return validated_records
