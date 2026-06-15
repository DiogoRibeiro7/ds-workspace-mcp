from __future__ import annotations

import math
from pathlib import Path
from typing import cast

import pandas as pd
from pydantic import BaseModel

from ds_workspace_mcp.config import get_settings
from ds_workspace_mcp.profiling import DatasetProfile, build_dataset_profile


class DatasetPreview(BaseModel):
    """Small row preview for a dataset."""

    file_name: str
    rows: list[dict[str, object]]


class DatasetIssue(BaseModel):
    """Simple data-quality issue detected in a dataset."""

    column: str
    issue_type: str
    description: str


def _normalize_preview_value(value: object) -> object:
    """Convert pandas missing values into JSON-friendly nulls."""

    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def get_data_root() -> Path:
    """
    Return the configured data root.

    The default is `./data`. The directory is created if it does not exist.
    """

    return get_settings().mcp_data_root


def resolve_dataset_path(file_name: str) -> Path:
    """
    Resolve a dataset path safely inside the configured data root.

    Args:
        file_name: CSV file name relative to the data root.

    Returns:
        The resolved path to the dataset.

    Raises:
        TypeError: If `file_name` is not a string.
        ValueError: If the file name is empty, escapes the data root, or is not a CSV.
        FileNotFoundError: If the CSV file does not exist.
    """

    if not isinstance(file_name, str):
        raise TypeError("file_name must be a string.")

    if not file_name.strip():
        raise ValueError("file_name must be a non-empty string.")

    data_root = get_data_root()
    path = (data_root / file_name).resolve()

    # Prevent path traversal such as ../secret.csv.
    if path != data_root and data_root not in path.parents:
        raise ValueError("Access outside the configured data directory is not allowed.")

    if path.suffix.lower() != ".csv":
        raise ValueError("Only CSV files are supported.")

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {file_name}")

    return path


def list_csv_files() -> list[str]:
    """
    List CSV files available in the configured data root.

    Returns:
        A sorted list of CSV file names.
    """

    data_root = get_data_root()
    return sorted(path.name for path in data_root.glob("*.csv") if path.is_file())


def read_csv_dataset(file_name: str, nrows: int | None = None) -> pd.DataFrame:
    """
    Read a CSV dataset from the safe data root.

    Args:
        file_name: CSV file name relative to the data root.
        nrows: Optional number of rows to read.

    Returns:
        A pandas DataFrame.
    """

    path = resolve_dataset_path(file_name)
    return pd.read_csv(path, nrows=nrows)


def preview_csv_dataset(file_name: str, rows: int = 5) -> DatasetPreview:
    """
    Preview the first rows of a CSV dataset.

    Args:
        file_name: CSV file name relative to the data root.
        rows: Number of rows to return. Must be between 1 and 50.

    Returns:
        A structured dataset preview.
    """

    if not isinstance(rows, int):
        raise TypeError("rows must be an integer.")

    max_preview_rows = get_settings().mcp_max_preview_rows
    if rows < 1 or rows > max_preview_rows:
        raise ValueError(f"rows must be between 1 and {max_preview_rows}.")

    df = read_csv_dataset(file_name=file_name, nrows=rows)
    records = cast(list[dict[str, object]], df.astype(object).to_dict(orient="records"))
    clean_rows = [
        {column: _normalize_preview_value(value) for column, value in row.items()}
        for row in records
    ]

    return DatasetPreview(
        file_name=file_name,
        rows=clean_rows,
    )


def profile_csv_dataset(file_name: str) -> DatasetProfile:
    """
    Profile a CSV dataset.

    Args:
        file_name: CSV file name relative to the data root.

    Returns:
        A structured profile containing shape, columns, dtypes, and missing values.
    """

    df = read_csv_dataset(file_name=file_name)
    return build_dataset_profile(df=df, file_name=file_name)


def detect_csv_dataset_issues(file_name: str) -> list[DatasetIssue]:
    """
    Detect simple data-quality issues in a CSV dataset.

    Args:
        file_name: CSV file name relative to the data root.

    Returns:
        A list of conservative data-quality issues.
    """

    df = read_csv_dataset(file_name=file_name)
    issues: list[DatasetIssue] = []

    for column in df.columns:
        column_name = str(column)
        missing_ratio = float(df[column].isna().mean())

        if missing_ratio > 0.30:
            issues.append(
                DatasetIssue(
                    column=column_name,
                    issue_type="high_missingness",
                    description=f"Column has {missing_ratio:.1%} missing values.",
                )
            )

        unique_ratio = float(df[column].nunique(dropna=True) / max(len(df), 1))

        if unique_ratio > 0.95:
            issues.append(
                DatasetIssue(
                    column=column_name,
                    issue_type="possible_identifier",
                    description="Column has very high cardinality and may be an identifier.",
                )
            )

    return issues
