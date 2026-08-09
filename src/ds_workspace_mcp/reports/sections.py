from __future__ import annotations

from pathlib import Path

from ds_workspace_mcp.exceptions import InvalidDatasetNameError

from .catalog import (
    get_latest_saved_report,
    list_recent_modeling_reports,
    list_saved_modeling_reports,
)
from .constants import MAX_REPORT_DIFF_PREVIEW_LINES, MAX_REPORT_SECTION_SUMMARY_EXAMPLES
from .diff import compare_markdown_lines
from .models import (
    ComparedModelingReportSection,
    ModelingReportSection,
    ModelingReportSectionMatch,
    ModelingReportSectionSummary,
    ReadModelingReportSection,
    SavedModelingReportSection,
)
from .parsing import build_section_snippet, extract_markdown_sections
from .paths import default_section_output_name, get_report_storage, resolve_existing_report_path


def list_latest_modeling_report_sections() -> list[ModelingReportSection]:
    """List markdown sections discovered inside the newest saved modeling report."""

    latest_report = get_latest_saved_report()
    return list_saved_modeling_report_sections(latest_report.output_name)


def list_saved_modeling_report_sections(output_name: str) -> list[ModelingReportSection]:
    """List markdown sections discovered inside one saved modeling report."""

    path = resolve_existing_report_path(output_name)
    lines = path.read_text(encoding="utf-8").splitlines()
    return [
        ModelingReportSection(heading=section.heading, level=section.level)
        for section in extract_markdown_sections(lines)
    ]


def read_saved_modeling_report_section(
    output_name: str,
    section_heading: str,
) -> ReadModelingReportSection:
    """Read one markdown section from a saved modeling report."""

    if not isinstance(section_heading, str) or not section_heading.strip():
        raise InvalidDatasetNameError("section_heading must be a non-empty string.")

    path = resolve_existing_report_path(output_name)
    lines = path.read_text(encoding="utf-8").splitlines()
    normalized_heading = section_heading.strip().lower()
    for section in extract_markdown_sections(lines):
        if section.heading.lower() == normalized_heading:
            return ReadModelingReportSection(
                output_name=path.name,
                output_path=str(path),
                heading=section.heading,
                level=section.level,
                markdown="\n".join(section.lines),
            )

    raise InvalidDatasetNameError(f"Modeling report section not found: {section_heading}")


def read_latest_modeling_report_section(section_heading: str) -> ReadModelingReportSection:
    """Read one markdown section from the newest saved modeling report."""

    latest_report = get_latest_saved_report()
    return read_saved_modeling_report_section(
        output_name=latest_report.output_name,
        section_heading=section_heading,
    )


def search_saved_modeling_report_sections(query: str) -> list[ModelingReportSectionMatch]:
    """Search section headings across saved modeling reports."""

    if not isinstance(query, str) or not query.strip():
        raise InvalidDatasetNameError("query must be a non-empty string.")

    normalized_query = query.strip().lower()
    matches: list[ModelingReportSectionMatch] = []
    for report in list_saved_modeling_reports():
        path = Path(report.output_path)
        lines = path.read_text(encoding="utf-8").splitlines()
        for section in extract_markdown_sections(lines):
            if normalized_query not in section.heading.lower():
                continue
            matches.append(
                ModelingReportSectionMatch(
                    output_name=report.output_name,
                    output_path=report.output_path,
                    heading=section.heading,
                    level=section.level,
                    snippet=build_section_snippet(section.lines),
                )
            )

    return _sort_section_matches(matches)


def search_latest_modeling_report_sections(query: str) -> list[ModelingReportSectionMatch]:
    """Search section headings inside the newest saved modeling report."""

    if not isinstance(query, str) or not query.strip():
        raise InvalidDatasetNameError("query must be a non-empty string.")

    latest_report = get_latest_saved_report()
    return search_saved_modeling_report_sections_in_report(
        output_name=latest_report.output_name,
        query=query,
    )


def search_saved_modeling_report_sections_in_report(
    output_name: str,
    query: str,
) -> list[ModelingReportSectionMatch]:
    """Search section headings inside one saved modeling report."""

    if not isinstance(query, str) or not query.strip():
        raise InvalidDatasetNameError("query must be a non-empty string.")

    path = resolve_existing_report_path(output_name)
    normalized_query = query.strip().lower()
    matches: list[ModelingReportSectionMatch] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for section in extract_markdown_sections(lines):
        if normalized_query not in section.heading.lower():
            continue
        matches.append(
            ModelingReportSectionMatch(
                output_name=path.name,
                output_path=str(path),
                heading=section.heading,
                level=section.level,
                snippet=build_section_snippet(section.lines),
            )
        )

    return _sort_section_matches(matches)


