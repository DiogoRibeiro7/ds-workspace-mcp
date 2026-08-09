from __future__ import annotations

import logging

from ds_workspace_mcp.mcp.app import _mcp_tool
from ds_workspace_mcp.timeseries import TimeSeriesValidationResult, validate_time_series_dataset
from ds_workspace_mcp.tracing import traced_operation

logger = logging.getLogger(__name__)


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
