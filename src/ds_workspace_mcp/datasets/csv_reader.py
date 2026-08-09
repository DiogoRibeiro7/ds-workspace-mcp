from __future__ import annotations

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


class CsvDatasetReader:
    """CSV implementation of the dataset reader interface."""

    format: DatasetFormat = DatasetFormat.CSV
    extensions: tuple[str, ...] = (".csv",)
    can_query: bool = True

    def load_frame(
        self,
        ref: DatasetRef,
        path: Path,
        *,
        nrows: int | None = None,
    ) -> pd.DataFrame:
        """Load a CSV dataset into a pandas frame."""

        try:
            return pd.read_csv(path, nrows=nrows)
        except (UnicodeDecodeError, pd.errors.ParserError) as exc:
            raise DatasetReadError(f"Could not read dataset: {path.name}") from exc

    def fingerprint(self, path: Path) -> DatasetFingerprint:
        """Return a path-free fingerprint for one CSV file."""

        stat = path.stat()
        return DatasetFingerprint(
            size_bytes=stat.st_size,
            modified_time_ns=stat.st_mtime_ns,
        )

    def inspect(self, ref: DatasetRef, path: Path) -> DatasetMetadata:
        """Return path-free metadata for one CSV file."""

        fingerprint = self.fingerprint(path)
        try:
            header_frame = pd.read_csv(path, nrows=0)
        except (UnicodeDecodeError, pd.errors.ParserError) as exc:
            raise DatasetReadError(f"Could not read dataset: {path.name}") from exc
        return DatasetMetadata(
            file_name=ref.file_name,
            format=self.format,
            size_bytes=fingerprint.size_bytes,
            modified_time_ns=fingerprint.modified_time_ns,
            fingerprint=fingerprint.cache_token,
            can_query=self.can_query,
            column_count=len(header_frame.columns),
            columns=[
                DatasetColumnMetadata(name=str(column), data_type=str(dtype))
                for column, dtype in header_frame.dtypes.items()
            ],
        )
