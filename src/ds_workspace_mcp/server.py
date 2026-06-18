from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from ds_workspace_mcp.auth import build_http_auth
from ds_workspace_mcp.config import Settings, Transport, get_settings
from ds_workspace_mcp.core import (
    DatasetIssue,
    DatasetPreview,
    detect_csv_dataset_issues,
    list_csv_files,
    preview_csv_dataset,
    profile_csv_dataset,
)
from ds_workspace_mcp.diagnostics import (
    CorrelationSummary,
    LeakageSummary,
    detect_possible_target_leakage_dataset,
    summarize_correlations_dataset,
)
from ds_workspace_mcp.experiment_plan import (
    ExperimentPlanResult,
    build_experiment_plan_dataset,
)
from ds_workspace_mcp.feature_selection import (
    FeatureSelectionResult,
    suggest_feature_columns_dataset,
)
from ds_workspace_mcp.logging_config import configure_logging
from ds_workspace_mcp.ml.baselines import (
    BaselineEvaluationResult,
    evaluate_baseline_model_dataset,
)
from ds_workspace_mcp.modeling_readiness import (
    ModelingReadinessResult,
    assess_modeling_readiness_dataset,
)
from ds_workspace_mcp.modeling_report import (
    ModelingReportResult,
    build_modeling_report_dataset,
)
from ds_workspace_mcp.overview import DatasetOverview, summarize_dataset_overview
from ds_workspace_mcp.profiling import DatasetProfile
from ds_workspace_mcp.report_export import (
    ComparedModelingReport,
    ComparedModelingReportSection,
    CopiedModelingReport,
    DeletedModelingReport,
    ModelingReportCatalogSummary,
    ModelingReportMetadata,
    ModelingReportSection,
    ModelingReportSectionMatch,
    ModelingReportSectionSummary,
    PreviewModelingReport,
    ReadModelingReport,
    ReadModelingReportSection,
    RenamedModelingReport,
    ReportSearchMatch,
    SavedModelingReport,
    SavedModelingReportSection,
    StoredModelingReport,
    compare_latest_modeling_report_sections,
    compare_latest_modeling_reports,
    compare_saved_modeling_report_sections,
    compare_saved_modeling_reports,
    copy_latest_modeling_report,
    copy_saved_modeling_report,
    delete_saved_modeling_report,
    inspect_latest_modeling_report,
    inspect_saved_modeling_report,
    list_latest_modeling_report_sections,
    list_recent_modeling_reports,
    list_saved_modeling_report_sections,
    list_saved_modeling_reports,
    preview_latest_modeling_report,
    preview_saved_modeling_report,
    read_latest_modeling_report,
    read_latest_modeling_report_section,
    read_saved_modeling_report,
    read_saved_modeling_report_section,
    rename_saved_modeling_report,
    save_latest_modeling_report_section,
    save_modeling_report_dataset,
    save_modeling_report_section,
    search_latest_modeling_report_content,
    search_latest_modeling_report_sections,
    search_saved_modeling_report_content,
    search_saved_modeling_report_sections,
    search_saved_modeling_reports,
    summarize_modeling_report_catalog,
    summarize_saved_modeling_report_sections,
)
from ds_workspace_mcp.sql.duckdb_engine import DuckDBQueryResult, query_csv_with_duckdb_dataset
from ds_workspace_mcp.sql.sqlite_engine import (
    SQLiteDatabaseInfo,
    SQLiteQueryResult,
    SQLiteTableSchema,
    list_sqlite_files,
    query_sqlite_database,
)
from ds_workspace_mcp.sql.sqlite_engine import (
    describe_sqlite_table as describe_sqlite_table_dataset,
)
from ds_workspace_mcp.sql.sqlite_engine import (
    list_sqlite_tables as list_sqlite_tables_dataset,
)
from ds_workspace_mcp.targeting import (
    TargetSuggestionResult,
    suggest_target_columns_dataset,
)
from ds_workspace_mcp.timeseries import TimeSeriesValidationResult, validate_time_series_dataset
from ds_workspace_mcp.tracing import configure_tracing, traced_operation

