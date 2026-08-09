from __future__ import annotations

import logging

from ds_workspace_mcp.mcp.app import _mcp_resource
from ds_workspace_mcp.report_export import (
    ModelingReportSection,
    list_latest_modeling_report_sections,
    list_saved_modeling_report_sections,
    list_saved_modeling_reports,
    read_latest_modeling_report,
    read_latest_modeling_report_section,
    read_saved_modeling_report,
    read_saved_modeling_report_section,
)
from ds_workspace_mcp.tracing import traced_operation

logger = logging.getLogger(__name__)


@_mcp_resource("reports://modeling")
def list_modeling_reports_resource() -> str:
    """List saved modeling report artifacts from the local reports directory."""

    with traced_operation("resource.list_modeling_reports"):
        reports = list_saved_modeling_reports()
        logger.info("Resource request reports://modeling returned %s reports", len(reports))

        if not reports:
            return "No modeling reports found in the local reports directory."

        return "\n".join(report.output_name for report in reports)


@_mcp_resource("reports://modeling/latest", mime_type="text/markdown")
def latest_modeling_report_resource() -> str:
    """Return the latest saved modeling report as markdown."""

    with traced_operation("resource.latest_modeling_report"):
        reports = list_saved_modeling_reports()
        logger.info("Resource request reports://modeling/latest evaluated %s reports", len(reports))

        if not reports:
            return "No modeling reports found in the local reports directory."

        return read_latest_modeling_report().markdown


@_mcp_resource("reports://modeling/{output_name}", mime_type="text/markdown")
def read_modeling_report_resource(output_name: str) -> str:
    """Return one saved modeling report as markdown."""

    with traced_operation(
        "resource.read_modeling_report",
        {"resource.output_name": output_name},
    ):
        logger.info("Resource request reports://modeling/%s invoked", output_name)
        return read_saved_modeling_report(output_name=output_name).markdown


@_mcp_resource("reports://modeling/latest/sections")
def latest_modeling_report_sections_resource() -> list[ModelingReportSection]:
    """Return section headings from the latest saved modeling report."""

    with traced_operation("resource.latest_modeling_report_sections"):
        sections = list_latest_modeling_report_sections()
        logger.info(
            "Resource request reports://modeling/latest/sections returned %s sections",
            len(sections),
        )
        return sections


@_mcp_resource("reports://modeling/{output_name}/sections")
def modeling_report_sections_resource(output_name: str) -> list[ModelingReportSection]:
    """Return section headings from one saved modeling report."""

    with traced_operation(
        "resource.modeling_report_sections",
        {"resource.output_name": output_name},
    ):
        sections = list_saved_modeling_report_sections(output_name=output_name)
        logger.info(
            "Resource request reports://modeling/%s/sections returned %s sections",
            output_name,
            len(sections),
        )
        return sections


@_mcp_resource("reports://modeling/latest/sections/{section_heading}", mime_type="text/markdown")
def latest_modeling_report_section_resource(section_heading: str) -> str:
    """Return one section from the latest saved modeling report as markdown."""

    with traced_operation(
        "resource.latest_modeling_report_section",
        {"resource.section_heading": section_heading},
    ):
        logger.info(
            "Resource request reports://modeling/latest/sections/%s invoked",
            section_heading,
        )
        return read_latest_modeling_report_section(section_heading=section_heading).markdown


@_mcp_resource(
    "reports://modeling/{output_name}/sections/{section_heading}",
    mime_type="text/markdown",
)
def modeling_report_section_resource(output_name: str, section_heading: str) -> str:
    """Return one section from a saved modeling report as markdown."""

    with traced_operation(
        "resource.modeling_report_section",
        {
            "resource.output_name": output_name,
            "resource.section_heading": section_heading,
        },
    ):
        logger.info(
            "Resource request reports://modeling/%s/sections/%s invoked",
            output_name,
            section_heading,
        )
        return read_saved_modeling_report_section(
            output_name=output_name,
            section_heading=section_heading,
        ).markdown
