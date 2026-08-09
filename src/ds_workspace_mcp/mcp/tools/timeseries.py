from __future__ import annotations

import logging

from ds_workspace_mcp.forecasting import (
    ForecastBaselineEvaluationResult,
    evaluate_forecast_baselines_dataset,
)
from ds_workspace_mcp.mcp.app import _mcp_tool
from ds_workspace_mcp.timeseries import TimeSeriesValidationResult, validate_time_series_dataset
from ds_workspace_mcp.tracing import traced_operation

logger = logging.getLogger(__name__)


@_mcp_tool()
def evaluate_forecast_baselines(
    file_name: str,
    time_column: str,
    target_column: str,
    group_column: str | None = None,
    forecast_horizon: int = 1,
    test_size: float = 0.2,
    seasonal_period: int | None = None,
) -> ForecastBaselineEvaluationResult:
    """Evaluate transparent time-ordered forecasting baselines."""

    with traced_operation(
        "tool.evaluate_forecast_baselines",
        {
            "tool.name": "evaluate_forecast_baselines",
            "dataset.file_name": file_name,
            "tool.time_column": time_column,
            "tool.target_column": target_column,
            "tool.group_column": group_column,
            "tool.forecast_horizon": forecast_horizon,
        },
    ):
        logger.info(
            "Tool evaluate_forecast_baselines invoked "
            "file_name=%s time_column=%s target_column=%s group_column=%s "
            "forecast_horizon=%s test_size=%s seasonal_period=%s",
            file_name,
            time_column,
            target_column,
            group_column,
            forecast_horizon,
            test_size,
            seasonal_period,
        )
        return evaluate_forecast_baselines_dataset(
            file_name=file_name,
            time_column=time_column,
            target_column=target_column,
            group_column=group_column,
            forecast_horizon=forecast_horizon,
            test_size=test_size,
            seasonal_period=seasonal_period,
        )


@_mcp_tool()
def validate_time_series_dataset_tool(
    file_name: str,
    time_column: str,
    target_column: str | None = None,
    group_column: str | None = None,
) -> TimeSeriesValidationResult:
    """Validate whether a dataset looks suitable for time-series modeling."""

    with traced_operation(
        "tool.validate_time_series_dataset",
        {
            "tool.name": "validate_time_series_dataset",
            "dataset.file_name": file_name,
            "tool.time_column": time_column,
            "tool.target_column": target_column,
            "tool.group_column": group_column,
        },
    ):
        logger.info(
            "Tool validate_time_series_dataset_tool invoked "
            "file_name=%s time_column=%s target_column=%s group_column=%s",
            file_name,
            time_column,
            target_column,
            group_column,
        )
        return validate_time_series_dataset(
            file_name=file_name,
            time_column=time_column,
            target_column=target_column,
            group_column=group_column,
        )
