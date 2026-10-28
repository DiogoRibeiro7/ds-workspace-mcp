from __future__ import annotations

import warnings
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

        return _read_csv_frame(path, nrows=nrows)

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
        header_frame = _read_csv_frame(path, nrows=0)
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


def _read_csv_frame(path: Path, *, nrows: int | None = None) -> pd.DataFrame:
    """Read strict UTF-8 CSV, distinguishing empty, malformed and undecodable inputs.

    A UTF-8 BOM is accepted, but mixed or legacy encodings are never guessed or
    silently repaired. Header-only files remain valid zero-row datasets.
    """

    try:
        with warnings.catch_warnings():
            # Do not let pandas silently treat excess CSV fields as an index
            # or drop their values while parsing inconsistent rows.
            warnings.simplefilter("error", pd.errors.ParserWarning)
            return pd.read_csv(
                path,
                nrows=nrows,
                encoding="utf-8-sig",
                index_col=False,
                on_bad_lines="error",
            )
    except pd.errors.EmptyDataError as exc:
        raise DatasetReadError(
            f"Could not read dataset: {path.name} (empty CSV or missing header)."
        ) from exc
    except UnicodeDecodeError as exc:
        raise DatasetReadError(
            f"Could not read dataset: {path.name} (invalid or mixed UTF-8 encoding)."
        ) from exc
    except (pd.errors.ParserError, pd.errors.ParserWarning, ValueError) as exc:
        raise DatasetReadError(f"Could not read dataset: {path.name} (malformed CSV).") from exc
