"""Bounded, read-only resampling for numeric time-series datasets."""

from __future__ import annotations

import re
from typing import Any, Literal, cast

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from ds_workspace_mcp.config import get_settings
from ds_workspace_mcp.core import read_dataset_frame
from ds_workspace_mcp.timeseries import _validate_column_exists

ResampleAggregation = Literal["mean", "sum", "min", "max", "median", "count"]
FillMethod = Literal[
    "none",
    "forward_fill",
    "backward_fill",
    "linear_interpolation",
    "zero",
]

DEFAULT_RESAMPLE_PREVIEW_ROWS = 20
MAX_RESAMPLE_GROUPS = 20
MAX_MISSING_INTERVAL_EXAMPLES = 10

_FREQUENCY_PATTERN = re.compile(r"^(?P<multiplier>[1-9][0-9]{0,2})?(?P<unit>MS|ME|min|s|h|H|D|W)$")
_FIXED_UNIT_SECONDS = {"s": 1, "min": 60, "h": 3_600, "D": 86_400, "W": 604_800}


class ResampledTimePoint(BaseModel):
    """A time bucket in a bounded preview, including its data provenance."""

    timestamp: str
    group: str | None = None
    value: float | None = None
    observed_rows: int = Field(ge=0)
    observed_values: int = Field(ge=0)
    filled: bool


class MissingIntervalExample(BaseModel):
    """A timestamp with no source observations in its resampling bucket."""

    timestamp: str
    group: str | None = None


class IntervalFillSuggestion(BaseModel):
    """A fill option and the assumptions required to use it safely."""

    method: FillMethod
    guidance: str
    uses_future_values: bool


