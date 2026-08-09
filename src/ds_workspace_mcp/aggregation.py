from __future__ import annotations

import math
from enum import Enum
from typing import Any, cast

import pandas as pd
from pandas.api.types import is_bool_dtype, is_datetime64_any_dtype, is_numeric_dtype
from pydantic import BaseModel, Field

from ds_workspace_mcp.config import get_settings
from ds_workspace_mcp.core import read_dataset_frame
from ds_workspace_mcp.exceptions import InvalidAggregationError


class AggregateOperation(str, Enum):
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    SUM = "sum"
    MEAN = "mean"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    STD = "std"


class FilterOperation(str, Enum):
    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    NOT_NULL = "not_null"
    BETWEEN = "between"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class AggregationMetric(BaseModel):
    """One allowlisted aggregation metric."""

    operation: AggregateOperation
    column: str | None = None
    output_name: str | None = None


class AggregationFilter(BaseModel):
    """One typed filter predicate."""

    column: str
    operation: FilterOperation
    value: object | None = None
    values: list[object] | None = None
    lower: object | None = None
    upper: object | None = None


class AggregationOrder(BaseModel):
    """One result ordering rule."""

    column: str
    direction: SortDirection = SortDirection.ASC


class AggregationRequest(BaseModel):
    """Structured aggregation request with no executable expressions."""

    file_name: str
    group_by: list[str] = Field(default_factory=list)
    metrics: list[AggregationMetric]
    filters: list[AggregationFilter] = Field(default_factory=list)
    order_by: list[AggregationOrder] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1)


class AggregationResult(BaseModel):
    """Bounded JSON-safe aggregation result."""

    file_name: str
    group_by: list[str]
    metric_columns: list[str]
    rows: list[dict[str, object]]
    row_count: int = Field(ge=0)
    total_group_count: int = Field(ge=0)
    limit_applied: int = Field(ge=1)


def aggregate_dataset(request: AggregationRequest) -> AggregationResult:
    """Run a safe bounded aggregation over any supported tabular dataset."""

    settings = get_settings()
    limit = min(request.limit, settings.mcp_max_sql_rows)
    df = read_dataset_frame(request.file_name)
    _validate_columns(df, request.group_by, label="group_by")
    for filter_spec in request.filters:
        _validate_columns(df, [filter_spec.column], label="filters")
    for metric in request.metrics:
        if metric.column is not None:
            _validate_columns(df, [metric.column], label="metrics")
        _validate_metric_dtype(df, metric)

    filtered = _apply_filters(df, request.filters)
    total_group_count = _count_groups(filtered, request.group_by)
    if total_group_count > settings.mcp_max_sql_rows:
        raise InvalidAggregationError(
            f"grouping cardinality must not exceed {settings.mcp_max_sql_rows}."
        )

    result_frame, metric_columns = _aggregate_frame(filtered, request.group_by, request.metrics)
    _apply_ordering(result_frame, request.order_by)
    bounded_frame = result_frame.head(limit)
    records = cast(list[dict[str, object]], bounded_frame.astype(object).to_dict("records"))
    rows = [{column: _normalize_scalar(value) for column, value in row.items()} for row in records]
    return AggregationResult(
        file_name=request.file_name,
        group_by=request.group_by,
        metric_columns=metric_columns,
        rows=rows,
        row_count=len(rows),
        total_group_count=total_group_count,
        limit_applied=limit,
    )


def _validate_columns(df: pd.DataFrame, columns: list[str], *, label: str) -> None:
    existing = {str(column) for column in df.columns}
    for column in columns:
        if not isinstance(column, str) or column not in existing:
            raise InvalidAggregationError(f"Unknown {label} column: {column}")


def _validate_metric_dtype(df: pd.DataFrame, metric: AggregationMetric) -> None:
    if metric.operation == AggregateOperation.COUNT and metric.column is None:
        return
    if metric.column is None:
        raise InvalidAggregationError(f"{metric.operation.value} requires a column.")

    series = df[metric.column]
    if metric.operation in {
        AggregateOperation.SUM,
        AggregateOperation.MEAN,
        AggregateOperation.MEDIAN,
        AggregateOperation.STD,
    } and (not is_numeric_dtype(series) or is_bool_dtype(series)):
        raise InvalidAggregationError(f"{metric.operation.value} requires a numeric column.")
    if metric.operation in {AggregateOperation.MIN, AggregateOperation.MAX} and not (
        is_numeric_dtype(series) or is_datetime64_any_dtype(series)
    ):
        raise InvalidAggregationError(
            f"{metric.operation.value} requires numeric or datetime data."
        )


