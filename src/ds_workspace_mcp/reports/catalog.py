from __future__ import annotations

from pathlib import Path

from ds_workspace_mcp.exceptions import InvalidDatasetNameError

from .constants import MAX_REPORT_DIFF_PREVIEW_LINES, MAX_REPORT_PREVIEW_LINES
from .diff import compare_markdown_lines
from .models import (
    ComparedModelingReport,
    CopiedModelingReport,
    DeletedModelingReport,
    ModelingReportCatalogSummary,
    ModelingReportMetadata,
    PreviewModelingReport,
    ReadModelingReport,
    RenamedModelingReport,
    ReportSearchMatch,
    StoredModelingReport,
)
from .parsing import build_search_snippet, extract_headline
from .paths import get_report_storage, resolve_existing_report_path


def search_saved_modeling_reports(query: str) -> list[StoredModelingReport]:
    """Return saved markdown modeling reports whose names match the query."""

    if not isinstance(query, str) or not query.strip():
        raise InvalidDatasetNameError("query must be a non-empty string.")

    normalized_query = query.strip().lower()
    matches = [
        report
        for report in list_saved_modeling_reports()
        if normalized_query in report.output_name.lower()
    ]
    return sorted(matches, key=lambda report: (report.output_name.lower(), report.output_name))


def search_saved_modeling_report_content(query: str) -> list[ReportSearchMatch]:
    """Return saved modeling reports whose markdown body matches the query."""

    if not isinstance(query, str) or not query.strip():
        raise InvalidDatasetNameError("query must be a non-empty string.")

    normalized_query = query.strip().lower()
    matches: list[ReportSearchMatch] = []
    for report in list_saved_modeling_reports():
        path = Path(report.output_path)
        markdown = path.read_text(encoding="utf-8")
        normalized_markdown = markdown.lower()
        query_index = normalized_markdown.find(normalized_query)
        if query_index < 0:
            continue
        lines = markdown.splitlines()
        matches.append(
            ReportSearchMatch(
                output_name=report.output_name,
                output_path=report.output_path,
                headline=extract_headline(lines),
                snippet=build_search_snippet(markdown, query_index, len(normalized_query)),
            )
        )

    return sorted(matches, key=lambda match: (match.output_name.lower(), match.output_name))


def search_latest_modeling_report_content(query: str) -> list[ReportSearchMatch]:
    """Return a bounded content match from the newest saved modeling report."""

    if not isinstance(query, str) or not query.strip():
        raise InvalidDatasetNameError("query must be a non-empty string.")

    latest_report = get_latest_saved_report()
    return search_saved_modeling_report_content_in_report(
        output_name=latest_report.output_name,
        query=query,
    )


def list_recent_modeling_reports(limit: int = 5) -> list[StoredModelingReport]:
    """Return the most recently modified saved modeling reports."""

    if limit < 1:
        raise InvalidDatasetNameError("limit must be greater than 0.")

    reports = list_saved_modeling_reports()
    return sorted(
        reports,
        key=lambda report: (report.modified_at, report.output_name),
        reverse=True,
    )[:limit]


def summarize_modeling_report_catalog(limit: int = 5) -> ModelingReportCatalogSummary:
    """Return a compact summary of saved markdown modeling reports."""

    if limit < 1:
        raise InvalidDatasetNameError("limit must be greater than 0.")

    reports = list_saved_modeling_reports()
    return ModelingReportCatalogSummary(
        report_count=len(reports),
        total_size_bytes=sum(report.size_bytes for report in reports),
        most_recent_reports=list_recent_modeling_reports(limit=limit),
    )


def read_latest_modeling_report() -> ReadModelingReport:
    """Read the most recently modified saved markdown modeling report."""

    latest_report = get_latest_saved_report()
    return read_saved_modeling_report(latest_report.output_name)


def inspect_latest_modeling_report() -> ModelingReportMetadata:
    """Return metadata for the most recently modified saved markdown modeling report."""

    latest_report = get_latest_saved_report()
    return inspect_saved_modeling_report(latest_report.output_name)


def preview_latest_modeling_report() -> PreviewModelingReport:
    """Return a bounded preview of the most recently modified modeling report."""

    latest_report = get_latest_saved_report()
    return preview_saved_modeling_report(latest_report.output_name)


def compare_saved_modeling_reports(
    output_name: str,
    other_output_name: str,
) -> ComparedModelingReport:
    """Return a bounded unified diff summary between two saved modeling reports."""

    primary_path = resolve_existing_report_path(output_name)
    other_path = resolve_existing_report_path(other_output_name)
    diff_summary = compare_markdown_lines(
        primary_path.read_text(encoding="utf-8").splitlines(),
        other_path.read_text(encoding="utf-8").splitlines(),
        fromfile=primary_path.name,
        tofile=other_path.name,
        max_preview_lines=MAX_REPORT_DIFF_PREVIEW_LINES,
    )
    return ComparedModelingReport(
        output_name=primary_path.name,
        other_output_name=other_path.name,
        changed=diff_summary.changed,
        added_line_count=diff_summary.added_line_count,
        removed_line_count=diff_summary.removed_line_count,
        diff_preview=diff_summary.diff_preview,
    )