logger = logging.getLogger(__name__)


def create_mcp(settings: Settings) -> FastMCP:
    """Create the MCP server with validated runtime settings."""

    auth_settings, token_verifier = build_http_auth(settings)
    return FastMCP(
        "Data Science Workspace MCP",
        json_response=True,
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level=settings.mcp_log_level,
        auth=auth_settings,
        token_verifier=token_verifier,
    )


mcp = create_mcp(get_settings())


@mcp.resource("datasets://catalog")
def list_datasets() -> str:
    """
    List CSV datasets available to the assistant.

    Resources are useful for exposing data without side effects.
    """

    with traced_operation("resource.list_datasets"):
        files = list_csv_files()
        logger.info("Resource request datasets://catalog returned %s files", len(files))

        if not files:
            return "No CSV datasets found in the configured data directory."

        return "\n".join(files)


@mcp.resource("databases://sqlite")
def list_sqlite_databases() -> str:
    """List SQLite databases available to the assistant."""

    with traced_operation("resource.list_sqlite_databases"):
        files = list_sqlite_files()
        logger.info("Resource request databases://sqlite returned %s files", len(files))

        if not files:
            return "No SQLite databases found in the configured data directory."

        return "\n".join(files)


@mcp.resource("reports://modeling")
def list_modeling_reports_resource() -> str:
    """List saved modeling report artifacts from the local reports directory."""

    with traced_operation("resource.list_modeling_reports"):
        reports = list_saved_modeling_reports()
        logger.info("Resource request reports://modeling returned %s reports", len(reports))

        if not reports:
            return "No modeling reports found in the local reports directory."

        return "\n".join(report.output_name for report in reports)


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

    with traced_operation(
        "tool.preview_csv",
        {"tool.name": "preview_csv", "dataset.file_name": file_name, "tool.rows": rows},
    ):
        logger.info("Tool preview_csv invoked file_name=%s rows=%s", file_name, rows)
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

    with traced_operation(
        "tool.profile_csv",
        {"tool.name": "profile_csv", "dataset.file_name": file_name},
    ):
        logger.info("Tool profile_csv invoked file_name=%s", file_name)
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

    with traced_operation(
        "tool.detect_csv_issues",
        {"tool.name": "detect_csv_issues", "dataset.file_name": file_name},
    ):
        logger.info("Tool detect_csv_issues invoked file_name=%s", file_name)
        return detect_csv_dataset_issues(file_name=file_name)


@mcp.tool()
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


@mcp.tool()
def suggest_target_columns(file_name: str) -> TargetSuggestionResult:
    """
    Suggest plausible target columns for modeling.

    Args:
        file_name: CSV file name inside the configured data directory.

    Returns:
        Ranked target candidates with suggested task types and reasoning.
    """

    with traced_operation(
        "tool.suggest_target_columns",
        {"tool.name": "suggest_target_columns", "dataset.file_name": file_name},
    ):
        logger.info("Tool suggest_target_columns invoked file_name=%s", file_name)
        return suggest_target_columns_dataset(file_name=file_name)


@mcp.tool()
def suggest_feature_columns(file_name: str, target_column: str) -> FeatureSelectionResult:
    """
    Suggest which feature columns to include, review, or exclude for modeling.

    Args:
        file_name: CSV file name inside the configured data directory.
        target_column: Target column to protect against leakage and trivial features.

    Returns:
        Structured feature-selection guidance for a baseline modeling workflow.
    """

    with traced_operation(
        "tool.suggest_feature_columns",
        {
            "tool.name": "suggest_feature_columns",
            "dataset.file_name": file_name,
            "tool.target_column": target_column,
        },
    ):
        logger.info(
            "Tool suggest_feature_columns invoked file_name=%s target_column=%s",
            file_name,
            target_column,
        )
        return suggest_feature_columns_dataset(
            file_name=file_name,
            target_column=target_column,
        )