def _apply_filters(df: pd.DataFrame, filters: list[AggregationFilter]) -> pd.DataFrame:
    filtered = df
    for filter_spec in filters:
        series = filtered[filter_spec.column]
        operation = filter_spec.operation
        if operation == FilterOperation.EQ:
            mask = series == _scalar_value(filter_spec.value)
        elif operation == FilterOperation.NE:
            mask = series != _scalar_value(filter_spec.value)
        elif operation in {
            FilterOperation.LT,
            FilterOperation.LTE,
            FilterOperation.GT,
            FilterOperation.GTE,
        }:
            _validate_orderable_filter(series, operation)
            value = _scalar_value(filter_spec.value)
            if operation == FilterOperation.LT:
                mask = series < value
            elif operation == FilterOperation.LTE:
                mask = series <= value
            elif operation == FilterOperation.GT:
                mask = series > value
            else:
                mask = series >= value
        elif operation == FilterOperation.IN:
            mask = series.isin(_list_values(filter_spec.values))
        elif operation == FilterOperation.NOT_IN:
            mask = ~series.isin(_list_values(filter_spec.values))
        elif operation == FilterOperation.IS_NULL:
            mask = series.isna()
        elif operation == FilterOperation.NOT_NULL:
            mask = series.notna()
        elif operation == FilterOperation.BETWEEN:
            _validate_orderable_filter(series, operation)
            lower = cast(Any, _scalar_value(filter_spec.lower))
            upper = cast(Any, _scalar_value(filter_spec.upper))
            mask = series.between(lower, upper)
        else:  # pragma: no cover - enum validation prevents this
            raise InvalidAggregationError(f"Unsupported filter operation: {operation}")
        filtered = filtered[mask]
    return filtered


def _count_groups(df: pd.DataFrame, group_by: list[str]) -> int:
    if not group_by:
        return 1
    return int(df[group_by].drop_duplicates().shape[0])


def _aggregate_frame(
    df: pd.DataFrame,
    group_by: list[str],
    metrics: list[AggregationMetric],
) -> tuple[pd.DataFrame, list[str]]:
    metric_frames: list[pd.DataFrame] = []
    metric_columns: list[str] = []
    grouped = df.groupby(group_by, dropna=False) if group_by else None
    for metric in metrics:
        output_name = _metric_output_name(metric)
        metric_columns.append(output_name)
        if group_by:
            assert grouped is not None
            series = _grouped_metric(grouped, metric)
            metric_frames.append(series.rename(output_name).reset_index())
        else:
            metric_frames.append(pd.DataFrame([{output_name: _ungrouped_metric(df, metric)}]))

    if not metric_frames:
        raise InvalidAggregationError("At least one metric is required.")
    result = metric_frames[0]
    for frame in metric_frames[1:]:
        result = result.merge(frame, on=group_by, how="inner") if group_by else result.join(frame)
    return result, metric_columns


def _grouped_metric(grouped: Any, metric: AggregationMetric) -> pd.Series[Any]:
    if metric.operation == AggregateOperation.COUNT and metric.column is None:
        return cast("pd.Series[Any]", grouped.size())
    assert metric.column is not None
    series = grouped[metric.column]
    if metric.operation == AggregateOperation.COUNT:
        return cast("pd.Series[Any]", series.count())
    if metric.operation == AggregateOperation.COUNT_DISTINCT:
        return cast("pd.Series[Any]", series.nunique(dropna=True))
    return cast("pd.Series[Any]", getattr(series, metric.operation.value)())


def _ungrouped_metric(df: pd.DataFrame, metric: AggregationMetric) -> object:
    if metric.operation == AggregateOperation.COUNT and metric.column is None:
        return int(len(df))
    assert metric.column is not None
    series = df[metric.column]
    if metric.operation == AggregateOperation.COUNT:
        return int(series.count())
    if metric.operation == AggregateOperation.COUNT_DISTINCT:
        return int(series.nunique(dropna=True))
    return cast(object, getattr(series, metric.operation.value)())


def _apply_ordering(result_frame: pd.DataFrame, order_by: list[AggregationOrder]) -> None:
    if not order_by:
        return
    columns = [order.column for order in order_by]
    for column in columns:
        if column not in result_frame.columns:
            raise InvalidAggregationError(f"Unknown order_by column: {column}")
    result_frame.sort_values(
        by=columns,
        ascending=[order.direction == SortDirection.ASC for order in order_by],
        inplace=True,
        kind="mergesort",
    )


def _metric_output_name(metric: AggregationMetric) -> str:
    if metric.output_name is not None:
        if not metric.output_name or not metric.output_name.isidentifier():
            raise InvalidAggregationError(f"Invalid metric output name: {metric.output_name}")
        return metric.output_name
    if metric.column is None:
        return metric.operation.value
    return f"{metric.operation.value}_{metric.column}"


def _scalar_value(value: object | None) -> object:
    if isinstance(value, dict | list):
        raise InvalidAggregationError("Filter values must be scalar.")
    return value


def _list_values(values: list[object] | None) -> list[object]:
    if not values:
        raise InvalidAggregationError("Filter operation requires a non-empty values list.")
    if any(isinstance(value, dict | list) for value in values):
        raise InvalidAggregationError("Filter values must be scalar.")
    return values


def _validate_orderable_filter(series: pd.Series[Any], operation: FilterOperation) -> None:
    if not (is_numeric_dtype(series) or is_datetime64_any_dtype(series)):
        raise InvalidAggregationError(f"{operation.value} requires numeric or datetime data.")


def _normalize_scalar(value: object) -> object:
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        try:
            return _normalize_scalar(value.item())
        except (AttributeError, ValueError, TypeError):
            pass
    if hasattr(value, "isoformat"):
        try:
            return cast(object, value.isoformat())
        except TypeError:
            return value
    return value
