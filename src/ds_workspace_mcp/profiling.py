from __future__ import annotations

import math
from collections.abc import Iterable
from itertools import combinations
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

_MAX_HISTOGRAM_BINS = 10
_MAX_CANDIDATE_KEY_COLUMNS = 12
_MAX_CANDIDATE_KEY_COMBINATIONS = 25
_NEAR_CONSTANT_RATIO = 0.95
_IDENTIFIER_UNIQUENESS_RATIO = 0.95
_FREE_TEXT_AVERAGE_LENGTH = 30
_FREE_TEXT_MAX_LENGTH = 80


class ValueFrequency(BaseModel):
    """A bounded frequency summary for categorical-like data."""

    value: str
    count: int = Field(ge=0)


class ProfileHeuristicSignal(BaseModel):
    """Advisory profile heuristic with explicit evidence metadata."""

    signal: str
    reason: str
    severity: str
    confidence: str


class ColumnQualitySignal(BaseModel):
    """Dataset-level advisory signal tied to one column."""

    column: str
    signal: str
    reason: str
    severity: str
    confidence: str


class NumericHistogramBin(BaseModel):
    """One bounded histogram bin for numeric profiling."""

    lower_bound: float
    upper_bound: float
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
    iqr: float | None
    robust_spread: float | None
    histogram: list[NumericHistogramBin]
    iqr_outlier_count: int = Field(ge=0)
    z_score_outlier_count: int | None
    skewness: float | None
    quality_signals: list[ProfileHeuristicSignal] = Field(default_factory=list)


class CategoricalColumnProfile(BaseModel):
    """Summary statistics for a categorical column."""

    column: str
    count: int = Field(ge=0)
    unique_count: int = Field(ge=0)
    top_value: str | None
    top_value_frequency: int = Field(ge=0)
    top_values: list[ValueFrequency]
    rare_category_count: int = Field(ge=0)
    rare_category_mass: float = Field(ge=0.0, le=1.0)
    entropy: float | None
    normalized_entropy: float | None
    quality_signals: list[ProfileHeuristicSignal] = Field(default_factory=list)


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
    max_histogram_bins: int = Field(default=_MAX_HISTOGRAM_BINS, ge=1)
    max_candidate_key_columns: int = Field(default=_MAX_CANDIDATE_KEY_COLUMNS, ge=1)
    max_candidate_key_combinations: int = Field(default=_MAX_CANDIDATE_KEY_COMBINATIONS, ge=1)


class CandidateKeyProfile(BaseModel):
    """Bounded candidate key diagnostic."""

    columns: list[str]
    uniqueness_ratio: float = Field(ge=0.0, le=1.0)
    missing_count: int = Field(ge=0)
    reason: str
    confidence: str


class DatasetQualityDiagnostics(BaseModel):
    """Dataset-level data-quality diagnostics."""

    duplicate_row_count: int = Field(ge=0)
    duplicate_row_percentage: float = Field(ge=0.0, le=100.0)
    candidate_keys: list[CandidateKeyProfile]
    empty_columns: list[ColumnQualitySignal]
    one_value_columns: list[ColumnQualitySignal]
    probable_free_text_columns: list[ColumnQualitySignal]
    possible_identifier_columns: list[ColumnQualitySignal]