@mcp.tool()
def assess_modeling_readiness(
    file_name: str,
    target_column: str | None = None,
) -> ModelingReadinessResult:
    """
    Assess whether a dataset is ready for a first supervised modeling iteration.

    Args:
        file_name: CSV file name inside the configured data directory.
        target_column: Optional target override. When omitted, the top suggested target is used.

    Returns:
        A compact orchestration of target selection, feature review, and leakage checks.
    """

    with traced_operation(
        "tool.assess_modeling_readiness",
        {
            "tool.name": "assess_modeling_readiness",
            "dataset.file_name": file_name,
            "tool.target_column": target_column,
        },
    ):
        logger.info(
            "Tool assess_modeling_readiness invoked file_name=%s target_column=%s",
            file_name,
            target_column,
        )
        return assess_modeling_readiness_dataset(
            file_name=file_name,
            target_column=target_column,
        )


@mcp.tool()
def build_experiment_plan(
    file_name: str,
    target_column: str | None = None,
) -> ExperimentPlanResult:
    """
    Build a concrete first-pass modeling experiment plan for a dataset.

    Args:
        file_name: CSV file name inside the configured data directory.
        target_column: Optional target override. When omitted, the top suggested target is used.

    Returns:
        A structured experiment plan with starter models, risks, metrics, and next steps.
    """

    with traced_operation(
        "tool.build_experiment_plan",
        {
            "tool.name": "build_experiment_plan",
            "dataset.file_name": file_name,
            "tool.target_column": target_column,
        },
    ):
        logger.info(
            "Tool build_experiment_plan invoked file_name=%s target_column=%s",
            file_name,
            target_column,
        )
        return build_experiment_plan_dataset(
            file_name=file_name,
            target_column=target_column,
        )


@mcp.tool()
def build_modeling_report(
    file_name: str,
    target_column: str | None = None,
) -> ModelingReportResult:
    """
    Build a markdown modeling report artifact for a dataset.

    Args:
        file_name: CSV file name inside the configured data directory.
        target_column: Optional target override. When omitted, the top suggested target is used.

    Returns:
        A compact markdown report suitable for review or handoff.
    """

    with traced_operation(
        "tool.build_modeling_report",
        {
            "tool.name": "build_modeling_report",
            "dataset.file_name": file_name,
            "tool.target_column": target_column,
        },
    ):
        logger.info(
            "Tool build_modeling_report invoked file_name=%s target_column=%s",
            file_name,
            target_column,
        )
        return build_modeling_report_dataset(
            file_name=file_name,
            target_column=target_column,
        )


@mcp.tool()
def save_modeling_report(
    file_name: str,
    target_column: str | None = None,
    output_name: str | None = None,
) -> SavedModelingReport:
    """
    Save a modeling report artifact into the local reports directory.

    Args:
        file_name: CSV file name inside the configured data directory.
        target_column: Optional target override. When omitted, the top suggested target is used.
        output_name: Optional markdown file name inside `reports/`.

    Returns:
        Metadata about the saved report artifact.
    """

    with traced_operation(
        "tool.save_modeling_report",
        {
            "tool.name": "save_modeling_report",
            "dataset.file_name": file_name,
            "tool.target_column": target_column,
            "tool.output_name": output_name,
        },
    ):
        logger.info(
            "Tool save_modeling_report invoked file_name=%s target_column=%s output_name=%s",
            file_name,
            target_column,
            output_name,
        )
        return save_modeling_report_dataset(
            file_name=file_name,
            target_column=target_column,
            output_name=output_name,
        )


@mcp.tool()
def list_modeling_reports() -> list[StoredModelingReport]:
    """Return markdown modeling reports saved inside the local reports directory."""

    with traced_operation("tool.list_modeling_reports", {"tool.name": "list_modeling_reports"}):
        logger.info("Tool list_modeling_reports invoked")
        return list_saved_modeling_reports()


