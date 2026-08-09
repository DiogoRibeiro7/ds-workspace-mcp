from __future__ import annotations

import logging

from ds_workspace_mcp.mcp.app import _mcp_tool
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
    rename_latest_modeling_report,
    rename_saved_modeling_report,
    save_latest_modeling_report_section,
    save_modeling_report_section,
    search_latest_modeling_report_content,
    search_latest_modeling_report_sections,
    search_saved_modeling_report_content,
    search_saved_modeling_report_sections,
    search_saved_modeling_reports,
    summarize_modeling_report_catalog,
    summarize_saved_modeling_report_sections,
)
from ds_workspace_mcp.tracing import traced_operation

logger = logging.getLogger(__name__)


@_mcp_tool()
def list_modeling_reports() -> list[StoredModelingReport]:
    """Return markdown modeling reports saved inside the local reports directory."""

    with traced_operation("tool.list_modeling_reports", {"tool.name": "list_modeling_reports"}):
        logger.info("Tool list_modeling_reports invoked")
        return list_saved_modeling_reports()


@_mcp_tool()
def search_modeling_reports(query: str) -> list[StoredModelingReport]:
    """Return saved markdown modeling reports whose file names match the query."""

    with traced_operation(
        "tool.search_modeling_reports",
        {"tool.name": "search_modeling_reports", "tool.query": query},
    ):
        logger.info("Tool search_modeling_reports invoked query=%s", query)
        return search_saved_modeling_reports(query=query)


@_mcp_tool()
def search_modeling_report_content(query: str) -> list[ReportSearchMatch]:
    """Return saved modeling reports whose markdown content matches the query."""

    with traced_operation(
        "tool.search_modeling_report_content",
        {"tool.name": "search_modeling_report_content", "tool.query": query},
    ):
        logger.info("Tool search_modeling_report_content invoked query=%s", query)
        return search_saved_modeling_report_content(query=query)


@_mcp_tool()
def search_latest_modeling_report_content_tool(query: str) -> list[ReportSearchMatch]:
    """Return content matches from the newest saved modeling report."""

    with traced_operation(
        "tool.search_latest_modeling_report_content",
        {"tool.name": "search_latest_modeling_report_content", "tool.query": query},
    ):
        logger.info("Tool search_latest_modeling_report_content_tool invoked query=%s", query)
        return search_latest_modeling_report_content(query=query)


@_mcp_tool()
def search_modeling_report_sections(query: str) -> list[ModelingReportSectionMatch]:
    """Search section headings across saved modeling reports."""

    with traced_operation(
        "tool.search_modeling_report_sections",
        {"tool.name": "search_modeling_report_sections", "tool.query": query},
    ):
        logger.info("Tool search_modeling_report_sections invoked query=%s", query)
        return search_saved_modeling_report_sections(query=query)


@_mcp_tool()
def search_latest_modeling_report_sections_tool(query: str) -> list[ModelingReportSectionMatch]:
    """Search section headings inside the newest saved modeling report."""

    with traced_operation(
        "tool.search_latest_modeling_report_sections",
        {"tool.name": "search_latest_modeling_report_sections", "tool.query": query},
    ):
        logger.info("Tool search_latest_modeling_report_sections_tool invoked query=%s", query)
        return search_latest_modeling_report_sections(query=query)


@_mcp_tool()
def summarize_modeling_report_sections() -> list[ModelingReportSectionSummary]:
    """Summarize recurring section headings across saved modeling reports."""

    with traced_operation(
        "tool.summarize_modeling_report_sections",
        {"tool.name": "summarize_modeling_report_sections"},
    ):
        logger.info("Tool summarize_modeling_report_sections invoked")
        return summarize_saved_modeling_report_sections()


@_mcp_tool()
def list_recent_modeling_reports_tool(limit: int = 5) -> list[StoredModelingReport]:
    """Return the most recently modified saved modeling reports."""

    with traced_operation(
        "tool.list_recent_modeling_reports",
        {"tool.name": "list_recent_modeling_reports", "tool.limit": limit},
    ):
        logger.info("Tool list_recent_modeling_reports_tool invoked limit=%s", limit)
        return list_recent_modeling_reports(limit=limit)


@_mcp_tool()
def summarize_modeling_report_catalog_tool(limit: int = 5) -> ModelingReportCatalogSummary:
    """Return a compact summary of saved modeling report artifacts."""

    with traced_operation(
        "tool.summarize_modeling_report_catalog",
        {"tool.name": "summarize_modeling_report_catalog", "tool.limit": limit},
    ):
        logger.info("Tool summarize_modeling_report_catalog_tool invoked limit=%s", limit)
        return summarize_modeling_report_catalog(limit=limit)


