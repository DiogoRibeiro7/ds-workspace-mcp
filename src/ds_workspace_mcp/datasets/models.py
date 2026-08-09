from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from ds_workspace_mcp.exceptions import InvalidDatasetNameError, PathTraversalError


class DatasetFormat(StrEnum):
    """Dataset formats supported by the dataset registry."""

    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"
    EXCEL = "excel"


@dataclass(frozen=True)
class DatasetRef:
    """A dataset reference relative to an approved data root."""

    file_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.file_name, str):
            raise InvalidDatasetNameError("file_name must be a string.")
        if not self.file_name.strip():
            raise InvalidDatasetNameError("file_name must be a non-empty string.")
        if not self.path_name:
            raise InvalidDatasetNameError("file_name must include a dataset file name.")
        if Path(self.path_name).is_absolute():
            raise PathTraversalError("Access outside the configured data directory is not allowed.")

    @property
    def path_name(self) -> str:
        """Return the relative filesystem component without an optional selector."""

        return self.file_name.split("#", maxsplit=1)[0].strip()

    @property
    def selector(self) -> str | None:
        """Return an optional format-specific selector such as an Excel sheet name."""

        if "#" not in self.file_name:
            return None
        selector = self.file_name.split("#", maxsplit=1)[1].strip()
        return selector or None


@dataclass(frozen=True)
class DatasetFingerprint:
    """A stable file fingerprint for cache invalidation."""

    size_bytes: int
    modified_time_ns: int

    @property
    def cache_token(self) -> str:
        """Return a path-free token that changes when the file fingerprint changes."""

        return f"{self.size_bytes}:{self.modified_time_ns}"


class DatasetColumnMetadata(BaseModel):
    """Path-free metadata for one dataset column."""

    name: str
    data_type: str


class DatasetMetadata(BaseModel):
    """Path-free metadata for one resolved dataset."""

    file_name: str
    format: DatasetFormat
    size_bytes: int = Field(ge=0)
    modified_time_ns: int = Field(ge=0)
    fingerprint: str
    can_query: bool
    row_count: int | None = Field(default=None, ge=0)
    column_count: int | None = Field(default=None, ge=0)
    columns: list[DatasetColumnMetadata] = Field(default_factory=list)
    format_metadata: dict[str, object] = Field(default_factory=dict)
