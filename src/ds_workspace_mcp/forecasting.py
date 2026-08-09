from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd
from pydantic import BaseModel, Field

from ds_workspace_mcp.core import read_csv_dataset
from ds_workspace_mcp.exceptions import InsufficientDataError
from ds_workspace_mcp.timeseries import FrequencyInferenceResult, _infer_frequency

MIN_FORECAST_ROWS = 10
MAX_FORECAST_GROUPS = 20
DEFAULT_FORECAST_HORIZON = 1
DEFAULT_FORECAST_TEST_SIZE = 0.2


class ForecastMetricNotes(BaseModel):
    """Definitions for forecast baseline metrics."""

    mae: str
    rmse: str
    mase: str
    smape: str


class ForecastBaselineMetrics(BaseModel):
    """Forecast baseline error metrics."""

    mae: float
    rmse: float
    mase: float | None
    smape: float


class ForecastBaselineResult(BaseModel):
    """One transparent forecast baseline evaluation."""

    baseline_name: str
    baseline_definition: str
    forecast_horizon: int = Field(ge=1)
    seasonal_period: int | None = None
    training_start: str
    training_end: str
    test_start: str
    test_end: str
    evaluated_points: int = Field(ge=0)
    metrics: ForecastBaselineMetrics


class GroupForecastBaselineResult(BaseModel):
    """Forecast baseline evaluation for one bounded group."""

    group: str
    row_count: int = Field(ge=0)
    frequency: FrequencyInferenceResult
    baselines: list[ForecastBaselineResult]


