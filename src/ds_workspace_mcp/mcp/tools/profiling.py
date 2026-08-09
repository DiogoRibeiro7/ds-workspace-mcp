from __future__ import annotations

import logging

from ds_workspace_mcp.core import profile_csv_dataset
from ds_workspace_mcp.diagnostics import (
    CorrelationSummary,
    LeakageSummary,
    detect_possible_target_leakage_dataset,
    summarize_correlations_dataset,
)
from ds_workspace_mcp.mcp.app import _mcp_tool
from ds_workspace_mcp.profiling import DatasetProfile
from ds_workspace_mcp.tracing import traced_operation

logger = logging.getLogger(__name__)


@_mcp_tool()
def profile_csv(file_name: str) -> DatasetProfile:
    """
    Profile a CSV dataset.

    Args:
        file_name: CSV file name inside the configured data directory.

    Returns:
        Dataset shape, column names, dtypes, and missing-value statistics.
    """

    with traced_operation(
        "tool.profile_csv",
        {"tool.name": "profile_csv", "dataset.file_name": file_name},
    ):
        logger.info("Tool profile_csv invoked file_name=%s", file_name)
        return profile_csv_dataset(file_name=file_name)


@_mcp_tool()
def summarize_correlations(file_name: str, method: str = "pearson") -> CorrelationSummary:
    """Summarize the top absolute correlations among numeric columns."""

    with traced_operation(
        "tool.summarize_correlations",
        {
            "tool.name": "summarize_correlations",
            "dataset.file_name": file_name,
            "tool.method": method,
        },
    ):
        logger.info(
            "Tool summarize_correlations invoked file_name=%s method=%s",
            file_name,
            method,
        )
        return summarize_correlations_dataset(file_name=file_name, method=method)


@_mcp_tool()
def detect_possible_target_leakage(file_name: str, target_column: str) -> LeakageSummary:
    """Return heuristic warnings about possible target leakage."""

    with traced_operation(
        "tool.detect_possible_target_leakage",
        {
            "tool.name": "detect_possible_target_leakage",
            "dataset.file_name": file_name,
            "tool.target_column": target_column,
        },
    ):
        logger.info(
            "Tool detect_possible_target_leakage invoked file_name=%s target_column=%s",
            file_name,
            target_column,
        )
        return detect_possible_target_leakage_dataset(
            file_name=file_name,
            target_column=target_column,
        )
