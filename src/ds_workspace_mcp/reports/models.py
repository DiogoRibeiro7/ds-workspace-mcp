from __future__ import annotations

from pydantic import BaseModel


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
    created_at: str
    modified_at: str
    content_sha256: str | None = None


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


class CopiedModelingReport(BaseModel):
    """Metadata for a copied modeling report artifact."""

    source_output_name: str
    new_output_name: str
    source_output_path: str
    new_output_path: str


class ModelingReportMetadata(BaseModel):
    """Metadata summary for one saved modeling report artifact."""

    output_name: str
    output_path: str
    size_bytes: int
    created_at: str
    metadata_changed_at: str
    modified_at: str
    content_sha256: str


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


class ModelingReportSection(BaseModel):
    """One markdown section discovered inside a saved modeling report."""

    heading: str
    level: int


class ReadModelingReportSection(BaseModel):
    """One extracted markdown section from a saved modeling report."""

    output_name: str
    output_path: str
    heading: str
    level: int
    markdown: str


class SavedModelingReportSection(BaseModel):
    """Metadata for one extracted section saved as a markdown artifact."""

    source_output_name: str
    section_heading: str
    output_path: str


class ComparedModelingReportSection(BaseModel):
    """A bounded diff summary between matching sections in two saved reports."""

    output_name: str
    other_output_name: str
    section_heading: str
    changed: bool
    added_line_count: int
    removed_line_count: int
    diff_preview: str


class ModelingReportSectionMatch(BaseModel):
    """One saved report section that matches a heading query."""

    output_name: str
    output_path: str
    heading: str
    level: int
    snippet: str


class ModelingReportSectionSummary(BaseModel):
    """A compact summary of one recurring section heading across saved reports."""

    heading: str
    level: int
    report_count: int
    example_reports: list[str]
