from __future__ import annotations

import math
from collections.abc import Iterable
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


class ValueFrequency(BaseModel):
    """A bounded frequency summary for categorical-like data."""

    value: str
    count: int = Field(ge=0)


class NumericColumnProfile(BaseModel):
    """Summary statistics for a numeric column."""

    column: str
    count: int = Field(ge=0)
    mean: float | None
    std: float | None
    min: float | None
    q25: float | None
    median: float | None
    q75: float | None
    max: float | None


class CategoricalColumnProfile(BaseModel):
    """Summary statistics for a categorical column."""

    column: str
    count: int = Field(ge=0)
    unique_count: int = Field(ge=0)
    top_value: str | None
    top_value_frequency: int = Field(ge=0)
    top_values: list[ValueFrequency]


class BooleanColumnProfile(BaseModel):
    """Summary statistics for a boolean column."""

    column: str
    true_count: int = Field(ge=0)
    false_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)


class DatetimeColumnProfile(BaseModel):
    """Summary statistics for a datetime column."""

    column: str
    count: int = Field(ge=0)
    min: str | None
    max: str | None


class ProfilingLimits(BaseModel):
    """Runtime bounds applied by the profiling layer."""

    max_categorical_values: int = Field(ge=1)


class DatasetProfile(BaseModel):
    """Structured profile for a tabular dataset."""

    file_name: str
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    columns: list[str]
    dtypes: dict[str, str]
    missing_values: dict[str, int]
    missing_percentage: dict[str, float]
    numeric_columns: list[NumericColumnProfile] = Field(default_factory=list)
    categorical_columns: list[CategoricalColumnProfile] = Field(default_factory=list)
    boolean_columns: list[BooleanColumnProfile] = Field(default_factory=list)
    datetime_columns: list[DatetimeColumnProfile] = Field(default_factory=list)
    profiling_limits: ProfilingLimits


def build_dataset_profile(df: pd.DataFrame, file_name: str) -> DatasetProfile:
    """Build a bounded structured profile for a dataset."""

    missing_values = df.isna().sum().astype(int).to_dict()
    missing_percentage = (df.isna().mean() * 100).round(2).to_dict()
    max_categorical_values = get_settings().mcp_max_categorical_values

    numeric_profiles: list[NumericColumnProfile] = []
    categorical_profiles: list[CategoricalColumnProfile] = []
    boolean_profiles: list[BooleanColumnProfile] = []
    datetime_profiles: list[DatetimeColumnProfile] = []

    for column in df.columns:
        column_name = str(column)
        series = df[column]
        datetime_series = _coerce_datetime_series(series)

        if _is_boolean_series(series):
            boolean_profiles.append(_build_boolean_profile(column_name, series))
            continue

        if datetime_series is not None:
            datetime_profiles.append(_build_datetime_profile(column_name, datetime_series))
            continue

        if _is_numeric_series(series):
            numeric_profiles.append(_build_numeric_profile(column_name, series))
            continue

        if _is_categorical_series(series):
            categorical_profiles.append(
                _build_categorical_profile(
                    column_name=column_name,
                    series=series,
                    max_values=max_categorical_values,
                )
            )

    return DatasetProfile(
        file_name=file_name,
        row_count=int(df.shape[0]),
        column_count=int(df.shape[1]),
        columns=[str(column) for column in df.columns],
        dtypes={str(column): str(dtype) for column, dtype in df.dtypes.items()},
        missing_values={str(column): int(value) for column, value in missing_values.items()},
        missing_percentage={
            str(column): float(value) for column, value in missing_percentage.items()
        },
        numeric_columns=numeric_profiles,
        categorical_columns=categorical_profiles,
        boolean_columns=boolean_profiles,
        datetime_columns=datetime_profiles,
        profiling_limits=ProfilingLimits(max_categorical_values=max_categorical_values),
    )


def _is_numeric_series(series: pd.Series[Any]) -> bool:
    """Return whether a series should be summarized numerically."""

    return bool(is_numeric_dtype(series) and not is_bool_dtype(series))


def _is_categorical_series(series: pd.Series[Any]) -> bool:
    """Return whether a series should be summarized categorically."""

    return bool(
        is_object_dtype(series) or is_string_dtype(series) or str(series.dtype) == "category"
    )