@mcp.tool()
def search_modeling_reports(query: str) -> list[StoredModelingReport]:
    """Return saved markdown modeling reports whose file names match the query."""

    with traced_operation(
        "tool.search_modeling_reports",
        {"tool.name": "search_modeling_reports", "tool.query": query},
    ):
        logger.info("Tool search_modeling_reports invoked query=%s", query)
        return search_saved_modeling_reports(query=query)


@mcp.tool()
def search_modeling_report_content(query: str) -> list[ReportSearchMatch]:
    """Return saved modeling reports whose markdown content matches the query."""

    with traced_operation(
        "tool.search_modeling_report_content",
        {"tool.name": "search_modeling_report_content", "tool.query": query},
    ):
        logger.info("Tool search_modeling_report_content invoked query=%s", query)
        return search_saved_modeling_report_content(query=query)


@mcp.tool()
def search_latest_modeling_report_content_tool(query: str) -> list[ReportSearchMatch]:
    """Return content matches from the newest saved modeling report."""

    with traced_operation(
        "tool.search_latest_modeling_report_content",
        {"tool.name": "search_latest_modeling_report_content", "tool.query": query},
    ):
        logger.info("Tool search_latest_modeling_report_content_tool invoked query=%s", query)
        return search_latest_modeling_report_content(query=query)


@mcp.tool()
def search_modeling_report_sections(query: str) -> list[ModelingReportSectionMatch]:
    """Search section headings across saved modeling reports."""

    with traced_operation(
        "tool.search_modeling_report_sections",
        {"tool.name": "search_modeling_report_sections", "tool.query": query},
    ):
        logger.info("Tool search_modeling_report_sections invoked query=%s", query)
        return search_saved_modeling_report_sections(query=query)


@mcp.tool()
def search_latest_modeling_report_sections_tool(query: str) -> list[ModelingReportSectionMatch]:
    """Search section headings inside the newest saved modeling report."""

    with traced_operation(
        "tool.search_latest_modeling_report_sections",
        {"tool.name": "search_latest_modeling_report_sections", "tool.query": query},
    ):
        logger.info("Tool search_latest_modeling_report_sections_tool invoked query=%s", query)
        return search_latest_modeling_report_sections(query=query)


@mcp.tool()
def summarize_modeling_report_sections() -> list[ModelingReportSectionSummary]:
    """Summarize recurring section headings across saved modeling reports."""

    with traced_operation(
        "tool.summarize_modeling_report_sections",
        {"tool.name": "summarize_modeling_report_sections"},
    ):
        logger.info("Tool summarize_modeling_report_sections invoked")
        return summarize_saved_modeling_report_sections()


@mcp.tool()
def list_recent_modeling_reports_tool(limit: int = 5) -> list[StoredModelingReport]:
    """Return the most recently modified saved modeling reports."""

    with traced_operation(
        "tool.list_recent_modeling_reports",
        {"tool.name": "list_recent_modeling_reports", "tool.limit": limit},
    ):
        logger.info("Tool list_recent_modeling_reports_tool invoked limit=%s", limit)
        return list_recent_modeling_reports(limit=limit)


@mcp.tool()
def summarize_modeling_report_catalog_tool(limit: int = 5) -> ModelingReportCatalogSummary:
    """Return a compact summary of saved modeling report artifacts."""

    with traced_operation(
        "tool.summarize_modeling_report_catalog",
        {"tool.name": "summarize_modeling_report_catalog", "tool.limit": limit},
    ):
        logger.info("Tool summarize_modeling_report_catalog_tool invoked limit=%s", limit)
        return summarize_modeling_report_catalog(limit=limit)


