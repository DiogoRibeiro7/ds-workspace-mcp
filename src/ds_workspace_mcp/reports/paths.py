from __future__ import annotations

from pathlib import Path

from ds_workspace_mcp.config import get_settings

from .storage import ReportStorage


def resolve_report_output_path(
    file_name: str,
    target_column: str,
    output_name: str | None = None,
) -> Path:
    """Resolve a safe markdown output path inside the reports directory."""

    candidate_name = output_name or default_output_name(file_name, target_column)
    return get_report_storage().resolve_target(candidate_name)


def resolve_existing_report_path(output_name: str) -> Path:
    """Resolve one existing markdown report inside the reports directory."""

    return get_report_storage().resolve_existing(output_name)


def resolve_report_target_path(output_name: str) -> Path:
    """Resolve a target markdown report path inside the reports directory."""

    return get_report_storage().resolve_target(output_name)


def default_output_name(file_name: str, target_column: str) -> str:
    """Build a stable default markdown file name for a report artifact."""

    dataset_stem = Path(file_name).stem
    safe_dataset = slugify(dataset_stem)
    safe_target = slugify(target_column)
    return f"{safe_dataset}--{safe_target}--modeling-report.md"


def default_section_output_name(output_name: str, section_heading: str) -> str:
    """Build a stable default markdown file name for an extracted section artifact."""

    base_name = Path(output_name).stem
    safe_base_name = slugify(base_name)
    safe_heading = slugify(section_heading)
    return f"{safe_base_name}--{safe_heading}--section.md"


def slugify(value: str) -> str:
    """Convert free text into a conservative file-name slug."""

    cleaned = "".join(character.lower() if character.isalnum() else "-" for character in value)
    collapsed = "-".join(part for part in cleaned.split("-") if part)
    return collapsed or "report"


def get_reports_root() -> Path:
    """Return the configured reports root."""

    return get_settings().mcp_reports_root


def get_report_storage() -> ReportStorage:
    """Return storage configured for the current reports root."""

    return ReportStorage(get_reports_root())
