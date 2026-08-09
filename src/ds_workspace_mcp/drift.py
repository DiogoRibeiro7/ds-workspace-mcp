from __future__ import annotations

import math
from typing import Any, cast

import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
    is_string_dtype,
)
from pydantic import BaseModel, Field

from ds_workspace_mcp.config import get_settings
from ds_workspace_mcp.core import read_dataset_frame


class DatasetComparisonSampling(BaseModel):
    """Bounded-computation policy used for dataset comparison."""

    strategy: str
    max_rows_per_dataset: int = Field(ge=1)
    left_rows_analyzed: int = Field(ge=0)
    right_rows_analyzed: int = Field(ge=0)
    left_truncated: bool
    right_truncated: bool
    note: str


class RowCountChange(BaseModel):
    """Row-count comparison for analyzed rows."""

    left_row_count: int = Field(ge=0)
    right_row_count: int = Field(ge=0)
    change: int
    exact: bool


class ColumnTypeChange(BaseModel):
    """Dtype change for a shared column."""

    column: str
    left_dtype: str
    right_dtype: str


class NullRateChange(BaseModel):
    """Null-rate change for a shared column."""

    column: str
    left_null_rate: float = Field(ge=0.0, le=1.0)
    right_null_rate: float = Field(ge=0.0, le=1.0)
    change: float


class CardinalityChange(BaseModel):
    """Cardinality change for a bounded categorical column."""

    column: str
    left_unique_count: int = Field(ge=0)
    right_unique_count: int = Field(ge=0)
    change: int


class DatasetSchemaDiff(BaseModel):
    """Structural comparison between two datasets."""

    added_columns: list[str]
    removed_columns: list[str]
    dtype_changes: list[ColumnTypeChange]
    null_rate_changes: list[NullRateChange]
    row_count: RowCountChange
    cardinality_changes: list[CardinalityChange]


class NumericDrift(BaseModel):
    """Transparent numeric drift statistics for one shared numeric column."""

    column: str
    left_count: int = Field(ge=0)
    right_count: int = Field(ge=0)
    left_mean: float | None
    right_mean: float | None
    standardized_mean_difference: float | None
    left_std: float | None
    right_std: float | None
    median_shift: float | None
    q25_shift: float | None
    q75_shift: float | None
    ks_statistic: float | None
    effect_size: str
    statistical_evidence: str


class CategoryDistributionChange(BaseModel):
    """Bounded aligned category distribution detail."""

    category: str
    left_proportion: float = Field(ge=0.0, le=1.0)
    right_proportion: float = Field(ge=0.0, le=1.0)
    difference: float


class CategoricalDrift(BaseModel):
    """Transparent categorical drift statistics for one shared categorical column."""

    column: str
    left_count: int = Field(ge=0)
    right_count: int = Field(ge=0)
    left_unique_count: int = Field(ge=0)
    right_unique_count: int = Field(ge=0)
    total_variation_distance: float
    jensen_shannon_divergence: float
    compared_categories: list[CategoryDistributionChange]
    other_category_included: bool
    effect_size: str
    statistical_evidence: str


class TimestampRangeChange(BaseModel):
    """Timestamp range change for one shared datetime-like column."""

    column: str
    left_min: str | None
    left_max: str | None
    right_min: str | None
    right_max: str | None
    min_shift_seconds: float | None
    max_shift_seconds: float | None


class DatasetDriftDiagnostics(BaseModel):
    """Statistical drift diagnostics separated from schema changes."""

    numeric: list[NumericDrift]
    categorical: list[CategoricalDrift]
    timestamp_ranges: list[TimestampRangeChange]


class DatasetComparisonResult(BaseModel):
    """Bounded dataset comparison result."""

    left_file_name: str
    right_file_name: str
    schema_diff: DatasetSchemaDiff
    drift: DatasetDriftDiagnostics
    sampling: DatasetComparisonSampling


def compare_datasets_dataset(left_file_name: str, right_file_name: str) -> DatasetComparisonResult:
    """Compare two approved datasets using bounded transparent diagnostics."""

    settings = get_settings()
    sample_limit = settings.mcp_max_sql_rows
    left_raw = read_dataset_frame(left_file_name, nrows=sample_limit + 1)
    right_raw = read_dataset_frame(right_file_name, nrows=sample_limit + 1)
    left_truncated = len(left_raw) > sample_limit
    right_truncated = len(right_raw) > sample_limit
    left = left_raw.head(sample_limit).copy()
    right = right_raw.head(sample_limit).copy()
    sampling = DatasetComparisonSampling(
        strategy="head" if left_truncated or right_truncated else "full",
        max_rows_per_dataset=sample_limit,
        left_rows_analyzed=len(left),
        right_rows_analyzed=len(right),
        left_truncated=left_truncated,
        right_truncated=right_truncated,
        note=(
            "Comparison uses the first bounded rows from each dataset."
            if left_truncated or right_truncated
            else "Comparison used all rows loaded from each dataset."
        ),
    )
    common_columns = _common_columns(left, right)
    return DatasetComparisonResult(
        left_file_name=left_file_name,
        right_file_name=right_file_name,
        schema_diff=_build_schema_diff(left, right, sampling),
        drift=_build_drift_diagnostics(left, right, common_columns),
        sampling=sampling,
    )