class TimeSeriesResamplingResult(BaseModel):
    """Read-only resampling statistics and a capped preview of generated intervals."""

    file_name: str
    time_column: str
    value_column: str
    group_column: str | None = None
    frequency: str
    aggregation: ResampleAggregation
    fill_method: FillMethod
    source_rows: int = Field(ge=0)
    source_missing_values: int = Field(ge=0)
    group_count: int = Field(ge=0)
    generated_intervals: int = Field(ge=0)
    missing_intervals: int = Field(ge=0)
    filled_intervals: int = Field(ge=0)
    preview_truncated: bool
    preview_rows: list[ResampledTimePoint] = Field(default_factory=list)
    missing_interval_examples: list[MissingIntervalExample] = Field(default_factory=list)
    fill_suggestions: list[IntervalFillSuggestion] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def resample_time_series_dataset(
    file_name: str,
    time_column: str,
    value_column: str,
    frequency: str,
    group_column: str | None = None,
    aggregation: ResampleAggregation = "mean",
    fill_method: FillMethod = "none",
    rows: int = DEFAULT_RESAMPLE_PREVIEW_ROWS,
) -> TimeSeriesResamplingResult:
    """Resample a numeric CSV series without modifying or exporting the source.

    All timestamps are normalized to UTC. Missing intervals are buckets without
    observations, not source rows whose numeric value happens to be null. Filling
    affects only missing intervals and is explicitly selected by the caller.

    The number of generated buckets across all groups is bounded by
    ``MCP_MAX_RESAMPLE_INTERVALS``; returned rows are capped separately by
    ``MCP_MAX_PREVIEW_ROWS``.
    """

    settings = get_settings()
    if isinstance(rows, bool) or not isinstance(rows, int):
        raise TypeError("rows must be an integer.")
    if not 1 <= rows <= settings.mcp_max_preview_rows:
        raise ValueError(
            f"rows must be between 1 and {settings.mcp_max_preview_rows} (MCP_MAX_PREVIEW_ROWS)."
        )
    normalized_frequency, multiplier, unit = _validate_frequency(frequency)
    allowed_aggregations = {"mean", "sum", "min", "max", "median", "count"}
    allowed_fill_methods = {"none", "forward_fill", "backward_fill", "linear_interpolation", "zero"}
    if aggregation not in allowed_aggregations:
        raise ValueError(f"aggregation must be one of {sorted(allowed_aggregations)}.")
    if fill_method not in allowed_fill_methods:
        raise ValueError(f"fill_method must be one of {sorted(allowed_fill_methods)}.")
    if time_column == value_column or group_column in {time_column, value_column}:
        raise ValueError("time_column, value_column, and group_column must be distinct.")

    frame = read_dataset_frame(file_name)
    for column in (time_column, value_column, group_column):
        if column is not None:
            _validate_column_exists(frame, column)

    # UTC avoids ambiguous resample buckets around daylight-saving transitions.
    timestamps = pd.to_datetime(frame[time_column], errors="coerce", utc=True)
    invalid_timestamps = int(timestamps.isna().sum())
    if invalid_timestamps:
        raise ValueError(
            f"time_column `{time_column}` contains {invalid_timestamps} invalid timestamps; "
            "resampling requires all timestamps to be parseable."
        )

    original_values = frame[value_column]
    if pd.api.types.is_bool_dtype(original_values.dtype):
        raise ValueError(f"value_column `{value_column}` must contain numeric, non-boolean values.")
    numeric_values = pd.to_numeric(original_values, errors="coerce")
    invalid_values = int((original_values.notna() & numeric_values.isna()).sum())
    if invalid_values:
        raise ValueError(
            f"value_column `{value_column}` contains {invalid_values} nonnumeric values."
        )
    if int(numeric_values.notna().sum()) == 0:
        raise ValueError(f"value_column `{value_column}` has no numeric observations.")
    if not bool(np.isfinite(numeric_values.dropna().to_numpy(dtype=float)).all()):
        raise ValueError(f"value_column `{value_column}` contains non-finite values.")

    aligned = pd.DataFrame({"timestamp": timestamps, "value": numeric_values})
    if group_column is not None:
        if bool(frame[group_column].isna().any()):
            raise ValueError(f"group_column `{group_column}` must not contain missing groups.")
        aligned["group"] = frame[group_column]
        group_count = int(aligned["group"].nunique())
        if group_count > MAX_RESAMPLE_GROUPS:
            raise ValueError(f"resampling supports at most {MAX_RESAMPLE_GROUPS} groups.")
        grouped: list[tuple[str | None, pd.DataFrame]] = [
            (str(group_value), group_frame)
            for group_value, group_frame in aligned.groupby("group", sort=True)
        ]
    else:
        group_count = 1
        grouped = [(None, aligned)]

    total_intervals = 0
    missing_intervals = 0
    filled_intervals = 0
    preview_rows: list[ResampledTimePoint] = []
    missing_examples: list[MissingIntervalExample] = []

    for group, group_frame in grouped:
        timestamp_index = pd.DatetimeIndex(group_frame["timestamp"])
        series = pd.Series(
            group_frame["value"].to_numpy(dtype=float), index=timestamp_index, name="value"
        ).sort_index()
        remaining = settings.mcp_max_resample_intervals - total_intervals
        _check_interval_budget(
            cast(pd.Timestamp, series.index.min()),
            cast(pd.Timestamp, series.index.max()),
            multiplier,
            unit,
            remaining,
            settings.mcp_max_resample_intervals,
        )

        resampler = series.resample(normalized_frequency)
        if aggregation == "sum":
            aggregated = resampler.sum(min_count=1)
        else:
            aggregated = resampler.agg(aggregation)
        observed_rows = resampler.size()
        observed_values = resampler.count()
        if len(aggregated) > remaining:
            raise ValueError(
                "Resampling would generate more than "
                f"{settings.mcp_max_resample_intervals} intervals "
                "(MCP_MAX_RESAMPLE_INTERVALS)."
            )

        # An empty bucket is always missing, including when sum/count yields zero.
        missing_mask = observed_rows.eq(0)
        unfilled = aggregated.mask(missing_mask)
        filled = _fill_missing_intervals(unfilled, missing_mask, fill_method)
        filled_mask = missing_mask & filled.notna()

        total_intervals += len(aggregated)
        missing_intervals += int(missing_mask.sum())
        filled_intervals += int(filled_mask.sum())

        for timestamp in observed_rows.index[missing_mask]:
            if len(missing_examples) >= MAX_MISSING_INTERVAL_EXAMPLES:
                break
            missing_examples.append(
                MissingIntervalExample(
                    timestamp=cast(pd.Timestamp, timestamp).isoformat(), group=group
                )
            )

        # Materialize only the requested preview, even when more buckets exist.
        preview_remaining = rows - len(preview_rows)
        for index in range(min(preview_remaining, len(filled))):
            value = filled.iloc[index]
            preview_rows.append(
                ResampledTimePoint(
                    timestamp=cast(pd.Timestamp, filled.index[index]).isoformat(),
                    group=group,
                    value=float(value) if pd.notna(value) else None,
                    observed_rows=int(observed_rows.iloc[index]),
                    observed_values=int(observed_values.iloc[index]),
                    filled=bool(filled_mask.iloc[index]),
                )
            )

    warnings: list[str] = []
    source_missing_values = int(numeric_values.isna().sum())
    if source_missing_values:
        warnings.append(
            f"{source_missing_values} source numeric values are missing; interval filling "
            "does not impute observed rows with missing values."
        )
    if filled_intervals and fill_method in {"backward_fill", "linear_interpolation"}:
        warnings.append(
            f"{fill_method} uses future observations and can introduce look-ahead leakage "
            "in forecasting."
        )
    if filled_intervals and fill_method == "zero":
        warnings.append("Zero filling assumes an absent interval represents zero activity.")

    return TimeSeriesResamplingResult(
        file_name=file_name,
        time_column=time_column,
        value_column=value_column,
        group_column=group_column,
        frequency=normalized_frequency,
        aggregation=aggregation,
        fill_method=fill_method,
        source_rows=len(frame),
        source_missing_values=source_missing_values,
        group_count=group_count,
        generated_intervals=total_intervals,
        missing_intervals=missing_intervals,
        filled_intervals=filled_intervals,
        preview_truncated=total_intervals > len(preview_rows),
        preview_rows=preview_rows,
        missing_interval_examples=missing_examples,
        fill_suggestions=_fill_suggestions() if missing_intervals else [],
        warnings=warnings,
    )