@mcp.tool()
def read_modeling_report(output_name: str) -> ReadModelingReport:
    """Read one saved markdown modeling report from the local reports directory."""

    with traced_operation(
        "tool.read_modeling_report",
        {"tool.name": "read_modeling_report", "tool.output_name": output_name},
    ):
        logger.info("Tool read_modeling_report invoked output_name=%s", output_name)
        return read_saved_modeling_report(output_name=output_name)


@mcp.tool()
def list_modeling_report_sections(output_name: str) -> list[ModelingReportSection]:
    """List markdown sections discovered inside one saved modeling report."""

    with traced_operation(
        "tool.list_modeling_report_sections",
        {"tool.name": "list_modeling_report_sections", "tool.output_name": output_name},
    ):
        logger.info("Tool list_modeling_report_sections invoked output_name=%s", output_name)
        return list_saved_modeling_report_sections(output_name=output_name)


@mcp.tool()
def list_latest_modeling_report_sections_tool() -> list[ModelingReportSection]:
    """List markdown sections discovered inside the newest saved modeling report."""

    with traced_operation(
        "tool.list_latest_modeling_report_sections",
        {"tool.name": "list_latest_modeling_report_sections"},
    ):
        logger.info("Tool list_latest_modeling_report_sections_tool invoked")
        return list_latest_modeling_report_sections()


@mcp.tool()
def read_modeling_report_section(
    output_name: str,
    section_heading: str,
) -> ReadModelingReportSection:
    """Read one markdown section from a saved modeling report."""

    with traced_operation(
        "tool.read_modeling_report_section",
        {
            "tool.name": "read_modeling_report_section",
            "tool.output_name": output_name,
            "tool.section_heading": section_heading,
        },
    ):
        logger.info(
            "Tool read_modeling_report_section invoked output_name=%s section_heading=%s",
            output_name,
            section_heading,
        )
        return read_saved_modeling_report_section(
            output_name=output_name,
            section_heading=section_heading,
        )


@mcp.tool()
def read_latest_modeling_report_section_tool(
    section_heading: str,
) -> ReadModelingReportSection:
    """Read one markdown section from the newest saved modeling report."""

    with traced_operation(
        "tool.read_latest_modeling_report_section",
        {
            "tool.name": "read_latest_modeling_report_section",
            "tool.section_heading": section_heading,
        },
    ):
        logger.info(
            "Tool read_latest_modeling_report_section_tool invoked section_heading=%s",
            section_heading,
        )
        return read_latest_modeling_report_section(section_heading=section_heading)


@mcp.tool()
def save_modeling_report_section_tool(
    output_name: str,
    section_heading: str,
    new_output_name: str | None = None,
) -> SavedModelingReportSection:
    """Save one markdown section from a report as a new markdown artifact."""

    with traced_operation(
        "tool.save_modeling_report_section",
        {
            "tool.name": "save_modeling_report_section",
            "tool.output_name": output_name,
            "tool.section_heading": section_heading,
            "tool.new_output_name": new_output_name,
        },
    ):
        logger.info(
            "Tool save_modeling_report_section_tool invoked "
            "output_name=%s section_heading=%s new_output_name=%s",
            output_name,
            section_heading,
            new_output_name,
        )
        return save_modeling_report_section(
            output_name=output_name,
            section_heading=section_heading,
            new_output_name=new_output_name,
        )


@mcp.tool()
def save_latest_modeling_report_section_tool(
    section_heading: str,
    new_output_name: str | None = None,
) -> SavedModelingReportSection:
    """Save one section from the newest report as a new markdown artifact."""

    with traced_operation(
        "tool.save_latest_modeling_report_section",
        {
            "tool.name": "save_latest_modeling_report_section",
            "tool.section_heading": section_heading,
            "tool.new_output_name": new_output_name,
        },
    ):
        logger.info(
            "Tool save_latest_modeling_report_section_tool invoked "
            "section_heading=%s new_output_name=%s",
            section_heading,
            new_output_name,
        )
        return save_latest_modeling_report_section(
            section_heading=section_heading,
            new_output_name=new_output_name,
        )


