from __future__ import annotations

from collections import Counter
from typing import Any, cast

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype
from pydantic import BaseModel, Field

from ds_workspace_mcp.core import read_csv_dataset

MIN_HISTORY_POINTS = 10


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
        inferred_frequency = _infer_frequency(aligned[time_column])
        missing_intervals = _count_missing_intervals(aligned[time_column], inferred_frequency)
        group_summaries: list[GroupTimeSeriesSummary] = []
        warnings.extend(
            _build_series_warnings(
                duplicate_timestamps=duplicate_timestamps,
                is_sorted=is_sorted,
                missing_intervals=missing_intervals,
                inferred_frequency=inferred_frequency,
                row_count=len(aligned),
                group=None,
            )
        )
    else:
        group_summaries = []
        duplicate_timestamps = 0
        missing_intervals = 0
        sorted_flags: list[bool] = []
        inferred_frequencies: list[str] = []

        for group_value, group_df in aligned.groupby(group_column, sort=True):
            group_timestamps = group_df[time_column]
            group_duplicates = int(group_timestamps.duplicated().sum())
            group_sorted = bool(group_timestamps.is_monotonic_increasing)
            group_frequency = _infer_frequency(group_timestamps)
            group_missing_intervals = _count_missing_intervals(group_timestamps, group_frequency)

            duplicate_timestamps += group_duplicates
            missing_intervals += group_missing_intervals
            sorted_flags.append(group_sorted)
            if group_frequency is not None:
                inferred_frequencies.append(group_frequency)

            group_label = str(group_value)
            group_summaries.append(
                GroupTimeSeriesSummary(
                    group=group_label,
                    row_count=len(group_df),
                    duplicate_timestamps=group_duplicates,
                    missing_intervals=group_missing_intervals,
                    inferred_frequency=group_frequency,
                )
            )
            warnings.extend(
                _build_series_warnings(
                    duplicate_timestamps=group_duplicates,
                    is_sorted=group_sorted,
                    missing_intervals=group_missing_intervals,
                    inferred_frequency=group_frequency,
                    row_count=len(group_df),
                    group=group_label,
                )
            )

        is_sorted = all(sorted_flags) if sorted_flags else True
        inferred_frequency = _pick_dominant_frequency(inferred_frequencies)

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


def _infer_frequency(timestamps: pd.Series[Any]) -> str | None:
    """Infer the dominant timestamp step from sorted unique timestamps."""

    cleaned = timestamps.dropna().sort_values().drop_duplicates()
    if len(cleaned) < 3:
        return None

    diffs = cleaned.diff().dropna()
    if diffs.empty:
        return None

    dominant_diff = cast(pd.Timedelta, Counter(diffs).most_common(1)[0][0])
    return _format_timedelta(dominant_diff)


def _count_missing_intervals(timestamps: pd.Series[Any], frequency: str | None) -> int:
    """Count missing intervals against an inferred dominant frequency."""

    if frequency is None:
        return 0

    cleaned = timestamps.dropna().sort_values().drop_duplicates()
    if len(cleaned) < 3:
        return 0

    diffs = cleaned.diff().dropna()
    dominant_diff = cast(pd.Timedelta, Counter(diffs).most_common(1)[0][0])
    missing_intervals = 0
    for raw_diff in diffs:
        diff = cast(pd.Timedelta, raw_diff)
        if diff > dominant_diff:
            ratio = int(diff / dominant_diff)
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
    missing_intervals: int,
    inferred_frequency: str | None,
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

    if inferred_frequency is None and row_count >= 3:
        warnings.append(
            TimeSeriesWarning(
                warning_type="unresolved_frequency",
                description=f"{prefix} frequency could not be inferred confidently.",
                group=group,
            )
        )

    if missing_intervals > 0:
        warnings.append(
            TimeSeriesWarning(
                warning_type="missing_intervals",
                description=f"{prefix} appears to have {missing_intervals} missing intervals.",
                group=group,
            )
        )

    return warnings


def _pick_dominant_frequency(frequencies: list[str]) -> str | None:
    """Pick the most common inferred group frequency."""

    if not frequencies:
        return None
    return Counter(frequencies).most_common(1)[0][0]
