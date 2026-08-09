from __future__ import annotations

from collections import Counter
from typing import Any, Literal, cast

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype
from pydantic import BaseModel, Field

from ds_workspace_mcp.core import read_csv_dataset

MIN_HISTORY_POINTS = 10
APPROXIMATE_FREQUENCY_SUPPORT_THRESHOLD = 0.8
MAX_GROUP_SUMMARIES = 20

FrequencyKind = Literal[
    "regular",
    "approximately_regular",
    "irregular",
    "insufficient_data",
    "heterogeneous",
]


class FrequencyInferenceResult(BaseModel):
    """Structured frequency inference for one time series."""

    frequency: str | None = None
    frequency_kind: FrequencyKind
    confidence: float = Field(ge=0.0, le=1.0)
    support_ratio: float = Field(ge=0.0, le=1.0)
    candidate_interval: str | None = None
    is_regular: bool
    is_irregular: bool
    missing_interval_count: int = Field(ge=0)


class TimeSeriesWarning(BaseModel):
    """A warning about time-series dataset readiness."""

    warning_type: str
    description: str
    group: str | None = None


class GroupTimeSeriesSummary(BaseModel):
    """Summary metrics for one time-series group."""

    group: str
    row_count: int = Field(ge=0)
    duplicate_timestamps: int = Field(ge=0)
    missing_intervals: int = Field(ge=0)
    inferred_frequency: str | None = None
    frequency: FrequencyInferenceResult


class TimeSeriesValidationResult(BaseModel):
    """Structured readiness summary for time-series datasets."""

    file_name: str
    time_column: str
    target_column: str | None = None
    group_column: str | None = None
    row_count: int = Field(ge=0)
    parsed_timestamp_count: int = Field(ge=0)
    duplicate_timestamps: int = Field(ge=0)
    is_sorted: bool
    inferred_frequency: str | None = None
    missing_intervals: int = Field(ge=0)
    frequency: FrequencyInferenceResult
    missing_target_values: int | None = None
    group_summaries: list[GroupTimeSeriesSummary] = Field(default_factory=list)
    warnings: list[TimeSeriesWarning] = Field(default_factory=list)


def validate_time_series_dataset(
    file_name: str,
    time_column: str,
    target_column: str | None = None,
    group_column: str | None = None,
) -> TimeSeriesValidationResult:
    """Validate whether a dataset looks suitable for time-series modeling."""

    df = read_csv_dataset(file_name)
    _validate_column_exists(df, time_column)
    if target_column is not None:
        _validate_column_exists(df, target_column)
    if group_column is not None:
        _validate_column_exists(df, group_column)

    timestamps = _coerce_timestamps(df[time_column], time_column)
    parsed_timestamp_count = int(timestamps.notna().sum())
    warnings: list[TimeSeriesWarning] = []

    if parsed_timestamp_count != len(df):
        warnings.append(
            TimeSeriesWarning(
                warning_type="unparseable_timestamps",
                description=(
                    f"Time column contains {len(df) - parsed_timestamp_count} unparseable values."
                ),
            )
        )

    aligned = df.copy()
    aligned[time_column] = timestamps
    aligned = aligned.dropna(subset=[time_column])

    if group_column is None:
        duplicate_timestamps = int(aligned[time_column].duplicated().sum())
        is_sorted = bool(aligned[time_column].is_monotonic_increasing)
        frequency = _infer_frequency(aligned[time_column])
        inferred_frequency = frequency.frequency
        missing_intervals = frequency.missing_interval_count
        group_summaries: list[GroupTimeSeriesSummary] = []
        warnings.extend(
            _build_series_warnings(
                duplicate_timestamps=duplicate_timestamps,
                is_sorted=is_sorted,
                frequency=frequency,
                row_count=len(aligned),
                group=None,
            )
        )
    else:
        group_summaries = []
        duplicate_timestamps = 0
        missing_intervals = 0
        sorted_flags: list[bool] = []
        group_frequencies: list[FrequencyInferenceResult] = []

        for group_value, group_df in aligned.groupby(group_column, sort=True):
            group_timestamps = group_df[time_column]
            group_duplicates = int(group_timestamps.duplicated().sum())
            group_sorted = bool(group_timestamps.is_monotonic_increasing)
            group_frequency = _infer_frequency(group_timestamps)
            group_missing_intervals = group_frequency.missing_interval_count

            duplicate_timestamps += group_duplicates
            missing_intervals += group_missing_intervals
            sorted_flags.append(group_sorted)
            group_frequencies.append(group_frequency)

            group_label = str(group_value)
            if len(group_summaries) < MAX_GROUP_SUMMARIES:
                group_summaries.append(
                    GroupTimeSeriesSummary(
                        group=group_label,
                        row_count=len(group_df),
                        duplicate_timestamps=group_duplicates,
                        missing_intervals=group_missing_intervals,
                        inferred_frequency=group_frequency.frequency,
                        frequency=group_frequency,
                    )
                )
            warnings.extend(
                _build_series_warnings(
                    duplicate_timestamps=group_duplicates,
                    is_sorted=group_sorted,
                    frequency=group_frequency,
                    row_count=len(group_df),
                    group=group_label,
                )
            )

        is_sorted = all(sorted_flags) if sorted_flags else True
        frequency = _combine_group_frequencies(group_frequencies)
        inferred_frequency = frequency.frequency
        if frequency.frequency_kind == "heterogeneous":
            warnings.append(
                TimeSeriesWarning(
                    warning_type="heterogeneous_frequencies",
                    description="Grouped time series contain different inferred frequencies.",
                )
            )

    missing_target_values: int | None = None
    if target_column is not None:
        missing_target_values = int(df[target_column].isna().sum())
        if missing_target_values > 0:
            warnings.append(
                TimeSeriesWarning(
                    warning_type="missing_target_values",
                    description=f"Target column contains {missing_target_values} missing values.",
                )
            )

    if len(aligned) < MIN_HISTORY_POINTS:
        warnings.append(
            TimeSeriesWarning(
                warning_type="insufficient_history",
                description=(
                    f"Dataset has {len(aligned)} valid timestamped rows; at least "
                    f"{MIN_HISTORY_POINTS} are recommended for baseline forecasting."
                ),
            )
        )

    return TimeSeriesValidationResult(
        file_name=file_name,
        time_column=time_column,
        target_column=target_column,
        group_column=group_column,
        row_count=len(df),
        parsed_timestamp_count=parsed_timestamp_count,
        duplicate_timestamps=duplicate_timestamps,
        is_sorted=is_sorted,
        inferred_frequency=inferred_frequency,
        missing_intervals=missing_intervals,
        frequency=frequency,
        missing_target_values=missing_target_values,
        group_summaries=group_summaries,
        warnings=warnings,
    )


