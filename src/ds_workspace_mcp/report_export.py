from __future__ import annotations

from datetime import UTC, datetime
from difflib import unified_diff
from pathlib import Path

from pydantic import BaseModel

from ds_workspace_mcp.exceptions import InvalidDatasetNameError, PathTraversalError
from ds_workspace_mcp.modeling_report import build_modeling_report_dataset

REPORTS_DIR = Path("reports")


class SavedModelingReport(BaseModel):
    """Metadata for a saved modeling report artifact."""

    file_name: str
    target_column: str
    output_path: str
    headline: str


class StoredModelingReport(BaseModel):
    """A saved modeling report discovered from the reports directory."""

    output_name: str
    output_path: str
    size_bytes: int
    modified_at: str


class ReadModelingReport(BaseModel):
    """A saved modeling report loaded from the reports directory."""

    output_name: str
    output_path: str
    markdown: str


class DeletedModelingReport(BaseModel):
    """Metadata for a deleted modeling report artifact."""

    output_name: str
    output_path: str


class RenamedModelingReport(BaseModel):
    """Metadata for a renamed modeling report artifact."""

    old_output_name: str
    new_output_name: str
    old_output_path: str
    new_output_path: str


class ModelingReportMetadata(BaseModel):
    """Metadata summary for one saved modeling report artifact."""

    output_name: str
    output_path: str
    size_bytes: int
    created_at: str
    modified_at: str


class PreviewModelingReport(BaseModel):
    """A bounded preview of one saved modeling report artifact."""

    output_name: str
    output_path: str
    headline: str
    preview_markdown: str
    line_count: int


class ModelingReportCatalogSummary(BaseModel):
    """Summary of the local modeling report catalog."""

    report_count: int
    total_size_bytes: int
    most_recent_reports: list[StoredModelingReport]


class ComparedModelingReport(BaseModel):
    """A bounded diff summary between two saved modeling reports."""

    output_name: str
    other_output_name: str
    changed: bool
    added_line_count: int
    removed_line_count: int
    diff_preview: str


class ReportSearchMatch(BaseModel):
    """A bounded full-text search match inside one saved modeling report."""

    output_name: str
    output_path: str
    headline: str
    snippet: str


MAX_REPORT_PREVIEW_LINES = 12
MAX_REPORT_DIFF_PREVIEW_LINES = 40
MAX_REPORT_SEARCH_SNIPPET_LENGTH = 200


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
                headline=_extract_headline(lines),
                snippet=_build_search_snippet(markdown, query_index, len(normalized_query)),
            )
        )

    return sorted(matches, key=lambda match: (match.output_name.lower(), match.output_name))


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

    latest_report = _get_latest_saved_report()
    return read_saved_modeling_report(latest_report.output_name)


def preview_latest_modeling_report() -> PreviewModelingReport:
    """Return a bounded preview of the most recently modified modeling report."""

    latest_report = _get_latest_saved_report()
    return preview_saved_modeling_report(latest_report.output_name)


