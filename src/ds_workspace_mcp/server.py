from __future__ import annotations

import os
from typing import Literal, cast

from mcp.server.fastmcp import FastMCP

from ds_workspace_mcp.core import (
    DatasetIssue,
    DatasetPreview,
    DatasetProfile,
    detect_csv_dataset_issues,
    list_csv_files,
    preview_csv_dataset,
    profile_csv_dataset,
)

Transport = Literal["stdio", "streamable-http"]

mcp = FastMCP("Data Science Workspace MCP", json_response=True)


@mcp.resource("datasets://catalog")
def list_datasets() -> str:
    """
    List CSV datasets available to the assistant.

    Resources are useful for exposing data without side effects.
    """

    files = list_csv_files()

    if not files:
        return "No CSV datasets found in the configured data directory."

    return "\n".join(files)


@mcp.tool()
def preview_csv(file_name: str, rows: int = 5) -> DatasetPreview:
    """
    Preview the first rows of a CSV dataset.

    Args:
        file_name: CSV file name inside the configured data directory.
        rows: Number of rows to return. Must be between 1 and 50.

    Returns:
        A structured preview of the dataset.
    """

    return preview_csv_dataset(file_name=file_name, rows=rows)


@mcp.tool()
def profile_csv(file_name: str) -> DatasetProfile:
    """
    Profile a CSV dataset.

    Args:
        file_name: CSV file name inside the configured data directory.

    Returns:
        Dataset shape, column names, dtypes, and missing-value statistics.
    """

    return profile_csv_dataset(file_name=file_name)


@mcp.tool()
def detect_csv_issues(file_name: str) -> list[DatasetIssue]:
    """
    Detect simple data-quality issues in a CSV dataset.

    This tool is intentionally conservative and does not modify the dataset.

    Args:
        file_name: CSV file name inside the configured data directory.

    Returns:
        A list of detected data-quality issues.
    """

    return detect_csv_dataset_issues(file_name=file_name)


@mcp.prompt()
def dataset_analysis_prompt(file_name: str, objective: str = "exploratory analysis") -> str:
    """
    Create a reusable analysis prompt for a dataset.

    Args:
        file_name: Dataset file name.
        objective: Analysis objective.

    Returns:
        A prompt that an MCP-compatible assistant can use.
    """

    return f"""
You are analysing the dataset `{file_name}`.

Objective:
{objective}

Start by:
1. Inspecting the dataset schema.
2. Checking missing values and suspicious columns.
3. Suggesting useful target variables.
4. Proposing baseline statistical and machine learning approaches.
5. Explaining risks, assumptions, and validation strategy.

Keep the analysis practical and reproducible.
""".strip()


def get_transport() -> Transport:
    """
    Read and validate the MCP transport from the environment.

    Returns:
        Either `stdio` or `streamable-http`.
    """

    raw_transport = os.getenv("MCP_TRANSPORT", "streamable-http")

    if raw_transport not in {"stdio", "streamable-http"}:
        raise ValueError("MCP_TRANSPORT must be either 'stdio' or 'streamable-http'.")

    return cast(Transport, raw_transport)


def main() -> None:
    """Run the MCP server."""

    mcp.run(transport=get_transport())


if __name__ == "__main__":
    main()