def save_modeling_report_section(
    output_name: str,
    section_heading: str,
    new_output_name: str | None = None,
    overwrite: bool = False,
) -> SavedModelingReportSection:
    """Persist one extracted report section as a new markdown artifact."""

    section = read_saved_modeling_report_section(
        output_name=output_name,
        section_heading=section_heading,
    )
    target_output_name = new_output_name or default_section_output_name(
        output_name=output_name,
        section_heading=section.heading,
    )
    target_path = get_report_storage().write_text(
        target_output_name,
        section.markdown,
        overwrite=overwrite,
    )
    return SavedModelingReportSection(
        source_output_name=section.output_name,
        section_heading=section.heading,
        output_path=str(target_path),
    )


def save_latest_modeling_report_section(
    section_heading: str,
    new_output_name: str | None = None,
    overwrite: bool = False,
) -> SavedModelingReportSection:
    """Persist one section from the newest saved report as a markdown artifact."""

    latest_report = get_latest_saved_report()
    return save_modeling_report_section(
        output_name=latest_report.output_name,
        section_heading=section_heading,
        new_output_name=new_output_name,
        overwrite=overwrite,
    )


def compare_saved_modeling_report_sections(
    output_name: str,
    other_output_name: str,
    section_heading: str,
) -> ComparedModelingReportSection:
    """Return a bounded diff summary between matching sections in two reports."""

    primary_section = read_saved_modeling_report_section(
        output_name=output_name,
        section_heading=section_heading,
    )
    other_section = read_saved_modeling_report_section(
        output_name=other_output_name,
        section_heading=section_heading,
    )
    diff_summary = compare_markdown_lines(
        primary_section.markdown.splitlines(),
        other_section.markdown.splitlines(),
        fromfile=f"{primary_section.output_name}:{primary_section.heading}",
        tofile=f"{other_section.output_name}:{other_section.heading}",
        max_preview_lines=MAX_REPORT_DIFF_PREVIEW_LINES,
    )
    return ComparedModelingReportSection(
        output_name=primary_section.output_name,
        other_output_name=other_section.output_name,
        section_heading=primary_section.heading,
        changed=diff_summary.changed,
        added_line_count=diff_summary.added_line_count,
        removed_line_count=diff_summary.removed_line_count,
        diff_preview=diff_summary.diff_preview,
    )


def compare_latest_modeling_report_sections(section_heading: str) -> ComparedModelingReportSection:
    """Return a bounded diff summary for one section across the two newest reports."""

    recent_reports = list_recent_modeling_reports(limit=2)
    if len(recent_reports) < 2:
        raise InvalidDatasetNameError(
            "At least two modeling reports are required in the local reports directory."
        )
    return compare_saved_modeling_report_sections(
        output_name=recent_reports[1].output_name,
        other_output_name=recent_reports[0].output_name,
        section_heading=section_heading,
    )


def summarize_saved_modeling_report_sections() -> list[ModelingReportSectionSummary]:
    """Summarize recurring section headings across saved modeling reports."""

    grouped_sections: dict[tuple[str, int], list[str]] = {}
    for report in list_saved_modeling_reports():
        path = Path(report.output_path)
        lines = path.read_text(encoding="utf-8").splitlines()
        seen_in_report: set[tuple[str, int]] = set()
        for section in extract_markdown_sections(lines):
            key = (section.heading, section.level)
            if key in seen_in_report:
                continue
            seen_in_report.add(key)
            grouped_sections.setdefault(key, []).append(report.output_name)

    summaries = [
        ModelingReportSectionSummary(
            heading=heading,
            level=level,
            report_count=len(report_names),
            example_reports=sorted(report_names, key=str.lower)[
                :MAX_REPORT_SECTION_SUMMARY_EXAMPLES
            ],
        )
        for (heading, level), report_names in grouped_sections.items()
    ]
    return sorted(
        summaries,
        key=lambda summary: (-summary.report_count, summary.level, summary.heading.lower()),
    )


def _sort_section_matches(
    matches: list[ModelingReportSectionMatch],
) -> list[ModelingReportSectionMatch]:
    return sorted(
        matches,
        key=lambda match: (
            match.heading.lower(),
            match.output_name.lower(),
            match.output_name,
        ),
    )
