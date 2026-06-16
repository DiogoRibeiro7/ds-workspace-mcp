from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal, cast

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype
from pydantic import BaseModel, Field

from ds_workspace_mcp.core import read_csv_dataset

CorrelationMethod = Literal["pearson", "spearman", "kendall"]
CORRELATION_METHODS: set[CorrelationMethod] = {"pearson", "spearman", "kendall"}
MAX_CORRELATION_RESULTS = 10
HIGH_CORRELATION_THRESHOLD = 0.9


class CorrelationPair(BaseModel):
    """A ranked correlation between two numeric columns."""

    left_column: str
    right_column: str
    correlation: float
    absolute_correlation: float = Field(ge=0.0, le=1.0)


class CorrelationSummary(BaseModel):
    """Bounded correlation summary for a dataset."""

    file_name: str
    method: str
    numeric_columns: list[str]
    top_correlations: list[CorrelationPair]


class LeakageWarning(BaseModel):
    """A heuristic warning about possible target leakage."""

    column: str
    warning_type: str
    description: str


class LeakageSummary(BaseModel):
    """Heuristic target leakage summary for a dataset."""

    file_name: str
    target_column: str
    warnings: list[LeakageWarning]


def summarize_correlations_dataset(
    file_name: str,
    method: str = "pearson",
) -> CorrelationSummary:
    """Return the top absolute correlations among numeric columns."""

    validated_method = _validate_correlation_method(method)
    df = read_csv_dataset(file_name)
    numeric_df = df.select_dtypes(include=["number"]).copy()
    numeric_columns = [str(column) for column in numeric_df.columns]

    if len(numeric_columns) < 2:
        return CorrelationSummary(
            file_name=file_name,
            method=validated_method,
            numeric_columns=numeric_columns,
            top_correlations=[],
        )

    correlation_matrix = numeric_df.corr(method=cast(CorrelationMethod, validated_method))
    pairs: list[CorrelationPair] = []
    for left_index, left_column in enumerate(numeric_columns):
        for right_column in numeric_columns[left_index + 1 :]:
            value = correlation_matrix.loc[left_column, right_column]
            if pd.isna(value):
                continue
            pairs.append(
                CorrelationPair(
                    left_column=left_column,
                    right_column=right_column,
                    correlation=_to_float(value),
                    absolute_correlation=abs(_to_float(value)),
                )
            )

    top_pairs = sorted(
        pairs,
        key=lambda pair: (pair.absolute_correlation, abs(pair.correlation)),
        reverse=True,
    )[:MAX_CORRELATION_RESULTS]
    return CorrelationSummary(
        file_name=file_name,
        method=validated_method,
        numeric_columns=numeric_columns,
        top_correlations=top_pairs,
    )


def detect_possible_target_leakage_dataset(
    file_name: str,
    target_column: str,
) -> LeakageSummary:
    """Return heuristic warnings about possible target leakage."""

    df = read_csv_dataset(file_name)
    if target_column not in df.columns:
        raise ValueError(f"Unknown target column: {target_column}")

    warnings: list[LeakageWarning] = []
    target_series = df[target_column]
    target_name_normalized = _normalize_name(target_column)

    for column in df.columns:
        column_name = str(column)
        if column_name == target_column:
            continue

        series = df[column]
        warning_types: set[str] = set()

        if target_name_normalized and target_name_normalized in _normalize_name(column_name):
            warning_types.add("target_name_overlap")
            warnings.append(
                LeakageWarning(
                    column=column_name,
                    warning_type="target_name_overlap",
                    description="Column name contains the target name and may encode the label.",
                )
            )

        if _is_identifier_like(series):
            warning_types.add("identifier_like")
            warnings.append(
                LeakageWarning(
                    column=column_name,
                    warning_type="identifier_like",
                    description="Column has near-unique values and may act like an identifier.",
                )
            )

        if _is_highly_correlated(series, target_series):
            warning_types.add("high_correlation")
            warnings.append(
                LeakageWarning(
                    column=column_name,
                    warning_type="high_correlation",
                    description=(
                        "Column is highly correlated with the target "
                        "and may leak target information."
                    ),
                )
            )

        if _is_duplicate_column(series, target_series):
            warning_types.add("duplicate_values")
            warnings.append(
                LeakageWarning(
                    column=column_name,
                    warning_type="duplicate_values",
                    description="Column duplicates the target values exactly after alignment.",
                )
            )

        if _is_datetime_like(series):
            warnings.append(
                LeakageWarning(
                    column=column_name,
                    warning_type="datetime_review",
                    description=(
                        "Datetime-like column may occur after the prediction "
                        "point and should be reviewed."
                    ),
                )
            )

    ordered_warnings = sorted(warnings, key=lambda warning: (warning.column, warning.warning_type))
    return LeakageSummary(
        file_name=file_name,
        target_column=target_column,
        warnings=ordered_warnings,
    )


def _validate_correlation_method(method: str) -> str:
    """Validate the requested correlation method."""

    if method not in CORRELATION_METHODS:
        raise ValueError("method must be one of: pearson, spearman, kendall.")
    return method


def _normalize_name(value: str) -> str:
    """Normalize a column name for heuristic comparisons."""

    return "".join(character for character in value.lower() if character.isalnum())


def _is_identifier_like(series: pd.Series[Any]) -> bool:
    """Return whether a column behaves like an identifier."""

    non_null = series.dropna()
    if non_null.empty:
        return False
    unique_ratio = float(non_null.nunique() / max(len(series), 1))
    return unique_ratio > 0.95


def _is_highly_correlated(left: pd.Series[Any], right: pd.Series[Any]) -> bool:
    """Return whether two numeric series are strongly correlated."""

    if not is_numeric_dtype(left) or not is_numeric_dtype(right):
        return False

    combined = pd.concat([left, right], axis=1).dropna()
    if len(combined) < 3:
        return False
    if combined.iloc[:, 0].nunique() <= 1 or combined.iloc[:, 1].nunique() <= 1:
        return False

    correlation = combined.iloc[:, 0].corr(combined.iloc[:, 1])
    if pd.isna(correlation):
        return False
    return abs(float(correlation)) >= HIGH_CORRELATION_THRESHOLD


def _is_duplicate_column(left: pd.Series[Any], right: pd.Series[Any]) -> bool:
    """Return whether two aligned columns have identical non-null values."""

    combined = pd.concat([left, right], axis=1).dropna()
    if combined.empty:
        return False
    return bool(combined.iloc[:, 0].equals(combined.iloc[:, 1]))


def _is_datetime_like(series: pd.Series[Any]) -> bool:
    """Conservatively detect datetime-like columns."""

    if is_datetime64_any_dtype(series):
        return True

    if is_numeric_dtype(series):
        return False

    non_null = series.dropna()
    if non_null.empty:
        return False

    values = [str(value).strip() for value in non_null.tolist()]
    if not _has_datetime_markers(values):
        return False

    parsed = pd.to_datetime(non_null, errors="coerce")
    return bool(not parsed.isna().any())


def _has_datetime_markers(values: Iterable[str]) -> bool:
    """Return whether values look timestamp-like before parsing."""

    return any(any(marker in value for marker in ("-", "/", ":", "T")) for value in values)


def _to_float(value: object) -> float:
    """Convert pandas numeric correlation scalars into floats."""

    return float(cast(Any, value))