def _validate_frequency(frequency: str) -> tuple[str, int, str]:
    """Allow only common, explicit, positive pandas frequency aliases."""

    if not isinstance(frequency, str):
        raise TypeError("frequency must be a string.")
    match = _FREQUENCY_PATTERN.fullmatch(frequency)
    if match is None:
        raise ValueError(
            "frequency must be a positive interval such as 1h, 15min, 1D, 1W, "
            "1MS, or 1ME (multiplier at most 999)."
        )
    multiplier = int(match.group("multiplier") or "1")
    unit = match.group("unit").replace("H", "h")
    return f"{multiplier}{unit}", multiplier, unit


def _check_interval_budget(
    start: pd.Timestamp,
    end: pd.Timestamp,
    multiplier: int,
    unit: str,
    remaining: int,
    maximum: int,
) -> None:
    """Reject wide time spans before pandas builds a potentially huge index."""

    if remaining <= 0:
        raise ValueError(f"Resampling exceeds {maximum} intervals (MCP_MAX_RESAMPLE_INTERVALS).")
    if unit in {"MS", "ME"}:
        month_difference = (end.year - start.year) * 12 + end.month - start.month
        minimum_intervals = month_difference // multiplier
    else:
        seconds_per_interval = multiplier * _FIXED_UNIT_SECONDS[unit]
        minimum_intervals = int((end - start).total_seconds() // seconds_per_interval)

    # Anchoring can introduce one extra boundary bucket; check the exact size too.
    if minimum_intervals > remaining:
        raise ValueError(
            f"Resampling would exceed {maximum} intervals (MCP_MAX_RESAMPLE_INTERVALS)."
        )


def _fill_missing_intervals(
    values: pd.Series[Any], missing_mask: pd.Series[Any], method: FillMethod
) -> pd.Series[Any]:
    """Fill only structural gaps, leaving null values from observed rows untouched."""

    if method == "none":
        return values
    if method == "forward_fill":
        candidate = values.ffill()
    elif method == "backward_fill":
        candidate = values.bfill()
    elif method == "linear_interpolation":
        candidate = values.interpolate(method="time", limit_area="inside")
    else:
        candidate = values.fillna(0.0)
    return values.where(~missing_mask, candidate)


def _fill_suggestions() -> list[IntervalFillSuggestion]:
    """Explain choices without assuming a dataset's measurement semantics."""

    return [
        IntervalFillSuggestion(
            method="none",
            guidance="Keep gaps visible when the reason for missing observations is unknown.",
            uses_future_values=False,
        ),
        IntervalFillSuggestion(
            method="forward_fill",
            guidance="Carry the last observation for persistent states or stock measurements.",
            uses_future_values=False,
        ),
        IntervalFillSuggestion(
            method="linear_interpolation",
            guidance="Interpolate smooth continuous measurements for retrospective analysis only.",
            uses_future_values=True,
        ),
        IntervalFillSuggestion(
            method="zero",
            guidance="Use only if no recorded interval truly means zero events or activity.",
            uses_future_values=False,
        ),
    ]