def _validate_column_exists(df: pd.DataFrame, column_name: str) -> None:
    """Raise when a required column is missing."""

    if column_name not in df.columns:
        raise ValueError(f"Unknown column: {column_name}")


def _coerce_timestamps(series: pd.Series[Any], column_name: str) -> pd.Series[Any]:
    """Parse timestamps conservatively."""

    if is_datetime64_any_dtype(series):
        return series

    parsed = pd.to_datetime(series, errors="coerce")
    if parsed.isna().all():
        raise ValueError(f"time_column `{column_name}` could not be parsed as timestamps.")
    return parsed


def _infer_frequency(timestamps: pd.Series[Any]) -> FrequencyInferenceResult:
    """Infer regularity from sorted unique timestamps without manufacturing frequency."""

    cleaned = timestamps.dropna().sort_values().drop_duplicates()
    if len(cleaned) < 3:
        return FrequencyInferenceResult(
            frequency=None,
            frequency_kind="insufficient_data",
            confidence=0.0,
            support_ratio=0.0,
            candidate_interval=None,
            is_regular=False,
            is_irregular=False,
            missing_interval_count=0,
        )

    diffs = cleaned.diff().dropna()
    if diffs.empty:
        return FrequencyInferenceResult(
            frequency=None,
            frequency_kind="insufficient_data",
            confidence=0.0,
            support_ratio=0.0,
            candidate_interval=None,
            is_regular=False,
            is_irregular=False,
            missing_interval_count=0,
        )

    inferred_alias = pd.infer_freq(cleaned)
    unique_diffs = diffs.unique()
    if len(unique_diffs) == 1:
        interval = _format_timedelta(cast(pd.Timedelta, unique_diffs[0]))
        return FrequencyInferenceResult(
            frequency=interval,
            frequency_kind="regular",
            confidence=1.0,
            support_ratio=1.0,
            candidate_interval=interval,
            is_regular=True,
            is_irregular=False,
            missing_interval_count=0,
        )

    if inferred_alias is not None:
        return FrequencyInferenceResult(
            frequency=inferred_alias,
            frequency_kind="regular",
            confidence=1.0,
            support_ratio=1.0,
            candidate_interval=inferred_alias,
            is_regular=True,
            is_irregular=False,
            missing_interval_count=0,
        )

    dominant_diff, support_count = Counter(diffs).most_common(1)[0]
    candidate_delta = cast(pd.Timedelta, dominant_diff)
    support_ratio = support_count / len(diffs)
    candidate_interval = _format_timedelta(candidate_delta)
    if support_ratio >= APPROXIMATE_FREQUENCY_SUPPORT_THRESHOLD and candidate_interval is not None:
        missing_interval_count = _count_missing_intervals_for_delta(diffs, candidate_delta)
        return FrequencyInferenceResult(
            frequency=candidate_interval,
            frequency_kind="approximately_regular",
            confidence=float(support_ratio),
            support_ratio=float(support_ratio),
            candidate_interval=candidate_interval,
            is_regular=False,
            is_irregular=False,
            missing_interval_count=missing_interval_count,
        )

    return FrequencyInferenceResult(
        frequency=None,
        frequency_kind="irregular",
        confidence=float(support_ratio),
        support_ratio=float(support_ratio),
        candidate_interval=candidate_interval,
        is_regular=False,
        is_irregular=True,
        missing_interval_count=0,
    )