def _is_boolean_series(series: pd.Series[Any]) -> bool:
    """Return whether a series should be summarized as boolean."""

    if is_bool_dtype(series):
        return True

    non_null_values = [str(value).strip().lower() for value in series.dropna().tolist()]
    if not non_null_values:
        return False

    valid_boolean_values = {"true", "false", "yes", "no", "0", "1"}
    return all(value in valid_boolean_values for value in non_null_values)


def _coerce_datetime_series(series: pd.Series[Any]) -> pd.Series[Any] | None:
    """Conservatively coerce a series to datetimes when it looks datetime-like."""

    if is_datetime64_any_dtype(series):
        return series

    if not (is_object_dtype(series) or is_string_dtype(series)):
        return None

    non_null = series.dropna()
    if non_null.empty:
        return None

    values = [str(value).strip() for value in non_null.tolist()]
    if not _has_datetime_markers(values):
        return None

    converted = pd.to_datetime(non_null, errors="coerce")
    if converted.isna().any():
        return None

    full_series = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    full_series.loc[non_null.index] = converted
    return full_series


def _has_datetime_markers(values: Iterable[str]) -> bool:
    """Check for common datetime-like separators before attempting coercion."""

    return any(any(marker in value for marker in ("-", "/", ":", "T")) for value in values)


def _build_numeric_profile(column_name: str, series: pd.Series[Any]) -> NumericColumnProfile:
    """Build numeric summary statistics."""

    numeric_series = pd.to_numeric(series, errors="coerce")
    quantiles = numeric_series.quantile([0.25, 0.5, 0.75])
    return NumericColumnProfile(
        column=column_name,
        count=int(numeric_series.count()),
        mean=_to_optional_float(numeric_series.mean()),
        std=_to_optional_float(numeric_series.std()),
        min=_to_optional_float(numeric_series.min()),
        q25=_to_optional_float(quantiles.loc[0.25]),
        median=_to_optional_float(quantiles.loc[0.5]),
        q75=_to_optional_float(quantiles.loc[0.75]),
        max=_to_optional_float(numeric_series.max()),
    )


def _build_categorical_profile(
    column_name: str,
    series: pd.Series[Any],
    max_values: int,
) -> CategoricalColumnProfile:
    """Build a bounded categorical summary."""

    normalized = series.dropna().astype(str)
    value_counts = normalized.value_counts()
    top_values = [
        ValueFrequency(value=str(index), count=int(count))
        for index, count in value_counts.head(max_values).items()
    ]
    top_value = top_values[0].value if top_values else None
    top_value_frequency = top_values[0].count if top_values else 0

    return CategoricalColumnProfile(
        column=column_name,
        count=int(normalized.count()),
        unique_count=int(normalized.nunique()),
        top_value=top_value,
        top_value_frequency=top_value_frequency,
        top_values=top_values,
    )


def _build_boolean_profile(column_name: str, series: pd.Series[Any]) -> BooleanColumnProfile:
    """Build a boolean summary using conservative normalization."""

    normalized = series.map(_coerce_boolean)
    true_count = int((normalized == True).sum())  # noqa: E712
    false_count = int((normalized == False).sum())  # noqa: E712
    missing_count = int(normalized.isna().sum())

    return BooleanColumnProfile(
        column=column_name,
        true_count=true_count,
        false_count=false_count,
        missing_count=missing_count,
    )


def _build_datetime_profile(
    column_name: str,
    series: pd.Series[Any],
) -> DatetimeColumnProfile:
    """Build a datetime summary."""

    datetime_series = pd.to_datetime(series, errors="coerce")
    min_value = datetime_series.min()
    max_value = datetime_series.max()
    return DatetimeColumnProfile(
        column=column_name,
        count=int(datetime_series.count()),
        min=min_value.isoformat() if pd.notna(min_value) else None,
        max=max_value.isoformat() if pd.notna(max_value) else None,
    )


def _coerce_boolean(value: object) -> bool | None:
    """Normalize typical boolean-like values."""

    if _is_missing_scalar(value):
        return None
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    return None


def _to_optional_float(value: object) -> float | None:
    """Convert pandas numeric scalars into optional floats."""

    if _is_missing_scalar(value):
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, int | float):
        return float(value)
    return float(cast(Any, value))


def _is_missing_scalar(value: object) -> bool:
    """Return whether a scalar should be treated as missing."""

    if value is None or value is pd.NA or value is pd.NaT:
        return True
    return isinstance(value, float) and math.isnan(value)