def compare_saved_modeling_reports(
    output_name: str,
    other_output_name: str,
) -> ComparedModelingReport:
    """Return a bounded unified diff summary between two saved modeling reports."""

    primary_path = resolve_existing_report_path(output_name)
    other_path = resolve_existing_report_path(other_output_name)
    primary_lines = primary_path.read_text(encoding="utf-8").splitlines()
    other_lines = other_path.read_text(encoding="utf-8").splitlines()
    diff_lines = list(
        unified_diff(
            primary_lines,
            other_lines,
            fromfile=primary_path.name,
            tofile=other_path.name,
            lineterm="",
        )
    )
    added_line_count = sum(
        1
        for line in diff_lines
        if line.startswith("+") and not line.startswith("+++")
    )
    removed_line_count = sum(
        1
        for line in diff_lines
        if line.startswith("-") and not line.startswith("---")
    )
    preview_lines = diff_lines[:MAX_REPORT_DIFF_PREVIEW_LINES]
    return ComparedModelingReport(
        output_name=primary_path.name,
        other_output_name=other_path.name,
        changed=bool(diff_lines),
        added_line_count=added_line_count,
        removed_line_count=removed_line_count,
        diff_preview="\n".join(preview_lines),
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


def save_modeling_report_dataset(
    file_name: str,
    target_column: str | None = None,
    output_name: str | None = None,
) -> SavedModelingReport:
    """Build and persist a modeling report inside the local reports directory."""

    report = build_modeling_report_dataset(
        file_name=file_name,
        target_column=target_column,
    )
    output_path = resolve_report_output_path(
        file_name=file_name,
        target_column=report.target_column,
        output_name=output_name,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.markdown, encoding="utf-8")
    return SavedModelingReport(
        file_name=file_name,
        target_column=report.target_column,
        output_path=str(output_path),
        headline=report.headline,
    )


def list_saved_modeling_reports() -> list[StoredModelingReport]:
    """List markdown modeling reports saved inside the local reports directory."""

    reports_root = REPORTS_DIR.resolve()
    reports_root.mkdir(parents=True, exist_ok=True)
    reports: list[StoredModelingReport] = []
    for path in sorted(reports_root.glob("*.md")):
        if not path.is_file():
            continue
        stat = path.stat()
        reports.append(
            StoredModelingReport(
                output_name=path.name,
                output_path=str(path.resolve()),
                size_bytes=stat.st_size,
                modified_at=_format_timestamp(stat.st_mtime),
            )
        )
    return reports


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

    path = resolve_existing_report_path(output_name)
    path.unlink()
    return DeletedModelingReport(
        output_name=path.name,
        output_path=str(path),
    )


def rename_saved_modeling_report(
    output_name: str,
    new_output_name: str,
) -> RenamedModelingReport:
    """Rename one saved markdown modeling report inside the local reports directory."""

    source_path = resolve_existing_report_path(output_name)
    target_path = resolve_report_target_path(new_output_name)
    if target_path.exists():
        raise InvalidDatasetNameError(f"Modeling report already exists: {new_output_name}")

    source_path.rename(target_path)
    return RenamedModelingReport(
        old_output_name=source_path.name,
        new_output_name=target_path.name,
        old_output_path=str(source_path),
        new_output_path=str(target_path),
    )


def inspect_saved_modeling_report(output_name: str) -> ModelingReportMetadata:
    """Return metadata for one saved markdown modeling report."""

    path = resolve_existing_report_path(output_name)
    stat = path.stat()
    return ModelingReportMetadata(
        output_name=path.name,
        output_path=str(path),
        size_bytes=stat.st_size,
        created_at=_format_timestamp(stat.st_ctime),
        modified_at=_format_timestamp(stat.st_mtime),
    )


def preview_saved_modeling_report(output_name: str) -> PreviewModelingReport:
    """Return a bounded preview of one saved markdown modeling report."""

    path = resolve_existing_report_path(output_name)
    markdown = path.read_text(encoding="utf-8")
    lines = markdown.splitlines()
    headline = _extract_headline(lines)
    preview_lines = lines[:MAX_REPORT_PREVIEW_LINES]
    preview_markdown = "\n".join(preview_lines)
    return PreviewModelingReport(
        output_name=path.name,
        output_path=str(path),
        headline=headline,
        preview_markdown=preview_markdown,
        line_count=len(lines),
    )


def resolve_report_output_path(
    file_name: str,
    target_column: str,
    output_name: str | None = None,
) -> Path:
    """Resolve a safe markdown output path inside the reports directory."""

    reports_root = REPORTS_DIR.resolve()
    reports_root.mkdir(parents=True, exist_ok=True)

    candidate_name = output_name or _default_output_name(file_name, target_column)
    if not isinstance(candidate_name, str) or not candidate_name.strip():
        raise InvalidDatasetNameError("output_name must be a non-empty string.")
    if Path(candidate_name).name != candidate_name:
        raise PathTraversalError("Report output must stay inside the reports directory.")
    if not candidate_name.lower().endswith(".md"):
        raise InvalidDatasetNameError("Report output_name must end with .md.")

    resolved = (reports_root / candidate_name).resolve()
    if resolved.parent != reports_root:
        raise PathTraversalError("Report output must stay inside the reports directory.")
    return resolved


def resolve_existing_report_path(output_name: str) -> Path:
    """Resolve one existing markdown report inside the reports directory."""

    reports_root = REPORTS_DIR.resolve()
    reports_root.mkdir(parents=True, exist_ok=True)

    if not isinstance(output_name, str) or not output_name.strip():
        raise InvalidDatasetNameError("output_name must be a non-empty string.")
    if Path(output_name).name != output_name:
        raise PathTraversalError("Report output must stay inside the reports directory.")
    if not output_name.lower().endswith(".md"):
        raise InvalidDatasetNameError("Report output_name must end with .md.")

    resolved = (reports_root / output_name).resolve()
    if resolved.parent != reports_root:
        raise PathTraversalError("Report output must stay inside the reports directory.")
    if not resolved.exists():
        raise InvalidDatasetNameError(f"Modeling report not found: {output_name}")
    return resolved


def resolve_report_target_path(output_name: str) -> Path:
    """Resolve a target markdown report path inside the reports directory."""

    reports_root = REPORTS_DIR.resolve()
    reports_root.mkdir(parents=True, exist_ok=True)

    if not isinstance(output_name, str) or not output_name.strip():
        raise InvalidDatasetNameError("output_name must be a non-empty string.")
    if Path(output_name).name != output_name:
        raise PathTraversalError("Report output must stay inside the reports directory.")
    if not output_name.lower().endswith(".md"):
        raise InvalidDatasetNameError("Report output_name must end with .md.")

    resolved = (reports_root / output_name).resolve()
    if resolved.parent != reports_root:
        raise PathTraversalError("Report output must stay inside the reports directory.")
    return resolved


def _default_output_name(file_name: str, target_column: str) -> str:
    """Build a stable default markdown file name for a report artifact."""

    dataset_stem = Path(file_name).stem
    safe_dataset = _slugify(dataset_stem)
    safe_target = _slugify(target_column)
    return f"{safe_dataset}--{safe_target}--modeling-report.md"


def _slugify(value: str) -> str:
    """Convert free text into a conservative file-name slug."""

    cleaned = "".join(character.lower() if character.isalnum() else "-" for character in value)
    collapsed = "-".join(part for part in cleaned.split("-") if part)
    return collapsed or "report"


def _format_timestamp(timestamp: float) -> str:
    """Convert filesystem timestamps into UTC ISO-8601 strings."""

    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


def _extract_headline(lines: list[str]) -> str:
    """Extract a human-readable report headline from markdown lines."""

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.removeprefix("# ").strip()
    return "Untitled modeling report"


def _get_latest_saved_report() -> StoredModelingReport:
    """Return the newest saved modeling report or fail when none exist."""

    reports = list_recent_modeling_reports(limit=1)
    if not reports:
        raise InvalidDatasetNameError("No modeling reports found in the local reports directory.")
    return reports[0]


def _build_search_snippet(markdown: str, match_index: int, query_length: int) -> str:
    """Build a bounded single-line snippet around a search hit."""

    snippet_radius = MAX_REPORT_SEARCH_SNIPPET_LENGTH // 2
    start = max(0, match_index - snippet_radius)
    end = min(len(markdown), match_index + query_length + snippet_radius)
    snippet = markdown[start:end].replace("\r", " ").replace("\n", " ").strip()
    if start > 0:
        snippet = f"...{snippet}"
    if end < len(markdown):
        snippet = f"{snippet}..."
    return snippet