def _build_schema_diff(
    left: pd.DataFrame,
    right: pd.DataFrame,
    sampling: DatasetComparisonSampling,
) -> DatasetSchemaDiff:
    left_columns = [str(column) for column in left.columns]
    right_columns = [str(column) for column in right.columns]
    common_columns = [column for column in left_columns if column in set(right_columns)]
    return DatasetSchemaDiff(
        added_columns=[column for column in right_columns if column not in set(left_columns)],
        removed_columns=[column for column in left_columns if column not in set(right_columns)],
        dtype_changes=_build_dtype_changes(left, right, common_columns),
        null_rate_changes=_build_null_rate_changes(left, right, common_columns),
        row_count=RowCountChange(
            left_row_count=len(left),
            right_row_count=len(right),
            change=len(right) - len(left),
            exact=not sampling.left_truncated and not sampling.right_truncated,
        ),
        cardinality_changes=_build_cardinality_changes(left, right, common_columns),
    )


def _build_dtype_changes(
    left: pd.DataFrame,
    right: pd.DataFrame,
    common_columns: list[str],
) -> list[ColumnTypeChange]:
    changes: list[ColumnTypeChange] = []
    for column in common_columns:
        left_dtype = str(left[column].dtype)
        right_dtype = str(right[column].dtype)
        if left_dtype != right_dtype:
            changes.append(
                ColumnTypeChange(column=column, left_dtype=left_dtype, right_dtype=right_dtype)
            )
    return changes


def _build_null_rate_changes(
    left: pd.DataFrame,
    right: pd.DataFrame,
    common_columns: list[str],
) -> list[NullRateChange]:
    changes: list[NullRateChange] = []
    for column in common_columns:
        left_rate = _null_rate(left[column])
        right_rate = _null_rate(right[column])
        if not math.isclose(left_rate, right_rate, abs_tol=0.0001):
            changes.append(
                NullRateChange(
                    column=column,
                    left_null_rate=left_rate,
                    right_null_rate=right_rate,
                    change=right_rate - left_rate,
                )
            )
    return changes


def _build_cardinality_changes(
    left: pd.DataFrame,
    right: pd.DataFrame,
    common_columns: list[str],
) -> list[CardinalityChange]:
    max_values = get_settings().mcp_max_categorical_values
    changes: list[CardinalityChange] = []
    for column in common_columns:
        if not (_is_categorical_series(left[column]) and _is_categorical_series(right[column])):
            continue
        left_unique = int(left[column].dropna().astype(str).nunique())
        right_unique = int(right[column].dropna().astype(str).nunique())
        if max(left_unique, right_unique) > max_values:
            continue
        if left_unique != right_unique:
            changes.append(
                CardinalityChange(
                    column=column,
                    left_unique_count=left_unique,
                    right_unique_count=right_unique,
                    change=right_unique - left_unique,
                )
            )
    return changes


def _build_drift_diagnostics(
    left: pd.DataFrame,
    right: pd.DataFrame,
    common_columns: list[str],
) -> DatasetDriftDiagnostics:
    numeric: list[NumericDrift] = []
    categorical: list[CategoricalDrift] = []
    timestamp_ranges: list[TimestampRangeChange] = []
    for column in common_columns:
        left_series = left[column]
        right_series = right[column]
        left_datetime = _coerce_datetime_series(left_series)
        right_datetime = _coerce_datetime_series(right_series)
        if left_datetime is not None and right_datetime is not None:
            timestamp_ranges.append(
                _build_timestamp_range_change(column, left_datetime, right_datetime)
            )
            continue
        if _is_numeric_series(left_series) and _is_numeric_series(right_series):
            numeric.append(_build_numeric_drift(column, left_series, right_series))
            continue
        if _is_categorical_series(left_series) and _is_categorical_series(right_series):
            categorical.append(_build_categorical_drift(column, left_series, right_series))
    return DatasetDriftDiagnostics(
        numeric=numeric,
        categorical=categorical,
        timestamp_ranges=timestamp_ranges,
    )


