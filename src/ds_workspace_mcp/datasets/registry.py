from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pandas as pd

from ds_workspace_mcp.exceptions import (
    DatasetNotFoundError,
    DatasetTooLargeError,
    PathTraversalError,
    UnsupportedFileTypeError,
)

from .models import DatasetFingerprint, DatasetFormat, DatasetMetadata, DatasetRef


class DatasetReader(Protocol):
    """Format-specific dataset behavior used by the registry."""

    format: DatasetFormat
    extensions: tuple[str, ...]
    can_query: bool

    def load_frame(
        self,
        ref: DatasetRef,
        path: Path,
        *,
        nrows: int | None = None,
    ) -> pd.DataFrame:
        """Load a bounded frame from a resolved dataset path."""

    def fingerprint(self, path: Path) -> DatasetFingerprint:
        """Return a path-free fingerprint for cache invalidation."""

    def inspect(self, ref: DatasetRef, path: Path) -> DatasetMetadata:
        """Return path-free metadata for a resolved dataset."""


@dataclass(frozen=True)
class ResolvedDataset:
    """A dataset reference resolved inside an approved data root."""

    ref: DatasetRef
    path: Path
    format: DatasetFormat
    reader: DatasetReader


class DatasetRegistry:
    """Resolve and dispatch datasets without leaking filesystem access to callers."""

    def __init__(
        self,
        data_root: Path,
        readers: tuple[DatasetReader, ...],
        *,
        max_dataset_bytes: int,
    ) -> None:
        self.data_root = data_root.resolve()
        self.max_dataset_bytes = max_dataset_bytes
        self._readers_by_extension: dict[str, DatasetReader] = {}
        for reader in readers:
            for extension in reader.extensions:
                self._readers_by_extension[extension.lower()] = reader

    def list(self, dataset_format: DatasetFormat | None = None) -> list[str]:
        """List datasets directly under the registry root."""

        if not self.data_root.exists():
            return []

        names: list[str] = []
        for path in self.data_root.iterdir():
            if not path.is_file():
                continue
            reader = self._readers_by_extension.get(path.suffix.lower())
            if reader is None:
                continue
            if dataset_format is not None and reader.format != dataset_format:
                continue
            names.append(path.name)
        return sorted(names)

    def resolve(
        self,
        ref: DatasetRef,
        *,
        expected_format: DatasetFormat | None = None,
        unsupported_message: str | None = None,
    ) -> ResolvedDataset:
        """Resolve a dataset reference and select the matching reader."""

        path = (self.data_root / ref.path_name).resolve()
        if path != self.data_root and self.data_root not in path.parents:
            raise PathTraversalError("Access outside the configured data directory is not allowed.")

        reader = self._readers_by_extension.get(path.suffix.lower())
        if reader is None or (expected_format is not None and reader.format != expected_format):
            raise UnsupportedFileTypeError(
                unsupported_message or f"Unsupported dataset format: {path.suffix.lower()}"
            )

        if not path.exists():
            raise DatasetNotFoundError(f"Dataset not found: {ref.path_name}")
        if not path.is_file():
            raise DatasetNotFoundError(f"Dataset not found: {ref.path_name}")

        self._validate_dataset_file_size(path)
        return ResolvedDataset(ref=ref, path=path, format=reader.format, reader=reader)

    def inspect(
        self,
        ref: DatasetRef,
        *,
        expected_format: DatasetFormat | None = None,
        unsupported_message: str | None = None,
    ) -> DatasetMetadata:
        """Return path-free metadata for a resolved dataset."""

        resolved = self.resolve(
            ref,
            expected_format=expected_format,
            unsupported_message=unsupported_message,
        )
        return resolved.reader.inspect(ref, resolved.path)

    def load_frame(
        self,
        ref: DatasetRef,
        *,
        nrows: int | None = None,
        expected_format: DatasetFormat | None = None,
        unsupported_message: str | None = None,
    ) -> pd.DataFrame:
        """Load a bounded frame through the selected format reader."""

        resolved = self.resolve(
            ref,
            expected_format=expected_format,
            unsupported_message=unsupported_message,
        )
        return resolved.reader.load_frame(resolved.ref, resolved.path, nrows=nrows)

    def fingerprint(
        self,
        ref: DatasetRef,
        *,
        expected_format: DatasetFormat | None = None,
        unsupported_message: str | None = None,
    ) -> DatasetFingerprint:
        """Return a path-free fingerprint for one resolved dataset."""

        resolved = self.resolve(
            ref,
            expected_format=expected_format,
            unsupported_message=unsupported_message,
        )
        return resolved.reader.fingerprint(resolved.path)

    def _validate_dataset_file_size(self, path: Path) -> None:
        file_size = path.stat().st_size
        if file_size > self.max_dataset_bytes:
            raise DatasetTooLargeError(
                f"Dataset exceeds the maximum allowed size of {self.max_dataset_bytes} bytes."
            )
