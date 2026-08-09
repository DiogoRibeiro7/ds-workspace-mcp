from __future__ import annotations

import logging

from ds_workspace_mcp.core import (
    DatasetIssue,
    DatasetPreview,
    detect_csv_dataset_issues,
    inspect_dataset,
    list_excel_sheets,
    preview_csv_dataset,
    preview_dataset,
)
from ds_workspace_mcp.datasets import DatasetMetadata
from ds_workspace_mcp.mcp.app import _mcp_tool
from ds_workspace_mcp.overview import DatasetOverview, summarize_dataset_overview
from ds_workspace_mcp.tracing import traced_operation

logger = logging.getLogger(__name__)


@_mcp_tool()
def preview_csv(file_name: str, rows: int = 5) -> DatasetPreview:
    """
    Preview the first rows of a CSV dataset.

    Args:
        file_name: CSV file name inside the configured data directory.
        rows: Number of rows to return. Must be between 1 and 50.

    Returns:
        A structured preview of the dataset.
    """

    with traced_operation(
        "tool.preview_csv",
        {"tool.name": "preview_csv", "dataset.file_name": file_name, "tool.rows": rows},
    ):
        logger.info("Tool preview_csv invoked file_name=%s rows=%s", file_name, rows)
        return preview_csv_dataset(file_name=file_name, rows=rows)


@_mcp_tool()
def preview_dataset_file(file_name: str, rows: int = 5) -> DatasetPreview:
    """Preview the first rows of any supported tabular dataset."""

    with traced_operation(
        "tool.preview_dataset_file",
        {
            "tool.name": "preview_dataset_file",
            "dataset.file_name": file_name,
            "tool.rows": rows,
        },
    ):
        logger.info("Tool preview_dataset_file invoked file_name=%s rows=%s", file_name, rows)
        return preview_dataset(file_name=file_name, rows=rows)


@_mcp_tool()
def inspect_dataset_file(file_name: str) -> DatasetMetadata:
    """Inspect path-free metadata for any supported tabular dataset."""

    with traced_operation(
        "tool.inspect_dataset_file",
        {"tool.name": "inspect_dataset_file", "dataset.file_name": file_name},
    ):
        logger.info("Tool inspect_dataset_file invoked file_name=%s", file_name)
        return inspect_dataset(file_name=file_name)


@_mcp_tool()
def list_excel_sheets_tool(file_name: str) -> list[str]:
    """List sheet names for one `.xlsx` dataset."""

    with traced_operation(
        "tool.list_excel_sheets",
        {"tool.name": "list_excel_sheets", "dataset.file_name": file_name},
    ):
        logger.info("Tool list_excel_sheets invoked file_name=%s", file_name)
        return list_excel_sheets(file_name=file_name)


@_mcp_tool()
def detect_csv_issues(file_name: str) -> list[DatasetIssue]:
    """
    Detect simple data-quality issues in a CSV dataset.

    This tool is intentionally conservative and does not modify the dataset.

    Args:
        file_name: CSV file name inside the configured data directory.

    Returns:
        A list of detected data-quality issues.
    """

    with traced_operation(
        "tool.detect_csv_issues",
        {"tool.name": "detect_csv_issues", "dataset.file_name": file_name},
    ):
        logger.info("Tool detect_csv_issues invoked file_name=%s", file_name)
        return detect_csv_dataset_issues(file_name=file_name)


@_mcp_tool()
def summarize_dataset(file_name: str) -> DatasetOverview:
    """
    Return a compact first-pass overview of a CSV dataset.

    Args:
        file_name: CSV file name inside the configured data directory.

    Returns:
        A concise overview with dataset shape, issue highlights, correlations, and next steps.
    """

    with traced_operation(
        "tool.summarize_dataset",
        {"tool.name": "summarize_dataset", "dataset.file_name": file_name},
    ):
        logger.info("Tool summarize_dataset invoked file_name=%s", file_name)
        return summarize_dataset_overview(file_name=file_name)