def _build_numeric_drift(
    column: str,
    left: pd.Series[Any],
    right: pd.Series[Any],
) -> NumericDrift:
    left_numeric = pd.to_numeric(left, errors="coerce").dropna()
    right_numeric = pd.to_numeric(right, errors="coerce").dropna()
    left_mean = _optional_float(left_numeric.mean())
    right_mean = _optional_float(right_numeric.mean())
    left_std = _optional_float(left_numeric.std())
    right_std = _optional_float(right_numeric.std())
    pooled_std = _pooled_std(left_numeric, right_numeric)
    smd = None
    if (
        pooled_std is not None
        and pooled_std > 0
        and left_mean is not None
        and right_mean is not None
    ):
        smd = (right_mean - left_mean) / pooled_std
    left_quantiles = left_numeric.quantile([0.25, 0.5, 0.75]) if not left_numeric.empty else None
    right_quantiles = right_numeric.quantile([0.25, 0.5, 0.75]) if not right_numeric.empty else None
    ks_statistic = _ks_statistic(left_numeric, right_numeric)
    return NumericDrift(
        column=column,
        left_count=int(left_numeric.count()),
        right_count=int(right_numeric.count()),
        left_mean=left_mean,
        right_mean=right_mean,
        standardized_mean_difference=_optional_float(smd),
        left_std=left_std,
        right_std=right_std,
        median_shift=_quantile_shift(left_quantiles, right_quantiles, 0.5),
        q25_shift=_quantile_shift(left_quantiles, right_quantiles, 0.25),
        q75_shift=_quantile_shift(left_quantiles, right_quantiles, 0.75),
        ks_statistic=ks_statistic,
        effect_size=_numeric_effect_label(smd),
        statistical_evidence=_sample_size_label(len(left_numeric), len(right_numeric)),
    )


def _build_categorical_drift(
    column: str,
    left: pd.Series[Any],
    right: pd.Series[Any],
) -> CategoricalDrift:
    max_values = get_settings().mcp_max_categorical_values
    left_normalized = left.dropna().astype(str)
    right_normalized = right.dropna().astype(str)
    left_counts = left_normalized.value_counts()
    right_counts = right_normalized.value_counts()
    ranked_categories = (
        (left_counts.add(right_counts, fill_value=0))
        .sort_values(ascending=False)
        .head(max_values)
        .index.tolist()
    )
    all_categories = set(left_counts.index).union(set(right_counts.index))
    other_included = len(all_categories.difference(set(ranked_categories))) > 0
    left_total = max(int(left_counts.sum()), 1)
    right_total = max(int(right_counts.sum()), 1)
    left_distribution: list[float] = []
    right_distribution: list[float] = []
    compared: list[CategoryDistributionChange] = []
    for category in ranked_categories:
        left_prop = float(left_counts.get(category, 0) / left_total)
        right_prop = float(right_counts.get(category, 0) / right_total)
        left_distribution.append(left_prop)
        right_distribution.append(right_prop)
        compared.append(
            CategoryDistributionChange(
                category=str(category),
                left_proportion=left_prop,
                right_proportion=right_prop,
                difference=right_prop - left_prop,
            )
        )
    if other_included:
        left_other = max(0.0, 1.0 - sum(left_distribution))
        right_other = max(0.0, 1.0 - sum(right_distribution))
        left_distribution.append(left_other)
        right_distribution.append(right_other)
        compared.append(
            CategoryDistributionChange(
                category="__other__",
                left_proportion=left_other,
                right_proportion=right_other,
                difference=right_other - left_other,
            )
        )
    tvd = _total_variation_distance(left_distribution, right_distribution)
    return CategoricalDrift(
        column=column,
        left_count=int(left_normalized.count()),
        right_count=int(right_normalized.count()),
        left_unique_count=int(left_normalized.nunique()),
        right_unique_count=int(right_normalized.nunique()),
        total_variation_distance=tvd,
        jensen_shannon_divergence=_jensen_shannon_divergence(left_distribution, right_distribution),
        compared_categories=compared,
        other_category_included=other_included,
        effect_size=_categorical_effect_label(tvd),
        statistical_evidence=_sample_size_label(len(left_normalized), len(right_normalized)),
    )


def _build_timestamp_range_change(
    column: str,
    left: pd.Series[Any],
    right: pd.Series[Any],
) -> TimestampRangeChange:
    left_min = left.min()
    left_max = left.max()
    right_min = right.min()
    right_max = right.max()
    return TimestampRangeChange(
        column=column,
        left_min=_timestamp_iso(left_min),
        left_max=_timestamp_iso(left_max),
        right_min=_timestamp_iso(right_min),
        right_max=_timestamp_iso(right_max),
        min_shift_seconds=_timestamp_shift_seconds(left_min, right_min),
        max_shift_seconds=_timestamp_shift_seconds(left_max, right_max),
    )


def _common_columns(left: pd.DataFrame, right: pd.DataFrame) -> list[str]:
    right_columns = {str(column) for column in right.columns}
    return [str(column) for column in left.columns if str(column) in right_columns]


def _is_numeric_series(series: pd.Series[Any]) -> bool:
    return bool(is_numeric_dtype(series) and not is_bool_dtype(series))