def compare_latest_modeling_reports() -> ComparedModelingReport:
    """Return a bounded unified diff summary between the two newest saved reports."""

    recent_reports = list_recent_modeling_reports(limit=2)
    if len(recent_reports) < 2:
        raise InvalidDatasetNameError(
            "At least two modeling reports are required in the local reports directory."
        )
    return compare_saved_modeling_reports(
        output_name=recent_reports[1].output_name,
        other_output_name=recent_reports[0].output_name,
    )


def search_saved_modeling_report_content_in_report(
    output_name: str,
    query: str,
) -> list[ReportSearchMatch]:
    """Return bounded content matches inside one saved modeling report."""

    if not isinstance(query, str) or not query.strip():
        raise InvalidDatasetNameError("query must be a non-empty string.")

    path = resolve_existing_report_path(output_name)
    markdown = path.read_text(encoding="utf-8")
    normalized_query = query.strip().lower()
    normalized_markdown = markdown.lower()
    query_index = normalized_markdown.find(normalized_query)
    if query_index < 0:
        return []

    lines = markdown.splitlines()
    return [
        ReportSearchMatch(
            output_name=path.name,
            output_path=str(path),
            headline=extract_headline(lines),
            snippet=build_search_snippet(markdown, query_index, len(normalized_query)),
        )
    ]


def list_saved_modeling_reports() -> list[StoredModelingReport]:
    """List markdown modeling reports saved inside the local reports directory."""

    return [
        StoredModelingReport(
            output_name=report.output_name,
            output_path=report.output_path,
            size_bytes=report.size_bytes,
            created_at=report.created_at,
            modified_at=report.modified_at,
            content_sha256=report.content_sha256,
        )
        for report in get_report_storage().list_markdown_reports()
    ]


def read_saved_modeling_report(output_name: str) -> ReadModelingReport:
    """Read one saved markdown modeling report from the local reports directory."""

    path = resolve_existing_report_path(output_name)
    return ReadModelingReport(
        output_name=path.name,
        output_path=str(path),
        markdown=path.read_text(encoding="utf-8"),
    )


def delete_saved_modeling_report(output_name: str) -> DeletedModelingReport:
    """Delete one saved markdown modeling report from the local reports directory."""

    path = get_report_storage().delete(output_name)
    return DeletedModelingReport(
        output_name=path.name,
        output_path=str(path),
    )


def rename_saved_modeling_report(
    output_name: str,
    new_output_name: str,
    overwrite: bool = False,
) -> RenamedModelingReport:
    """Rename one saved markdown modeling report inside the reports directory."""

    source_path = resolve_existing_report_path(output_name)
    target_path = get_report_storage().rename(
        output_name,
        new_output_name,
        overwrite=overwrite,
    )
    return RenamedModelingReport(
        old_output_name=source_path.name,
        new_output_name=target_path.name,
        old_output_path=str(source_path),
        new_output_path=str(target_path),
    )


def rename_latest_modeling_report(
    new_output_name: str,
    overwrite: bool = False,
) -> RenamedModelingReport:
    """Rename the most recently modified saved markdown modeling report."""

    latest_report = get_latest_saved_report()
    return rename_saved_modeling_report(
        output_name=latest_report.output_name,
        new_output_name=new_output_name,
        overwrite=overwrite,
    )


def copy_saved_modeling_report(
    output_name: str,
    new_output_name: str,
    overwrite: bool = False,
) -> CopiedModelingReport:
    """Copy one saved markdown modeling report inside the reports directory."""

    source_path = resolve_existing_report_path(output_name)
    target_path = get_report_storage().copy(
        output_name,
        new_output_name,
        overwrite=overwrite,
    )
    return CopiedModelingReport(
        source_output_name=source_path.name,
        new_output_name=target_path.name,
        source_output_path=str(source_path),
        new_output_path=str(target_path),
    )


def copy_latest_modeling_report(
    new_output_name: str,
    overwrite: bool = False,
) -> CopiedModelingReport:
    """Copy the most recently modified saved markdown modeling report."""

    latest_report = get_latest_saved_report()
    return copy_saved_modeling_report(
        output_name=latest_report.output_name,
        new_output_name=new_output_name,
        overwrite=overwrite,
    )


def inspect_saved_modeling_report(output_name: str) -> ModelingReportMetadata:
    """Return metadata for one saved markdown modeling report."""

    metadata = get_report_storage().metadata(output_name, include_hash=True)
    return ModelingReportMetadata(
        output_name=metadata.output_name,
        output_path=metadata.output_path,
        size_bytes=metadata.size_bytes,
        created_at=metadata.created_at,
        metadata_changed_at=metadata.metadata_changed_at,
        modified_at=metadata.modified_at,
        content_sha256=metadata.content_sha256 or "",
    )


def preview_saved_modeling_report(output_name: str) -> PreviewModelingReport:
    """Return a bounded preview of one saved markdown modeling report."""

    path = resolve_existing_report_path(output_name)
    markdown = path.read_text(encoding="utf-8")
    lines = markdown.splitlines()
    preview_markdown = "\n".join(lines[:MAX_REPORT_PREVIEW_LINES])
    return PreviewModelingReport(
        output_name=path.name,
        output_path=str(path),
        headline=extract_headline(lines),
        preview_markdown=preview_markdown,
        line_count=len(lines),
    )


def get_latest_saved_report() -> StoredModelingReport:
    """Return the newest saved modeling report or fail when none exist."""

    reports = list_recent_modeling_reports(limit=1)
    if not reports:
        raise InvalidDatasetNameError("No modeling reports found in the local reports directory.")
    return reports[0]
