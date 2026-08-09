from __future__ import annotations

from ds_workspace_mcp import report_export, report_storage
from ds_workspace_mcp.reports import StoredModelingReport
from ds_workspace_mcp.reports.diff import compare_markdown_lines
from ds_workspace_mcp.reports.models import StoredModelingReport as ReportModel
from ds_workspace_mcp.reports.parsing import extract_markdown_sections, parse_markdown_heading
from ds_workspace_mcp.reports.storage import ReportStorage


def test_report_compatibility_imports_point_to_split_modules() -> None:
    assert report_export.StoredModelingReport is ReportModel
    assert report_export.StoredModelingReport is StoredModelingReport
    assert report_storage.ReportStorage is ReportStorage


def test_markdown_section_parser_handles_nested_repeated_empty_and_fenced_headings() -> None:
    markdown = [
        "# Report",
        "",
        "```python",
        "# not a heading",
        "```",
        "## Repeated",
        "Body A",
        "### Nested",
        "Nested body",
        "## Repeated",
        "Body B",
        "## Empty",
        "## Closed ##",
        "Closed body",
    ]

    sections = extract_markdown_sections(markdown)

    assert [(section.heading, section.level) for section in sections] == [
        ("Report", 1),
        ("Repeated", 2),
        ("Nested", 3),
        ("Repeated", 2),
        ("Empty", 2),
        ("Closed", 2),
    ]
    assert "# not a heading" in "\n".join(sections[0].lines)
    assert "### Nested" in "\n".join(sections[1].lines)
    assert "## Repeated\nBody B" not in "\n".join(sections[1].lines)
    assert sections[4].lines == ["## Empty"]


def test_markdown_heading_parser_handles_atx_headings() -> None:
    assert parse_markdown_heading("### Closed heading ###") == (3, "Closed heading")
    assert parse_markdown_heading("not # a heading") is None
    assert parse_markdown_heading("####### Too deep") is None


def test_diff_summary_is_pure_and_bounded() -> None:
    summary = compare_markdown_lines(
        ["# Report", "Line A"],
        ["# Report", "Line B", "Line C"],
        fromfile="before.md",
        tofile="after.md",
        max_preview_lines=4,
    )

    assert summary.changed is True
    assert summary.added_line_count == 2
    assert summary.removed_line_count == 1
    assert len(summary.diff_preview.splitlines()) == 4