@mcp.tool()
def compare_modeling_report_sections(
    output_name: str,
    other_output_name: str,
    section_heading: str,
) -> ComparedModelingReportSection:
    """Return a bounded diff summary between matching sections in two reports."""

    with traced_operation(
        "tool.compare_modeling_report_sections",
        {
            "tool.name": "compare_modeling_report_sections",
            "tool.output_name": output_name,
            "tool.other_output_name": other_output_name,
            "tool.section_heading": section_heading,
        },
    ):
        logger.info(
            "Tool compare_modeling_report_sections invoked "
            "output_name=%s other_output_name=%s section_heading=%s",
            output_name,
            other_output_name,
            section_heading,
        )
        return compare_saved_modeling_report_sections(
            output_name=output_name,
            other_output_name=other_output_name,
            section_heading=section_heading,
        )


@mcp.tool()
def compare_latest_modeling_report_sections_tool(
    section_heading: str,
) -> ComparedModelingReportSection:
    """Return a bounded diff summary for one section across the two newest reports."""

    with traced_operation(
        "tool.compare_latest_modeling_report_sections",
        {
            "tool.name": "compare_latest_modeling_report_sections",
            "tool.section_heading": section_heading,
        },
    ):
        logger.info(
            "Tool compare_latest_modeling_report_sections_tool invoked section_heading=%s",
            section_heading,
        )
        return compare_latest_modeling_report_sections(section_heading=section_heading)


@mcp.tool()
def read_latest_modeling_report_tool() -> ReadModelingReport:
    """Read the most recently modified saved markdown modeling report."""

    with traced_operation(
        "tool.read_latest_modeling_report",
        {"tool.name": "read_latest_modeling_report"},
    ):
        logger.info("Tool read_latest_modeling_report_tool invoked")
        return read_latest_modeling_report()


@mcp.tool()
def delete_modeling_report(output_name: str) -> DeletedModelingReport:
    """Delete one saved markdown modeling report from the local reports directory."""

    with traced_operation(
        "tool.delete_modeling_report",
        {"tool.name": "delete_modeling_report", "tool.output_name": output_name},
    ):
        logger.info("Tool delete_modeling_report invoked output_name=%s", output_name)
        return delete_saved_modeling_report(output_name=output_name)


@mcp.tool()
def rename_modeling_report(
    output_name: str,
    new_output_name: str,
) -> RenamedModelingReport:
    """Rename one saved markdown modeling report inside the local reports directory."""

    with traced_operation(
        "tool.rename_modeling_report",
        {
            "tool.name": "rename_modeling_report",
            "tool.output_name": output_name,
            "tool.new_output_name": new_output_name,
        },
    ):
        logger.info(
            "Tool rename_modeling_report invoked output_name=%s new_output_name=%s",
            output_name,
            new_output_name,
        )
        return rename_saved_modeling_report(
            output_name=output_name,
            new_output_name=new_output_name,
        )


@mcp.tool()
def copy_modeling_report(
    output_name: str,
    new_output_name: str,
) -> CopiedModelingReport:
    """Copy one saved markdown modeling report inside the local reports directory."""

    with traced_operation(
        "tool.copy_modeling_report",
        {
            "tool.name": "copy_modeling_report",
            "tool.output_name": output_name,
            "tool.new_output_name": new_output_name,
        },
    ):
        logger.info(
            "Tool copy_modeling_report invoked output_name=%s new_output_name=%s",
            output_name,
            new_output_name,
        )
        return copy_saved_modeling_report(
            output_name=output_name,
            new_output_name=new_output_name,
        )