def _count_missing_intervals_for_delta(diffs: pd.Series[Any], expected_delta: pd.Timedelta) -> int:
    """Count missing intervals only after an expected fixed interval is established."""

    missing_intervals = 0
    for raw_diff in diffs:
        diff = cast(pd.Timedelta, raw_diff)
        if diff > expected_delta:
            ratio = int(diff / expected_delta)
            if ratio > 1:
                missing_intervals += ratio - 1
    return missing_intervals


def _format_timedelta(delta: pd.Timedelta) -> str | None:
    """Format a timedelta into a compact human-readable frequency."""

    total_seconds = int(delta.total_seconds())
    if total_seconds <= 0:
        return None
    if total_seconds % 86_400 == 0:
        days = total_seconds // 86_400
        return f"{days}D"
    if total_seconds % 3_600 == 0:
        hours = total_seconds // 3_600
        return f"{hours}H"
    if total_seconds % 60 == 0:
        minutes = total_seconds // 60
        return f"{minutes}min"
    return f"{total_seconds}s"


def _build_series_warnings(
    duplicate_timestamps: int,
    is_sorted: bool,
    frequency: FrequencyInferenceResult,
    row_count: int,
    group: str | None,
) -> list[TimeSeriesWarning]:
    """Build warnings for one overall or grouped time series."""

    warnings: list[TimeSeriesWarning] = []
    prefix = f"Group `{group}`" if group is not None else "Dataset"

    if duplicate_timestamps > 0:
        warnings.append(
            TimeSeriesWarning(
                warning_type="duplicate_timestamps",
                description=f"{prefix} contains {duplicate_timestamps} duplicate timestamps.",
                group=group,
            )
        )

    if not is_sorted:
        warnings.append(
            TimeSeriesWarning(
                warning_type="unsorted_timestamps",
                description=f"{prefix} timestamps are not sorted in ascending order.",
                group=group,
            )
        )

    if frequency.frequency_kind == "irregular":
        warnings.append(
            TimeSeriesWarning(
                warning_type="irregular_frequency",
                description=f"{prefix} frequency appears irregular.",
                group=group,
            )
        )
    elif frequency.frequency is None and row_count >= 3:
        warnings.append(
            TimeSeriesWarning(
                warning_type="unresolved_frequency",
                description=f"{prefix} frequency could not be inferred confidently.",
                group=group,
            )
        )

    if frequency.missing_interval_count > 0:
        warnings.append(
            TimeSeriesWarning(
                warning_type="missing_intervals",
                description=(
                    f"{prefix} appears to have "
                    f"{frequency.missing_interval_count} missing intervals."
                ),
                group=group,
            )
        )

    return warnings


def _combine_group_frequencies(
    frequencies: list[FrequencyInferenceResult],
) -> FrequencyInferenceResult:
    """Combine per-group frequency results without hiding heterogeneity."""

    if not frequencies:
        return FrequencyInferenceResult(
            frequency=None,
            frequency_kind="insufficient_data",
            confidence=0.0,
            support_ratio=0.0,
            candidate_interval=None,
            is_regular=False,
            is_irregular=False,
            missing_interval_count=0,
        )

    established = [
        frequency
        for frequency in frequencies
        if frequency.frequency_kind in {"regular", "approximately_regular"}
    ]
    unique_established = {
        (frequency.frequency, frequency.frequency_kind) for frequency in established
    }
    if len(established) == len(frequencies) and len(unique_established) == 1:
        first = established[0]
        return FrequencyInferenceResult(
            frequency=first.frequency,
            frequency_kind=first.frequency_kind,
            confidence=min(frequency.confidence for frequency in frequencies),
            support_ratio=min(frequency.support_ratio for frequency in frequencies),
            candidate_interval=first.candidate_interval,
            is_regular=first.frequency_kind == "regular",
            is_irregular=False,
            missing_interval_count=sum(
                frequency.missing_interval_count for frequency in frequencies
            ),
        )

    if len(unique_established) > 1 or (established and len(established) != len(frequencies)):
        return FrequencyInferenceResult(
            frequency=None,
            frequency_kind="heterogeneous",
            confidence=0.0,
            support_ratio=0.0,
            candidate_interval=None,
            is_regular=False,
            is_irregular=True,
            missing_interval_count=sum(
                frequency.missing_interval_count for frequency in frequencies
            ),
        )

    if all(frequency.frequency_kind == "insufficient_data" for frequency in frequencies):
        return FrequencyInferenceResult(
            frequency=None,
            frequency_kind="insufficient_data",
            confidence=0.0,
            support_ratio=0.0,
            candidate_interval=None,
            is_regular=False,
            is_irregular=False,
            missing_interval_count=0,
        )

    return FrequencyInferenceResult(
        frequency=None,
        frequency_kind="irregular",
        confidence=max(frequency.confidence for frequency in frequencies),
        support_ratio=max(frequency.support_ratio for frequency in frequencies),
        candidate_interval=None,
        is_regular=False,
        is_irregular=True,
        missing_interval_count=0,
    )