def _empty_dataset_quality_diagnostics() -> DatasetQualityDiagnostics:
    return DatasetQualityDiagnostics(
        duplicate_row_count=0,
        duplicate_row_percentage=0.0,
        candidate_keys=[],
        empty_columns=[],
        one_value_columns=[],
        probable_free_text_columns=[],
        possible_identifier_columns=[],
    )


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
    data_quality: DatasetQualityDiagnostics = Field(
        default_factory=_empty_dataset_quality_diagnostics
    )
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
        data_quality=_build_dataset_quality_diagnostics(df),
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
    clean = numeric_series.dropna()
    quantiles = clean.quantile([0.25, 0.5, 0.75]) if not clean.empty else None
    q25 = _quantile_value(quantiles, 0.25)
    median = _quantile_value(quantiles, 0.5)
    q75 = _quantile_value(quantiles, 0.75)
    iqr = _optional_difference(q75, q25)
    std = _to_optional_float(clean.std()) if not clean.empty else None
    mean = _to_optional_float(clean.mean()) if not clean.empty else None
    iqr_outlier_count = _iqr_outlier_count(clean, q25=q25, q75=q75, iqr=iqr)
    z_score_outlier_count = _z_score_outlier_count(clean, mean=mean, std=std)
    return NumericColumnProfile(
        column=column_name,
        count=int(clean.count()),
        mean=mean,
        std=std,
        min=_to_optional_float(clean.min()) if not clean.empty else None,
        q25=q25,
        median=median,
        q75=q75,
        max=_to_optional_float(clean.max()) if not clean.empty else None,
        iqr=iqr,
        robust_spread=(iqr / 1.349) if iqr is not None else None,
        histogram=_build_numeric_histogram(clean),
        iqr_outlier_count=iqr_outlier_count,
        z_score_outlier_count=z_score_outlier_count,
        skewness=_numeric_skewness(clean, std=std),
        quality_signals=_numeric_quality_signals(
            clean,
            iqr_outlier_count=iqr_outlier_count,
            z_score_outlier_count=z_score_outlier_count,
        ),
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
    rare_count, rare_mass = _rare_category_metrics(value_counts)
    entropy = _entropy(value_counts)

    return CategoricalColumnProfile(
        column=column_name,
        count=int(normalized.count()),
        unique_count=int(normalized.nunique()),
        top_value=top_value,
        top_value_frequency=top_value_frequency,
        top_values=top_values,
        rare_category_count=rare_count,
        rare_category_mass=rare_mass,
        entropy=entropy,
        normalized_entropy=_normalized_entropy(entropy, unique_count=int(normalized.nunique())),
        quality_signals=_categorical_quality_signals(value_counts),
    )


def _build_dataset_quality_diagnostics(df: pd.DataFrame) -> DatasetQualityDiagnostics:
    """Build bounded dataset-level diagnostics."""

    row_count = int(df.shape[0])
    duplicate_count = int(df.duplicated().sum()) if row_count else 0
    return DatasetQualityDiagnostics(
        duplicate_row_count=duplicate_count,
        duplicate_row_percentage=_percentage(duplicate_count, row_count),
        candidate_keys=_candidate_keys(df),
        empty_columns=_empty_column_signals(df),
        one_value_columns=_one_value_column_signals(df),
        probable_free_text_columns=_free_text_column_signals(df),
        possible_identifier_columns=_identifier_column_signals(df),
    )


def _build_numeric_histogram(series: pd.Series[Any]) -> list[NumericHistogramBin]:
    """Build a compact histogram with a hard bin cap."""

    if series.empty:
        return []

    minimum = _to_optional_float(series.min())
    maximum = _to_optional_float(series.max())
    if minimum is None or maximum is None:
        return []
    if math.isclose(minimum, maximum):
        return [NumericHistogramBin(lower_bound=minimum, upper_bound=maximum, count=len(series))]

    bin_count = min(_MAX_HISTOGRAM_BINS, max(1, int(series.nunique())))
    intervals = pd.cut(series, bins=bin_count, include_lowest=True)
    counts = intervals.value_counts(sort=False)
    histogram: list[NumericHistogramBin] = []
    for interval, count in counts.items():
        interval_value = cast(Any, interval)
        histogram.append(
            NumericHistogramBin(
                lower_bound=float(interval_value.left),
                upper_bound=float(interval_value.right),
                count=int(count),
            )
        )
    return histogram


def _iqr_outlier_count(
    series: pd.Series[Any],
    *,
    q25: float | None,
    q75: float | None,
    iqr: float | None,
) -> int:
    if series.empty or q25 is None or q75 is None or iqr is None or iqr <= 0:
        return 0
    lower = q25 - (1.5 * iqr)
    upper = q75 + (1.5 * iqr)
    return int(((series < lower) | (series > upper)).sum())


def _z_score_outlier_count(
    series: pd.Series[Any],
    *,
    mean: float | None,
    std: float | None,
) -> int | None:
    if len(series) < 30 or mean is None or std is None or std <= 0:
        return None
    return int((((series - mean) / std).abs() > 3.0).sum())


def _numeric_skewness(series: pd.Series[Any], *, std: float | None) -> float | None:
    if len(series) < 3 or std is None or std <= 0:
        return None
    return _to_optional_float(series.skew())


def _numeric_quality_signals(
    series: pd.Series[Any],
    *,
    iqr_outlier_count: int,
    z_score_outlier_count: int | None,
) -> list[ProfileHeuristicSignal]:
    signals: list[ProfileHeuristicSignal] = []
    non_null_count = len(series)
    if non_null_count == 0:
        return signals

    unique_count = int(series.nunique())
    if unique_count <= 1:
        signals.append(
            ProfileHeuristicSignal(
                signal="constant",
                severity="medium",
                confidence="high",
                reason="All non-missing numeric values are identical.",
            )
        )
    elif _top_value_ratio(series) >= _NEAR_CONSTANT_RATIO:
        signals.append(
            ProfileHeuristicSignal(
                signal="near_constant",
                severity="low",
                confidence="medium",
                reason=f"At least {_NEAR_CONSTANT_RATIO:.0%} of non-missing values are identical.",
            )
        )

    if iqr_outlier_count > 0:
        signals.append(
            ProfileHeuristicSignal(
                signal="iqr_outliers",
                severity="low",
                confidence="medium",
                reason=f"{iqr_outlier_count} values fall outside the 1.5x IQR bounds.",
            )
        )

    if z_score_outlier_count is not None and z_score_outlier_count > 0:
        signals.append(
            ProfileHeuristicSignal(
                signal="z_score_outliers",
                severity="low",
                confidence="medium",
                reason=f"{z_score_outlier_count} values have absolute z-score greater than 3.",
            )
        )

    return signals


def _rare_category_metrics(value_counts: pd.Series[Any]) -> tuple[int, float]:
    total = int(value_counts.sum())
    if total <= 0:
        return 0, 0.0
    rare_threshold = max(1, math.floor(total * 0.01))
    rare_counts = value_counts[value_counts <= rare_threshold]
    rare_category_count = int(len(rare_counts))
    rare_mass = float(rare_counts.sum() / total)
    return rare_category_count, rare_mass


def _entropy(value_counts: pd.Series[Any]) -> float | None:
    total = int(value_counts.sum())
    if total <= 0:
        return None
    entropy = 0.0
    for count in value_counts.tolist():
        probability = float(count / total)
        if probability > 0:
            entropy -= probability * math.log(probability, 2)
    return entropy


def _normalized_entropy(entropy: float | None, *, unique_count: int) -> float | None:
    if entropy is None:
        return None
    if unique_count <= 1:
        return 0.0
    return entropy / math.log(unique_count, 2)


def _categorical_quality_signals(value_counts: pd.Series[Any]) -> list[ProfileHeuristicSignal]:
    signals: list[ProfileHeuristicSignal] = []
    total = int(value_counts.sum())
    if total <= 0:
        return signals

    unique_count = int(len(value_counts))
    if unique_count <= 1:
        signals.append(
            ProfileHeuristicSignal(
                signal="constant",
                severity="medium",
                confidence="high",
                reason="All non-missing categorical values are identical.",
            )
        )
    elif float(value_counts.iloc[0] / total) >= _NEAR_CONSTANT_RATIO:
        signals.append(
            ProfileHeuristicSignal(
                signal="near_constant",
                severity="low",
                confidence="medium",
                reason=(
                    "The most frequent value covers at least "
                    f"{_NEAR_CONSTANT_RATIO:.0%} of non-missing rows."
                ),
            )
        )

    rare_count, rare_mass = _rare_category_metrics(value_counts)
    if rare_count > 0 and rare_mass >= 0.1:
        signals.append(
            ProfileHeuristicSignal(
                signal="rare_category_mass",
                severity="low",
                confidence="medium",
                reason=(
                    f"{rare_count} rare categories account for {rare_mass:.1%} of non-missing rows."
                ),
            )
        )

    return signals


def _empty_column_signals(df: pd.DataFrame) -> list[ColumnQualitySignal]:
    signals: list[ColumnQualitySignal] = []
    for column in df.columns:
        if int(df[column].count()) == 0:
            signals.append(
                ColumnQualitySignal(
                    column=str(column),
                    signal="empty_column",
                    severity="high",
                    confidence="high",
                    reason="Column has no non-missing values.",
                )
            )
    return signals


def _one_value_column_signals(df: pd.DataFrame) -> list[ColumnQualitySignal]:
    signals: list[ColumnQualitySignal] = []
    for column in df.columns:
        series = df[column].dropna()
        if not series.empty and int(series.astype(str).nunique()) == 1:
            signals.append(
                ColumnQualitySignal(
                    column=str(column),
                    signal="one_effective_value",
                    severity="medium",
                    confidence="high",
                    reason="Column has exactly one distinct non-missing value.",
                )
            )
    return signals


def _free_text_column_signals(df: pd.DataFrame) -> list[ColumnQualitySignal]:
    signals: list[ColumnQualitySignal] = []
    for column in df.columns:
        series = df[column]
        if not _is_categorical_series(series):
            continue
        normalized = series.dropna().astype(str)
        if normalized.empty:
            continue
        lengths = normalized.str.len()
        average_length = float(lengths.mean())
        max_length = int(lengths.max())
        unique_ratio = int(normalized.nunique()) / max(len(normalized), 1)
        if unique_ratio >= 0.5 and (
            average_length >= _FREE_TEXT_AVERAGE_LENGTH or max_length >= _FREE_TEXT_MAX_LENGTH
        ):
            signals.append(
                ColumnQualitySignal(
                    column=str(column),
                    signal="probable_free_text",
                    severity="low",
                    confidence="medium",
                    reason=(
                        "Column has high text uniqueness with long average or maximum value length."
                    ),
                )
            )
    return signals


def _identifier_column_signals(df: pd.DataFrame) -> list[ColumnQualitySignal]:
    signals: list[ColumnQualitySignal] = []
    row_count = int(df.shape[0])
    if row_count == 0:
        return signals
    for column in df.columns:
        series = df[column]
        non_null_count = int(series.count())
        if non_null_count == 0:
            continue
        unique_count = int(series.dropna().astype(str).nunique())
        uniqueness_ratio = unique_count / max(non_null_count, 1)
        completeness_ratio = non_null_count / row_count
        name_hint = any(token in str(column).lower() for token in ("id", "uuid", "key"))
        if (
            uniqueness_ratio >= _IDENTIFIER_UNIQUENESS_RATIO
            and completeness_ratio >= _IDENTIFIER_UNIQUENESS_RATIO
        ):
            confidence = "high" if name_hint or math.isclose(uniqueness_ratio, 1.0) else "medium"
            signals.append(
                ColumnQualitySignal(
                    column=str(column),
                    signal="possible_identifier",
                    severity="low",
                    confidence=confidence,
                    reason="Column is nearly unique and nearly complete across rows.",
                )
            )
    return signals


def _candidate_keys(df: pd.DataFrame) -> list[CandidateKeyProfile]:
    row_count = int(df.shape[0])
    if row_count == 0:
        return []

    candidates: list[CandidateKeyProfile] = []
    columns = [(str(column), column) for column in df.columns]
    for column_name, column_key in columns[:_MAX_CANDIDATE_KEY_COLUMNS]:
        series = df[column_key]
        missing_count = int(series.isna().sum())
        unique_count = int(series.dropna().astype(str).nunique())
        if missing_count == 0 and unique_count == row_count:
            candidates.append(
                CandidateKeyProfile(
                    columns=[column_name],
                    uniqueness_ratio=1.0,
                    missing_count=0,
                    confidence="high",
                    reason="Single column is complete and unique across all rows.",
                )
            )

    eligible_columns = [
        (column_name, column_key)
        for column_name, column_key in columns[:_MAX_CANDIDATE_KEY_COLUMNS]
        if int(df[column_key].count()) == row_count
        and int(df[column_key].astype(str).nunique()) > 1
    ]
    for pair_index, (left_column, right_column) in enumerate(combinations(eligible_columns, 2)):
        if pair_index >= _MAX_CANDIDATE_KEY_COMBINATIONS:
            break
        left_name, left_key = left_column
        right_name, right_key = right_column
        unique_pairs = int(df[[left_key, right_key]].astype(str).drop_duplicates().shape[0])
        if unique_pairs == row_count:
            candidates.append(
                CandidateKeyProfile(
                    columns=[left_name, right_name],
                    uniqueness_ratio=1.0,
                    missing_count=0,
                    confidence="medium",
                    reason=(
                        "Two-column combination is complete and unique within bounded key search."
                    ),
                )
            )
    return candidates[:_MAX_CANDIDATE_KEY_COMBINATIONS]


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


def _quantile_value(quantiles: pd.Series[Any] | None, quantile: float) -> float | None:
    if quantiles is None:
        return None
    return _to_optional_float(quantiles.loc[quantile])


def _optional_difference(right: float | None, left: float | None) -> float | None:
    if right is None or left is None:
        return None
    return right - left


def _top_value_ratio(series: pd.Series[Any]) -> float:
    if series.empty:
        return 0.0
    value_counts = series.value_counts()
    if value_counts.empty:
        return 0.0
    return float(value_counts.iloc[0] / len(series))


def _percentage(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((count / total) * 100, 2)


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