@_mcp_tool()
def read_modeling_report(output_name: str) -> ReadModelingReport:
    """Read one saved markdown modeling report from the local reports directory."""

    with traced_operation(
        "tool.read_modeling_report",
        {"tool.name": "read_modeling_report", "tool.output_name": output_name},
    ):
        logger.info("Tool read_modeling_report invoked output_name=%s", output_name)
        return read_saved_modeling_report(output_name=output_name)


@_mcp_tool()
def list_modeling_report_sections(output_name: str) -> list[ModelingReportSection]:
    """List markdown sections discovered inside one saved modeling report."""

    with traced_operation(
        "tool.list_modeling_report_sections",
        {"tool.name": "list_modeling_report_sections", "tool.output_name": output_name},
    ):
        logger.info("Tool list_modeling_report_sections invoked output_name=%s", output_name)
        return list_saved_modeling_report_sections(output_name=output_name)


@_mcp_tool()
def list_latest_modeling_report_sections_tool() -> list[ModelingReportSection]:
    """List markdown sections discovered inside the newest saved modeling report."""

    with traced_operation(
        "tool.list_latest_modeling_report_sections",
        {"tool.name": "list_latest_modeling_report_sections"},
    ):
        logger.info("Tool list_latest_modeling_report_sections_tool invoked")
        return list_latest_modeling_report_sections()


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
def save_modeling_report_section_tool(
    output_name: str,
    section_heading: str,
    new_output_name: str | None = None,
    overwrite: bool = False,
) -> SavedModelingReportSection:
    """Save one markdown section from a report as a new markdown artifact."""

    with traced_operation(
        "tool.save_modeling_report_section",
        {
            "tool.name": "save_modeling_report_section",
            "tool.output_name": output_name,
            "tool.section_heading": section_heading,
            "tool.new_output_name": new_output_name,
            "tool.overwrite": overwrite,
        },
    ):
        logger.info(
            "Tool save_modeling_report_section_tool invoked "
            "output_name=%s section_heading=%s new_output_name=%s overwrite=%s",
            output_name,
            section_heading,
            new_output_name,
            overwrite,
        )
        return save_modeling_report_section(
            output_name=output_name,
            section_heading=section_heading,
            new_output_name=new_output_name,
            overwrite=overwrite,
        )


@_mcp_tool()
def save_latest_modeling_report_section_tool(
    section_heading: str,
    new_output_name: str | None = None,
    overwrite: bool = False,
) -> SavedModelingReportSection:
    """Save one section from the newest report as a new markdown artifact."""

    with traced_operation(
        "tool.save_latest_modeling_report_section",
        {
            "tool.name": "save_latest_modeling_report_section",
            "tool.section_heading": section_heading,
            "tool.new_output_name": new_output_name,
            "tool.overwrite": overwrite,
        },
    ):
        logger.info(
            "Tool save_latest_modeling_report_section_tool invoked "
            "section_heading=%s new_output_name=%s overwrite=%s",
            section_heading,
            new_output_name,
            overwrite,
        )
        return save_latest_modeling_report_section(
            section_heading=section_heading,
            new_output_name=new_output_name,
            overwrite=overwrite,
        )


@_mcp_tool()
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


@_mcp_tool()
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


@_mcp_tool()
def read_latest_modeling_report_tool() -> ReadModelingReport:
    """Read the most recently modified saved markdown modeling report."""

    with traced_operation(
        "tool.read_latest_modeling_report",
        {"tool.name": "read_latest_modeling_report"},
    ):
        logger.info("Tool read_latest_modeling_report_tool invoked")
        return read_latest_modeling_report()


@_mcp_tool()
def delete_modeling_report(output_name: str) -> DeletedModelingReport:
    """Delete one saved markdown modeling report from the local reports directory."""

    with traced_operation(
        "tool.delete_modeling_report",
        {"tool.name": "delete_modeling_report", "tool.output_name": output_name},
    ):
        logger.info("Tool delete_modeling_report invoked output_name=%s", output_name)
        return delete_saved_modeling_report(output_name=output_name)


@_mcp_tool()
def rename_modeling_report(
    output_name: str,
    new_output_name: str,
    overwrite: bool = False,
) -> RenamedModelingReport:
    """Rename one saved markdown modeling report inside the local reports directory."""

    with traced_operation(
        "tool.rename_modeling_report",
        {
            "tool.name": "rename_modeling_report",
            "tool.output_name": output_name,
            "tool.new_output_name": new_output_name,
            "tool.overwrite": overwrite,
        },
    ):
        logger.info(
            "Tool rename_modeling_report invoked output_name=%s new_output_name=%s " "overwrite=%s",
            output_name,
            new_output_name,
            overwrite,
        )
        return rename_saved_modeling_report(
            output_name=output_name,
            new_output_name=new_output_name,
            overwrite=overwrite,
        )


