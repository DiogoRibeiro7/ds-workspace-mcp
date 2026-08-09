from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from ds_workspace_mcp.exceptions import DatasetReadError

from .models import (
    DatasetColumnMetadata,
    DatasetFingerprint,
    DatasetFormat,
    DatasetMetadata,
    DatasetRef,
)


class ParquetDatasetReader:
    """Parquet implementation of the dataset reader interface."""

    format: DatasetFormat = DatasetFormat.PARQUET
    extensions: tuple[str, ...] = (".parquet",)
    can_query: bool = True

    def load_frame(self, path: Path, *, nrows: int | None = None) -> pd.DataFrame:
        """Load a bounded Parquet frame through DuckDB."""

        query = "SELECT * FROM read_parquet(?)"
        parameters: list[object] = [str(path)]
        if nrows is not None:
            query = f"{query} LIMIT ?"
            parameters.append(nrows)

        try:
            with duckdb.connect(database=":memory:") as connection:
                return connection.execute(query, parameters).fetch_df()
        except duckdb.Error as exc:
            raise DatasetReadError(f"Could not read dataset: {path.name}") from exc

    def fingerprint(self, path: Path) -> DatasetFingerprint:
        """Return a path-free fingerprint for one Parquet file."""

        stat = path.stat()
        return DatasetFingerprint(
            size_bytes=stat.st_size,
            modified_time_ns=stat.st_mtime_ns,
        )

    def inspect(self, ref: DatasetRef, path: Path) -> DatasetMetadata:
        """Return bounded, path-free metadata for one Parquet file."""

        try:
            with duckdb.connect(database=":memory:") as connection:
                schema_rows = connection.execute(
                    "DESCRIBE SELECT * FROM read_parquet(?)",
                    [str(path)],
                ).fetchall()
                row_count = connection.execute(
                    "SELECT COUNT(*) FROM read_parquet(?)",
                    [str(path)],
                ).fetchone()
        except duckdb.Error as exc:
            raise DatasetReadError(f"Could not read dataset: {path.name}") from exc

        fingerprint = self.fingerprint(path)
        columns = [
            DatasetColumnMetadata(name=str(row[0]), data_type=str(row[1])) for row in schema_rows
        ]
        return DatasetMetadata(
            file_name=ref.file_name,
            format=self.format,
            size_bytes=fingerprint.size_bytes,
            modified_time_ns=fingerprint.modified_time_ns,
            fingerprint=fingerprint.cache_token,
            can_query=self.can_query,
            row_count=int(row_count[0]) if row_count is not None else None,
            column_count=len(columns),
            columns=columns,
        )