@mcp.tool()
def copy_latest_modeling_report_tool(new_output_name: str) -> CopiedModelingReport:
    """Copy the most recently modified saved markdown modeling report."""

    with traced_operation(
        "tool.copy_latest_modeling_report",
        {
            "tool.name": "copy_latest_modeling_report",
            "tool.new_output_name": new_output_name,
        },
    ):
        logger.info(
            "Tool copy_latest_modeling_report_tool invoked new_output_name=%s",
            new_output_name,
        )
        return copy_latest_modeling_report(new_output_name=new_output_name)


@mcp.tool()
def inspect_modeling_report(output_name: str) -> ModelingReportMetadata:
    """Return metadata for one saved markdown modeling report."""

    with traced_operation(
        "tool.inspect_modeling_report",
        {"tool.name": "inspect_modeling_report", "tool.output_name": output_name},
    ):
        logger.info("Tool inspect_modeling_report invoked output_name=%s", output_name)
        return inspect_saved_modeling_report(output_name=output_name)


@mcp.tool()
def inspect_latest_modeling_report_tool() -> ModelingReportMetadata:
    """Return metadata for the most recently modified saved markdown modeling report."""

    with traced_operation(
        "tool.inspect_latest_modeling_report",
        {"tool.name": "inspect_latest_modeling_report"},
    ):
        logger.info("Tool inspect_latest_modeling_report_tool invoked")
        return inspect_latest_modeling_report()


@mcp.tool()
def preview_modeling_report(output_name: str) -> PreviewModelingReport:
    """Return a bounded preview of one saved markdown modeling report."""

    with traced_operation(
        "tool.preview_modeling_report",
        {"tool.name": "preview_modeling_report", "tool.output_name": output_name},
    ):
        logger.info("Tool preview_modeling_report invoked output_name=%s", output_name)
        return preview_saved_modeling_report(output_name=output_name)


@mcp.tool()
def compare_modeling_reports(
    output_name: str,
    other_output_name: str,
) -> ComparedModelingReport:
    """Return a bounded unified diff summary between two saved modeling reports."""

    with traced_operation(
        "tool.compare_modeling_reports",
        {
            "tool.name": "compare_modeling_reports",
            "tool.output_name": output_name,
            "tool.other_output_name": other_output_name,
        },
    ):
        logger.info(
            "Tool compare_modeling_reports invoked output_name=%s other_output_name=%s",
            output_name,
            other_output_name,
        )
        return compare_saved_modeling_reports(
            output_name=output_name,
            other_output_name=other_output_name,
        )


@mcp.tool()
def compare_latest_modeling_reports_tool() -> ComparedModelingReport:
    """Return a bounded diff summary between the two most recent reports."""

    with traced_operation(
        "tool.compare_latest_modeling_reports",
        {"tool.name": "compare_latest_modeling_reports"},
    ):
        logger.info("Tool compare_latest_modeling_reports_tool invoked")
        return compare_latest_modeling_reports()


@mcp.tool()
def preview_latest_modeling_report_tool() -> PreviewModelingReport:
    """Return a bounded preview of the most recently modified modeling report."""

    with traced_operation(
        "tool.preview_latest_modeling_report",
        {"tool.name": "preview_latest_modeling_report"},
    ):
        logger.info("Tool preview_latest_modeling_report_tool invoked")
        return preview_latest_modeling_report()


@mcp.tool()
def query_csv_with_duckdb(
    file_name: str,
    sql: str,
    limit: int | None = None,
) -> DuckDBQueryResult:
    """
    Run a safe read-only DuckDB query against a CSV dataset.

    Args:
        file_name: CSV file name inside the configured data directory.
        sql: A single SELECT or WITH query against the `dataset` table.
        limit: Optional maximum number of rows to return.

    Returns:
        Structured query results with bounded rows and column names.
    """

    with traced_operation(
        "tool.query_csv_with_duckdb",
        {"tool.name": "query_csv_with_duckdb", "dataset.file_name": file_name, "tool.limit": limit},
    ):
        logger.info(
            "Tool query_csv_with_duckdb invoked file_name=%s limit=%s",
            file_name,
            limit,
        )
        return query_csv_with_duckdb_dataset(file_name=file_name, sql=sql, limit=limit)