@_mcp_tool()
def rename_latest_modeling_report_tool(
    new_output_name: str,
    overwrite: bool = False,
) -> RenamedModelingReport:
    """Rename the most recently modified saved markdown modeling report."""

    with traced_operation(
        "tool.rename_latest_modeling_report",
        {
            "tool.name": "rename_latest_modeling_report",
            "tool.new_output_name": new_output_name,
            "tool.overwrite": overwrite,
        },
    ):
        logger.info(
            "Tool rename_latest_modeling_report_tool invoked new_output_name=%s overwrite=%s",
            new_output_name,
            overwrite,
        )
        return rename_latest_modeling_report(new_output_name=new_output_name, overwrite=overwrite)


@_mcp_tool()
def copy_modeling_report(
    output_name: str,
    new_output_name: str,
    overwrite: bool = False,
) -> CopiedModelingReport:
    """Copy one saved markdown modeling report inside the local reports directory."""

    with traced_operation(
        "tool.copy_modeling_report",
        {
            "tool.name": "copy_modeling_report",
            "tool.output_name": output_name,
            "tool.new_output_name": new_output_name,
            "tool.overwrite": overwrite,
        },
    ):
        logger.info(
            "Tool copy_modeling_report invoked output_name=%s new_output_name=%s overwrite=%s",
            output_name,
            new_output_name,
            overwrite,
        )
        return copy_saved_modeling_report(
            output_name=output_name,
            new_output_name=new_output_name,
            overwrite=overwrite,
        )


@_mcp_tool()
def copy_latest_modeling_report_tool(
    new_output_name: str,
    overwrite: bool = False,
) -> CopiedModelingReport:
    """Copy the most recently modified saved markdown modeling report."""

    with traced_operation(
        "tool.copy_latest_modeling_report",
        {
            "tool.name": "copy_latest_modeling_report",
            "tool.new_output_name": new_output_name,
            "tool.overwrite": overwrite,
        },
    ):
        logger.info(
            "Tool copy_latest_modeling_report_tool invoked new_output_name=%s overwrite=%s",
            new_output_name,
            overwrite,
        )
        return copy_latest_modeling_report(new_output_name=new_output_name, overwrite=overwrite)


@_mcp_tool()
def inspect_modeling_report(output_name: str) -> ModelingReportMetadata:
    """Return metadata for one saved markdown modeling report."""

    with traced_operation(
        "tool.inspect_modeling_report",
        {"tool.name": "inspect_modeling_report", "tool.output_name": output_name},
    ):
        logger.info("Tool inspect_modeling_report invoked output_name=%s", output_name)
        return inspect_saved_modeling_report(output_name=output_name)


@_mcp_tool()
def inspect_latest_modeling_report_tool() -> ModelingReportMetadata:
    """Return metadata for the most recently modified saved markdown modeling report."""

    with traced_operation(
        "tool.inspect_latest_modeling_report",
        {"tool.name": "inspect_latest_modeling_report"},
    ):
        logger.info("Tool inspect_latest_modeling_report_tool invoked")
        return inspect_latest_modeling_report()


@_mcp_tool()
def preview_modeling_report(output_name: str) -> PreviewModelingReport:
    """Return a bounded preview of one saved markdown modeling report."""

    with traced_operation(
        "tool.preview_modeling_report",
        {"tool.name": "preview_modeling_report", "tool.output_name": output_name},
    ):
        logger.info("Tool preview_modeling_report invoked output_name=%s", output_name)
        return preview_saved_modeling_report(output_name=output_name)


@_mcp_tool()
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


@_mcp_tool()
def compare_latest_modeling_reports_tool() -> ComparedModelingReport:
    """Return a bounded diff summary between the two most recent reports."""

    with traced_operation(
        "tool.compare_latest_modeling_reports",
        {"tool.name": "compare_latest_modeling_reports"},
    ):
        logger.info("Tool compare_latest_modeling_reports_tool invoked")
        return compare_latest_modeling_reports()


@_mcp_tool()
def preview_latest_modeling_report_tool() -> PreviewModelingReport:
    """Return a bounded preview of the most recently modified modeling report."""

    with traced_operation(
        "tool.preview_latest_modeling_report",
        {"tool.name": "preview_latest_modeling_report"},
    ):
        logger.info("Tool preview_latest_modeling_report_tool invoked")
        return preview_latest_modeling_report()
