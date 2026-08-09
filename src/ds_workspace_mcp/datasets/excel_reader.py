from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile

import pandas as pd

from ds_workspace_mcp.exceptions import DatasetReadError

from .models import (
    DatasetColumnMetadata,
    DatasetFingerprint,
    DatasetFormat,
    DatasetMetadata,
    DatasetRef,
)


class ExcelDatasetReader:
    """XLSX implementation with explicit sheet-selection rules."""

    format: DatasetFormat = DatasetFormat.EXCEL
    extensions: tuple[str, ...] = (".xlsx",)
    can_query: bool = True

    def load_frame(
        self,
        ref: DatasetRef,
        path: Path,
        *,
        nrows: int | None = None,
    ) -> pd.DataFrame:
        """Load one XLSX sheet into a pandas frame."""

        sheet_name = self._resolve_sheet_name(ref, path)
        try:
            return pd.read_excel(path, sheet_name=sheet_name, nrows=nrows, engine="openpyxl")
        except (BadZipFile, ValueError) as exc:
            raise DatasetReadError(f"Could not read dataset: {path.name}") from exc

    def fingerprint(self, path: Path) -> DatasetFingerprint:
        """Return a path-free fingerprint for one XLSX file."""

        stat = path.stat()
        return DatasetFingerprint(size_bytes=stat.st_size, modified_time_ns=stat.st_mtime_ns)

    def inspect(self, ref: DatasetRef, path: Path) -> DatasetMetadata:
        """Return path-free metadata for one XLSX sheet."""

        sheet_name = self._resolve_sheet_name(ref, path)
        try:
            header_frame = pd.read_excel(
                path,
                sheet_name=sheet_name,
                nrows=0,
                engine="openpyxl",
            )
        except (BadZipFile, ValueError) as exc:
            raise DatasetReadError(f"Could not read dataset: {path.name}") from exc

        fingerprint = self.fingerprint(path)
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
            format_metadata={
                "sheet_name": sheet_name,
                "sheet_names": self.list_sheets(path),
            },
        )

    def list_sheets(self, path: Path) -> list[str]:
        """Return workbook sheet names without loading sheet contents."""

        try:
            with pd.ExcelFile(path, engine="openpyxl") as workbook:
                return [str(sheet_name) for sheet_name in workbook.sheet_names]
        except (BadZipFile, ValueError) as exc:
            raise DatasetReadError(f"Could not read dataset: {path.name}") from exc

    def _resolve_sheet_name(self, ref: DatasetRef, path: Path) -> str:
        sheet_names = self.list_sheets(path)
        if ref.selector is not None:
            if ref.selector not in sheet_names:
                raise DatasetReadError(f"Excel sheet not found: {ref.selector}")
            return ref.selector
        if len(sheet_names) == 1:
            return sheet_names[0]
        raise DatasetReadError("Excel sheet selection is ambiguous; use file_name#sheet_name.")