@mcp.tool()
def list_sqlite_databases_tool() -> list[SQLiteDatabaseInfo]:
    """Return SQLite database files available in the configured data directory."""

    with traced_operation("tool.list_sqlite_databases", {"tool.name": "list_sqlite_databases"}):
        logger.info("Tool list_sqlite_databases_tool invoked")
        return [SQLiteDatabaseInfo(file_name=file_name) for file_name in list_sqlite_files()]


@mcp.tool()
def list_sqlite_tables(file_name: str) -> list[str]:
    """List user tables from a SQLite database."""

    with traced_operation(
        "tool.list_sqlite_tables",
        {"tool.name": "list_sqlite_tables", "dataset.file_name": file_name},
    ):
        logger.info("Tool list_sqlite_tables invoked file_name=%s", file_name)
        return list_sqlite_tables_dataset(file_name=file_name)


@mcp.tool()
def describe_sqlite_table(file_name: str, table_name: str) -> SQLiteTableSchema:
    """Describe a SQLite table schema."""

    with traced_operation(
        "tool.describe_sqlite_table",
        {
            "tool.name": "describe_sqlite_table",
            "dataset.file_name": file_name,
            "sqlite.table_name": table_name,
        },
    ):
        logger.info(
            "Tool describe_sqlite_table invoked file_name=%s table_name=%s",
            file_name,
            table_name,
        )
        return describe_sqlite_table_dataset(file_name=file_name, table_name=table_name)


@mcp.tool()
def query_sqlite(
    file_name: str,
    sql: str,
    limit: int | None = None,
) -> SQLiteQueryResult:
    """Run a safe read-only SQLite query against a database in the data directory."""

    with traced_operation(
        "tool.query_sqlite",
        {"tool.name": "query_sqlite", "dataset.file_name": file_name, "tool.limit": limit},
    ):
        logger.info("Tool query_sqlite invoked file_name=%s limit=%s", file_name, limit)
        return query_sqlite_database(file_name=file_name, sql=sql, limit=limit)


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
def evaluate_baseline_model(
    file_name: str,
    target_column: str,
    task_type: str,
    test_size: float = 0.2,
    random_state: int = 42,
) -> BaselineEvaluationResult:
    """Evaluate a dummy baseline model for a supervised learning task."""

    with traced_operation(
        "tool.evaluate_baseline_model",
        {
            "tool.name": "evaluate_baseline_model",
            "dataset.file_name": file_name,
            "tool.target_column": target_column,
            "tool.task_type": task_type,
        },
    ):
        logger.info(
            "Tool evaluate_baseline_model invoked file_name=%s target_column=%s task_type=%s",
            file_name,
            target_column,
            task_type,
        )
        return evaluate_baseline_model_dataset(
            file_name=file_name,
            target_column=target_column,
            task_type=task_type,
            test_size=test_size,
            random_state=random_state,
        )


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

    with traced_operation(
        "prompt.dataset_analysis_prompt",
        {
            "prompt.name": "dataset_analysis_prompt",
            "dataset.file_name": file_name,
            "prompt.objective_length": len(objective),
        },
    ):
        logger.info(
            "Prompt dataset_analysis_prompt created file_name=%s objective_length=%s",
            file_name,
            len(objective),
        )
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

    return get_settings().mcp_transport


def main() -> None:
    """Run the MCP server."""

    settings = get_settings()
    configure_logging(settings)
    configure_tracing(settings)
    logger.info(
        "Starting MCP server transport=%s host=%s port=%s auth_enabled=%s",
        settings.mcp_transport,
        settings.mcp_host,
        settings.mcp_port,
        settings.mcp_transport == "streamable-http" and settings.mcp_api_key is not None,
    )
    mcp.run(transport=get_transport())


if __name__ == "__main__":
    main()
