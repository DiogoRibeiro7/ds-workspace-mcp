from __future__ import annotations

import logging

from ds_workspace_mcp.config import Transport, get_settings
from ds_workspace_mcp.logging_config import configure_logging
from ds_workspace_mcp.mcp.app import create_mcp, create_mcp_server, mcp
from ds_workspace_mcp.mcp.prompts.analysis import (
    dataset_analysis_prompt,
    modeling_report_review_prompt,
)
from ds_workspace_mcp.mcp.resources.databases import list_sqlite_databases
from ds_workspace_mcp.mcp.resources.datasets import list_datasets
from ds_workspace_mcp.mcp.resources.reports import (
    latest_modeling_report_resource,
    latest_modeling_report_section_resource,
    latest_modeling_report_sections_resource,
    list_modeling_reports_resource,
    modeling_report_section_resource,
    modeling_report_sections_resource,
    read_modeling_report_resource,
)
from ds_workspace_mcp.mcp.tools.datasets import detect_csv_issues, preview_csv, summarize_dataset
from ds_workspace_mcp.mcp.tools.modeling import (
    assess_modeling_readiness,
    build_experiment_plan,
    build_modeling_report,
    evaluate_baseline_model,
    save_modeling_report,
    suggest_feature_columns,
    suggest_target_columns,
)
from ds_workspace_mcp.mcp.tools.profiling import (
    detect_possible_target_leakage,
    profile_csv,
    summarize_correlations,
)
from ds_workspace_mcp.mcp.tools.reports import (
    compare_latest_modeling_report_sections_tool,
    compare_latest_modeling_reports_tool,
    compare_modeling_report_sections,
    compare_modeling_reports,
    copy_latest_modeling_report_tool,
    copy_modeling_report,
    delete_modeling_report,
    inspect_latest_modeling_report_tool,
    inspect_modeling_report,
    list_latest_modeling_report_sections_tool,
    list_modeling_report_sections,
    list_modeling_reports,
    list_recent_modeling_reports_tool,
    preview_latest_modeling_report_tool,
    preview_modeling_report,
    read_latest_modeling_report_section_tool,
    read_latest_modeling_report_tool,
    read_modeling_report,
    read_modeling_report_section,
    rename_latest_modeling_report_tool,
    rename_modeling_report,
    save_latest_modeling_report_section_tool,
    save_modeling_report_section_tool,
    search_latest_modeling_report_content_tool,
    search_latest_modeling_report_sections_tool,
    search_modeling_report_content,
    search_modeling_report_sections,
    search_modeling_reports,
    summarize_modeling_report_catalog_tool,
    summarize_modeling_report_sections,
)
from ds_workspace_mcp.mcp.tools.sql import (
    describe_sqlite_table,
    list_sqlite_databases_tool,
    list_sqlite_tables,
    query_csv_with_duckdb,
    query_sqlite,
)
from ds_workspace_mcp.mcp.tools.timeseries import validate_time_series_dataset_tool
from ds_workspace_mcp.tracing import configure_tracing

logger = logging.getLogger(__name__)

__all__ = [
    "assess_modeling_readiness",
    "build_experiment_plan",
    "build_modeling_report",
    "compare_latest_modeling_report_sections_tool",
    "compare_latest_modeling_reports_tool",
    "compare_modeling_report_sections",
    "compare_modeling_reports",
    "copy_latest_modeling_report_tool",
    "copy_modeling_report",
    "create_mcp",
    "create_mcp_server",
    "dataset_analysis_prompt",
    "delete_modeling_report",
    "describe_sqlite_table",
    "detect_csv_issues",
    "detect_possible_target_leakage",
    "evaluate_baseline_model",
    "get_transport",
    "inspect_latest_modeling_report_tool",
    "inspect_modeling_report",
    "latest_modeling_report_resource",
    "latest_modeling_report_section_resource",
    "latest_modeling_report_sections_resource",
    "list_datasets",
    "list_latest_modeling_report_sections_tool",
    "list_modeling_report_sections",
    "list_modeling_reports",
    "list_modeling_reports_resource",
    "list_recent_modeling_reports_tool",
    "list_sqlite_databases",
    "list_sqlite_databases_tool",
    "list_sqlite_tables",
    "main",
    "mcp",
    "modeling_report_review_prompt",
    "modeling_report_section_resource",
    "modeling_report_sections_resource",
    "preview_csv",
    "preview_latest_modeling_report_tool",
    "preview_modeling_report",
    "profile_csv",
    "query_csv_with_duckdb",
    "query_sqlite",
    "read_latest_modeling_report_section_tool",
    "read_latest_modeling_report_tool",
    "read_modeling_report",
    "read_modeling_report_resource",
    "read_modeling_report_section",
    "rename_latest_modeling_report_tool",
    "rename_modeling_report",
    "save_latest_modeling_report_section_tool",
    "save_modeling_report",
    "save_modeling_report_section_tool",
    "search_latest_modeling_report_content_tool",
    "search_latest_modeling_report_sections_tool",
    "search_modeling_report_content",
    "search_modeling_report_sections",
    "search_modeling_reports",
    "suggest_feature_columns",
    "suggest_target_columns",
    "summarize_correlations",
    "summarize_dataset",
    "summarize_modeling_report_catalog_tool",
    "summarize_modeling_report_sections",
    "validate_time_series_dataset_tool",
]


def get_transport() -> Transport:
    """Read and validate the MCP transport from the environment."""

    return get_settings().mcp_transport


def main() -> None:
    """Run the MCP server."""

    settings = get_settings()
    configure_logging(settings)
    configure_tracing(settings)
    server = create_mcp_server(settings)
    logger.info(
        "Starting MCP server transport=%s host=%s port=%s auth_enabled=%s",
        settings.mcp_transport,
        settings.mcp_host,
        settings.mcp_port,
        settings.mcp_transport == "streamable-http" and settings.mcp_api_key is not None,
    )
    server.run(transport=get_transport())


if __name__ == "__main__":
    main()