def _is_categorical_series(series: pd.Series[Any]) -> bool:
    return bool(
        is_object_dtype(series) or is_string_dtype(series) or str(series.dtype) == "category"
    )


def _coerce_datetime_series(series: pd.Series[Any]) -> pd.Series[Any] | None:
    if is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce").dropna()
    if not (is_object_dtype(series) or is_string_dtype(series)):
        return None
    non_null = series.dropna()
    if non_null.empty:
        return None
    values = [str(value).strip() for value in non_null.tolist()]
    if not any(any(marker in value for marker in ("-", "/", ":", "T")) for value in values):
        return None
    converted = pd.to_datetime(non_null, errors="coerce")
    if converted.isna().any():
        return None
    return converted.dropna()


def _null_rate(series: pd.Series[Any]) -> float:
    if len(series) == 0:
        return 0.0
    return float(series.isna().mean())


def _pooled_std(left: pd.Series[Any], right: pd.Series[Any]) -> float | None:
    left_count = len(left)
    right_count = len(right)
    if left_count < 2 or right_count < 2:
        return None
    left_var = float(left.var())
    right_var = float(right.var())
    numerator = ((left_count - 1) * left_var) + ((right_count - 1) * right_var)
    denominator = left_count + right_count - 2
    if denominator <= 0:
        return None
    return math.sqrt(numerator / denominator)


def _ks_statistic(left: pd.Series[Any], right: pd.Series[Any]) -> float | None:
    if left.empty or right.empty:
        return None
    left_values = sorted(float(value) for value in left.tolist())
    right_values = sorted(float(value) for value in right.tolist())
    values = sorted(set(left_values + right_values))
    left_index = 0
    right_index = 0
    max_delta = 0.0
    for value in values:
        while left_index < len(left_values) and left_values[left_index] <= value:
            left_index += 1
        while right_index < len(right_values) and right_values[right_index] <= value:
            right_index += 1
        left_cdf = left_index / len(left_values)
        right_cdf = right_index / len(right_values)
        max_delta = max(max_delta, abs(left_cdf - right_cdf))
    return max_delta


def _quantile_shift(
    left_quantiles: pd.Series[Any] | None,
    right_quantiles: pd.Series[Any] | None,
    quantile: float,
) -> float | None:
    if left_quantiles is None or right_quantiles is None:
        return None
    return _optional_float(right_quantiles.loc[quantile] - left_quantiles.loc[quantile])


def _total_variation_distance(left: list[float], right: list[float]) -> float:
    return 0.5 * sum(
        abs(right_value - left_value) for left_value, right_value in zip(left, right, strict=True)
    )


def _jensen_shannon_divergence(left: list[float], right: list[float]) -> float:
    midpoint = [
        (left_value + right_value) / 2 for left_value, right_value in zip(left, right, strict=True)
    ]
    return 0.5 * _kl_divergence(left, midpoint) + 0.5 * _kl_divergence(right, midpoint)


def _kl_divergence(values: list[float], reference: list[float]) -> float:
    total = 0.0
    for value, ref_value in zip(values, reference, strict=True):
        if value <= 0:
            continue
        if ref_value <= 0:
            continue
        total += value * math.log(value / ref_value, 2)
    return total


def _numeric_effect_label(value: float | None) -> str:
    if value is None:
        return "unavailable"
    magnitude = abs(value)
    if magnitude >= 0.8:
        return "large"
    if magnitude >= 0.5:
        return "medium"
    if magnitude >= 0.2:
        return "small"
    return "negligible"


def _categorical_effect_label(value: float) -> str:
    if value >= 0.5:
        return "large"
    if value >= 0.25:
        return "medium"
    if value >= 0.1:
        return "small"
    return "negligible"


def _sample_size_label(left_count: int, right_count: int) -> str:
    minimum = min(left_count, right_count)
    if minimum >= 100:
        return "strong_sample_size"
    if minimum >= 30:
        return "moderate_sample_size"
    if minimum > 0:
        return "small_sample_size"
    return "insufficient_non_null_values"


def _optional_float(value: object) -> float | None:
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, int | float):
        return float(value)
    return float(value)  # type: ignore[arg-type]


def _timestamp_iso(value: object) -> str | None:
    if _is_missing_timestamp(value):
        return None
    timestamp = pd.Timestamp(cast(Any, value))
    return timestamp.isoformat()


def _timestamp_shift_seconds(left: object, right: object) -> float | None:
    if _is_missing_timestamp(left) or _is_missing_timestamp(right):
        return None
    return float((pd.Timestamp(cast(Any, right)) - pd.Timestamp(cast(Any, left))).total_seconds())


def _is_missing_timestamp(value: object) -> bool:
    if value is None or value is pd.NaT:
        return True
    return isinstance(value, float) and math.isnan(value)