class ForecastBaselineEvaluationResult(BaseModel):
    """Rolling-origin forecast baseline evaluation."""

    file_name: str
    time_column: str
    target_column: str
    group_column: str | None = None
    frequency: FrequencyInferenceResult
    forecast_horizon: int = Field(ge=1)
    test_size: float
    seasonal_period: int | None = None
    evaluated_points: int = Field(ge=0)
    baselines: list[ForecastBaselineResult]
    group_results: list[GroupForecastBaselineResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metric_notes: ForecastMetricNotes


class _BaselinePointSet(BaseModel):
    actuals: list[float]
    predictions: list[float]
    scaled_absolute_errors: list[float]


@dataclass(frozen=True)
class _SeriesEvaluation:
    group_result: GroupForecastBaselineResult
    points_by_baseline: dict[str, _BaselinePointSet]


def evaluate_forecast_baselines_dataset(
    file_name: str,
    time_column: str,
    target_column: str,
    group_column: str | None = None,
    forecast_horizon: int = DEFAULT_FORECAST_HORIZON,
    test_size: float = DEFAULT_FORECAST_TEST_SIZE,
    seasonal_period: int | None = None,
) -> ForecastBaselineEvaluationResult:
    """Evaluate transparent forecasting baselines with chronological backtesting."""

    _validate_forecast_horizon(forecast_horizon)
    _validate_test_size(test_size)
    if seasonal_period is not None:
        _validate_seasonal_period(seasonal_period)

    df = read_csv_dataset(file_name)
    _validate_column_exists(df, time_column)
    _validate_column_exists(df, target_column)
    if group_column is not None:
        _validate_column_exists(df, group_column)

    aligned = _prepare_forecast_frame(
        df=df,
        time_column=time_column,
        target_column=target_column,
        group_column=group_column,
    )

    if group_column is None:
        series_result = _evaluate_single_series(
            aligned,
            forecast_horizon=forecast_horizon,
            test_size=test_size,
            seasonal_period=seasonal_period,
            group=None,
        )
        return ForecastBaselineEvaluationResult(
            file_name=file_name,
            time_column=time_column,
            target_column=target_column,
            group_column=None,
            frequency=series_result.group_result.frequency,
            forecast_horizon=forecast_horizon,
            test_size=test_size,
            seasonal_period=_resolved_result_seasonal_period(series_result.group_result.baselines),
            evaluated_points=max(
                item.evaluated_points for item in series_result.group_result.baselines
            ),
            baselines=series_result.group_result.baselines,
            group_results=[],
            warnings=[],
            metric_notes=_metric_notes(),
        )

    group_count = int(aligned[group_column].nunique())
    if group_count > MAX_FORECAST_GROUPS:
        raise ValueError(
            f"grouped forecast baselines support at most {MAX_FORECAST_GROUPS} groups."
        )

    series_evaluations = [
        _evaluate_single_series(
            group_df,
            forecast_horizon=forecast_horizon,
            test_size=test_size,
            seasonal_period=seasonal_period,
            group=str(group_value),
        )
        for group_value, group_df in aligned.groupby(group_column, sort=True)
    ]
    group_results = [item.group_result for item in series_evaluations]
    return ForecastBaselineEvaluationResult(
        file_name=file_name,
        time_column=time_column,
        target_column=target_column,
        group_column=group_column,
        frequency=_combine_result_frequencies([item.frequency for item in group_results]),
        forecast_horizon=forecast_horizon,
        test_size=test_size,
        seasonal_period=_resolved_result_seasonal_period(
            [baseline for item in group_results for baseline in item.baselines]
        ),
        evaluated_points=sum(
            max(baseline.evaluated_points for baseline in item.baselines) for item in group_results
        ),
        baselines=_aggregate_group_baselines(
            series_evaluations,
            forecast_horizon=forecast_horizon,
        ),
        group_results=group_results,
        warnings=[],
        metric_notes=_metric_notes(),
    )


def _evaluate_single_series(
    df: pd.DataFrame,
    *,
    forecast_horizon: int,
    test_size: float,
    seasonal_period: int | None,
    group: str | None,
) -> _SeriesEvaluation:
    ordered = df.sort_values("__forecast_time", kind="mergesort").reset_index(drop=True)
    if ordered["__forecast_time"].duplicated().any():
        raise ValueError(_group_prefix(group) + "duplicate timestamps cannot be backtested.")
    if len(ordered) < MIN_FORECAST_ROWS:
        raise InsufficientDataError(
            _group_prefix(group)
            + f"at least {MIN_FORECAST_ROWS} timestamped target rows are required."
        )

    frequency = _infer_frequency(ordered["__forecast_time"])
    if frequency.frequency_kind != "regular":
        raise ValueError(
            _group_prefix(group)
            + "forecast baselines currently require a regular inferred frequency."
        )

    split_index = _resolve_split_index(row_count=len(ordered), test_size=test_size)
    effective_seasonal_period = _resolve_seasonal_period(
        frequency=frequency,
        requested_period=seasonal_period,
        series_length=split_index,
        forecast_horizon=forecast_horizon,
    )
    y_values = [float(value) for value in ordered["__forecast_target"].tolist()]
    times = pd.to_datetime(ordered["__forecast_time"])
    train_y = y_values[:split_index]

    baseline_points = {
        "last_value_naive": _last_value_points(
            y_values,
            split_index=split_index,
            forecast_horizon=forecast_horizon,
            mase_period=1,
        ),
        "drift": _drift_points(
            y_values,
            split_index=split_index,
            forecast_horizon=forecast_horizon,
            mase_period=1,
        ),
    }
    if effective_seasonal_period is not None:
        baseline_points["seasonal_naive"] = _seasonal_points(
            y_values,
            split_index=split_index,
            forecast_horizon=forecast_horizon,
            seasonal_period=effective_seasonal_period,
        )

    baselines = [
        _build_baseline_result(
            baseline_name=baseline_name,
            points=points,
            forecast_horizon=forecast_horizon,
            seasonal_period=(
                effective_seasonal_period if baseline_name == "seasonal_naive" else None
            ),
            train_y=train_y,
            training_start=times.iloc[0].isoformat(),
            training_end=times.iloc[split_index - 1].isoformat(),
            test_start=times.iloc[split_index].isoformat(),
            test_end=times.iloc[-1].isoformat(),
        )
        for baseline_name, points in baseline_points.items()
        if points.actuals
    ]
    if not baselines:
        raise InsufficientDataError(_group_prefix(group) + "no forecast points could be evaluated.")

    return _SeriesEvaluation(
        group_result=GroupForecastBaselineResult(
            group=group or "__all__",
            row_count=len(ordered),
            frequency=frequency,
            baselines=baselines,
        ),
        points_by_baseline=baseline_points,
    )


def _prepare_forecast_frame(
    *,
    df: pd.DataFrame,
    time_column: str,
    target_column: str,
    group_column: str | None,
) -> pd.DataFrame:
    parsed_time = pd.to_datetime(df[time_column], errors="coerce")
    parsed_target = pd.to_numeric(df[target_column], errors="coerce")
    aligned = df.copy()
    aligned["__forecast_time"] = parsed_time
    aligned["__forecast_target"] = parsed_target
    subset = ["__forecast_time", "__forecast_target"]
    if group_column is not None:
        subset.append(group_column)
    cleaned = aligned.dropna(subset=subset)
    if cleaned.empty:
        raise ValueError("No rows have both parseable timestamps and numeric target values.")
    return cleaned


def _last_value_points(
    values: list[float],
    *,
    split_index: int,
    forecast_horizon: int,
    mase_period: int,
) -> _BaselinePointSet:
    actuals: list[float] = []
    predictions: list[float] = []
    scaled_errors: list[float] = []
    denominator = _mase_denominator(values[:split_index], period=mase_period)
    for target_index in range(split_index, len(values)):
        origin_index = target_index - forecast_horizon
        if origin_index < 0:
            continue
        prediction = values[origin_index]
        _append_point(
            actuals=actuals,
            predictions=predictions,
            scaled_errors=scaled_errors,
            actual=values[target_index],
            prediction=prediction,
            mase_denominator=denominator,
        )
    return _BaselinePointSet(
        actuals=actuals,
        predictions=predictions,
        scaled_absolute_errors=scaled_errors,
    )


def _seasonal_points(
    values: list[float],
    *,
    split_index: int,
    forecast_horizon: int,
    seasonal_period: int,
) -> _BaselinePointSet:
    actuals: list[float] = []
    predictions: list[float] = []
    scaled_errors: list[float] = []
    denominator = _mase_denominator(values[:split_index], period=seasonal_period)
    for target_index in range(split_index, len(values)):
        seasonal_index = target_index - seasonal_period
        origin_index = target_index - forecast_horizon
        if seasonal_index < 0 or origin_index < 0 or seasonal_index > origin_index:
            continue
        _append_point(
            actuals=actuals,
            predictions=predictions,
            scaled_errors=scaled_errors,
            actual=values[target_index],
            prediction=values[seasonal_index],
            mase_denominator=denominator,
        )
    return _BaselinePointSet(
        actuals=actuals,
        predictions=predictions,
        scaled_absolute_errors=scaled_errors,
    )


def _drift_points(
    values: list[float],
    *,
    split_index: int,
    forecast_horizon: int,
    mase_period: int,
) -> _BaselinePointSet:
    actuals: list[float] = []
    predictions: list[float] = []
    scaled_errors: list[float] = []
    denominator = _mase_denominator(values[:split_index], period=mase_period)
    first_value = values[0]
    for target_index in range(split_index, len(values)):
        origin_index = target_index - forecast_horizon
        if origin_index <= 0:
            continue
        slope = (values[origin_index] - first_value) / origin_index
        prediction = values[origin_index] + (forecast_horizon * slope)
        _append_point(
            actuals=actuals,
            predictions=predictions,
            scaled_errors=scaled_errors,
            actual=values[target_index],
            prediction=prediction,
            mase_denominator=denominator,
        )
    return _BaselinePointSet(
        actuals=actuals,
        predictions=predictions,
        scaled_absolute_errors=scaled_errors,
    )


def _append_point(
    *,
    actuals: list[float],
    predictions: list[float],
    scaled_errors: list[float],
    actual: float,
    prediction: float,
    mase_denominator: float | None,
) -> None:
    actuals.append(actual)
    predictions.append(prediction)
    if mase_denominator is not None and mase_denominator > 0:
        scaled_errors.append(abs(actual - prediction) / mase_denominator)


def _build_baseline_result(
    *,
    baseline_name: str,
    points: _BaselinePointSet,
    forecast_horizon: int,
    seasonal_period: int | None,
    train_y: list[float],
    training_start: str,
    training_end: str,
    test_start: str,
    test_end: str,
) -> ForecastBaselineResult:
    return ForecastBaselineResult(
        baseline_name=baseline_name,
        baseline_definition=_baseline_definition(
            baseline_name,
            forecast_horizon=forecast_horizon,
            seasonal_period=seasonal_period,
            train_y=train_y,
        ),
        forecast_horizon=forecast_horizon,
        seasonal_period=seasonal_period,
        training_start=training_start,
        training_end=training_end,
        test_start=test_start,
        test_end=test_end,
        evaluated_points=len(points.actuals),
        metrics=_metrics(points),
    )


def _metrics(points: _BaselinePointSet) -> ForecastBaselineMetrics:
    errors = [
        prediction - actual
        for actual, prediction in zip(points.actuals, points.predictions, strict=True)
    ]
    absolute_errors = [abs(error) for error in errors]
    squared_errors = [error * error for error in errors]
    return ForecastBaselineMetrics(
        mae=float(sum(absolute_errors) / len(absolute_errors)),
        rmse=math.sqrt(sum(squared_errors) / len(squared_errors)),
        mase=(
            float(sum(points.scaled_absolute_errors) / len(points.scaled_absolute_errors))
            if points.scaled_absolute_errors
            else None
        ),
        smape=_smape(points.actuals, points.predictions),
    )


def _aggregate_group_baselines(
    series_evaluations: list[_SeriesEvaluation],
    *,
    forecast_horizon: int,
) -> list[ForecastBaselineResult]:
    baseline_names = sorted(
        {
            baseline.baseline_name
            for evaluation in series_evaluations
            for baseline in evaluation.group_result.baselines
        }
    )
    aggregate_results: list[ForecastBaselineResult] = []
    for baseline_name in baseline_names:
        actuals: list[float] = []
        predictions: list[float] = []
        scaled_errors: list[float] = []
        training_start: list[str] = []
        training_end: list[str] = []
        test_start: list[str] = []
        test_end: list[str] = []
        seasonal_periods: set[int] = set()
        for evaluation in series_evaluations:
            matching = [
                item
                for item in evaluation.group_result.baselines
                if item.baseline_name == baseline_name
            ]
            if not matching:
                continue
            baseline = matching[0]
            training_start.append(baseline.training_start)
            training_end.append(baseline.training_end)
            test_start.append(baseline.test_start)
            test_end.append(baseline.test_end)
            if baseline.seasonal_period is not None:
                seasonal_periods.add(baseline.seasonal_period)
            points = evaluation.points_by_baseline[baseline_name]
            actuals.extend(points.actuals)
            predictions.extend(points.predictions)
            scaled_errors.extend(points.scaled_absolute_errors)

        if actuals:
            seasonal_period = seasonal_periods.pop() if len(seasonal_periods) == 1 else None
            aggregate_results.append(
                ForecastBaselineResult(
                    baseline_name=baseline_name,
                    baseline_definition=_aggregate_baseline_definition(
                        baseline_name,
                        forecast_horizon=forecast_horizon,
                        seasonal_period=seasonal_period,
                    ),
                    forecast_horizon=forecast_horizon,
                    seasonal_period=seasonal_period,
                    training_start=min(training_start),
                    training_end=max(training_end),
                    test_start=min(test_start),
                    test_end=max(test_end),
                    evaluated_points=len(actuals),
                    metrics=_metrics(
                        _BaselinePointSet(
                            actuals=actuals,
                            predictions=predictions,
                            scaled_absolute_errors=scaled_errors,
                        )
                    ),
                )
            )
    return aggregate_results


def _smape(actuals: list[float], predictions: list[float]) -> float:
    values: list[float] = []
    for actual, prediction in zip(actuals, predictions, strict=True):
        denominator = abs(actual) + abs(prediction)
        if denominator == 0:
            values.append(0.0)
        else:
            values.append(200.0 * abs(prediction - actual) / denominator)
    return float(sum(values) / len(values))


def _mase_denominator(values: list[float], *, period: int) -> float | None:
    if period <= 0 or len(values) <= period:
        return None
    diffs = [abs(values[index] - values[index - period]) for index in range(period, len(values))]
    if not diffs:
        return None
    denominator = sum(diffs) / len(diffs)
    if denominator <= 0:
        return None
    return float(denominator)


def _resolve_seasonal_period(
    *,
    frequency: FrequencyInferenceResult,
    requested_period: int | None,
    series_length: int,
    forecast_horizon: int,
) -> int | None:
    candidate = requested_period or _default_seasonal_period(frequency.frequency)
    if candidate is None:
        return None
    if candidate < forecast_horizon:
        return None
    if series_length <= candidate:
        return None
    return candidate


def _default_seasonal_period(frequency: str | None) -> int | None:
    if frequency is None:
        return None
    normalized = frequency.lower()
    if normalized in {"1h", "60min"}:
        return 24
    if normalized == "1d":
        return 7
    if normalized in {"7d", "w", "w-mon", "w-sun"}:
        return 52
    if normalized in {"ms", "me", "m"}:
        return 12
    return None


def _baseline_definition(
    baseline_name: str,
    *,
    forecast_horizon: int,
    seasonal_period: int | None,
    train_y: list[float],
) -> str:
    if baseline_name == "last_value_naive":
        return (
            "Predicts each target point from the most recent observed value available "
            f"{forecast_horizon} step(s) before that point."
        )
    if baseline_name == "seasonal_naive":
        return (
            "Predicts each target point from the value observed "
            f"{seasonal_period} regular step(s) earlier."
        )
    if baseline_name == "drift":
        return (
            "Extends a straight-line drift from the first observed training value "
            f"({train_y[0]:g}) to the rolling forecast origin."
        )
    return baseline_name


def _aggregate_baseline_definition(
    baseline_name: str,
    *,
    forecast_horizon: int,
    seasonal_period: int | None,
) -> str:
    if baseline_name == "last_value_naive":
        return (
            "Grouped aggregate of last-value naive forecasts, each using only values "
            f"available {forecast_horizon} step(s) before its target point."
        )
    if baseline_name == "seasonal_naive":
        return "Grouped aggregate of seasonal naive forecasts" + (
            f" using a {seasonal_period}-step seasonal period."
            if seasonal_period is not None
            else " with per-group seasonal periods."
        )
    if baseline_name == "drift":
        return "Grouped aggregate of drift forecasts from each group's first value."
    return baseline_name


def _combine_result_frequencies(
    frequencies: list[FrequencyInferenceResult],
) -> FrequencyInferenceResult:
    if not frequencies:
        raise ValueError("No group frequencies were available.")
    first = frequencies[0]
    if all(
        item.frequency == first.frequency and item.frequency_kind == first.frequency_kind
        for item in frequencies
    ):
        return FrequencyInferenceResult(
            frequency=first.frequency,
            frequency_kind=first.frequency_kind,
            confidence=min(item.confidence for item in frequencies),
            support_ratio=min(item.support_ratio for item in frequencies),
            candidate_interval=first.candidate_interval,
            is_regular=first.is_regular,
            is_irregular=first.is_irregular,
            missing_interval_count=sum(item.missing_interval_count for item in frequencies),
        )
    return FrequencyInferenceResult(
        frequency=None,
        frequency_kind="heterogeneous",
        confidence=0.0,
        support_ratio=0.0,
        candidate_interval=None,
        is_regular=False,
        is_irregular=True,
        missing_interval_count=sum(item.missing_interval_count for item in frequencies),
    )


def _resolved_result_seasonal_period(baselines: list[ForecastBaselineResult]) -> int | None:
    periods = {
        baseline.seasonal_period
        for baseline in baselines
        if baseline.baseline_name == "seasonal_naive" and baseline.seasonal_period is not None
    }
    if len(periods) == 1:
        return periods.pop()
    return None


def _metric_notes() -> ForecastMetricNotes:
    return ForecastMetricNotes(
        mae="Mean absolute error over evaluated backtest points.",
        rmse="Root mean squared error over evaluated backtest points.",
        mase=(
            "Mean absolute scaled error. Non-seasonal baselines use the mean absolute "
            "one-step training difference as denominator; seasonal naive uses the "
            "seasonal-period training difference. Returned as null when the denominator "
            "is zero or unavailable."
        ),
        smape=(
            "Symmetric mean absolute percentage error using "
            "200*abs(actual-prediction)/(abs(actual)+abs(prediction)); terms with both "
            "actual and prediction equal to zero contribute 0."
        ),
    )


def _resolve_split_index(row_count: int, test_size: float) -> int:
    test_rows = max(1, int(row_count * test_size + 0.999999))
    split_index = row_count - test_rows
    if split_index <= 0 or split_index >= row_count:
        raise InsufficientDataError("test_size produced an empty train or test window.")
    return split_index


def _validate_column_exists(df: pd.DataFrame, column_name: str) -> None:
    if column_name not in df.columns:
        raise ValueError(f"Unknown column: {column_name}")


def _validate_forecast_horizon(forecast_horizon: int) -> None:
    if forecast_horizon < 1:
        raise ValueError("forecast_horizon must be greater than or equal to 1.")


def _validate_test_size(test_size: float) -> None:
    if test_size <= 0 or test_size >= 1:
        raise ValueError("test_size must be greater than 0 and less than 1.")


def _validate_seasonal_period(seasonal_period: int) -> None:
    if seasonal_period < 1:
        raise ValueError("seasonal_period must be greater than or equal to 1.")


def _group_prefix(group: str | None) -> str:
    return f"Group `{group}` " if group is not None else ""
