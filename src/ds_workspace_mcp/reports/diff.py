from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from difflib import unified_diff


@dataclass(frozen=True)
class MarkdownDiffSummary:
    """A bounded unified diff summary between two markdown fragments."""

    changed: bool
    added_line_count: int
    removed_line_count: int
    diff_preview: str


def compare_markdown_lines(
    primary_lines: Iterable[str],
    other_lines: Iterable[str],
    *,
    fromfile: str,
    tofile: str,
    max_preview_lines: int,
) -> MarkdownDiffSummary:
    """Return a bounded unified diff summary for two markdown line iterables."""

    diff_lines = list(
        unified_diff(
            list(primary_lines),
            list(other_lines),
            fromfile=fromfile,
            tofile=tofile,
            lineterm="",
        )
    )
    added_line_count = sum(
        1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
    )
    removed_line_count = sum(
        1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
    )
    preview_lines = diff_lines[:max_preview_lines]
    return MarkdownDiffSummary(
        changed=bool(diff_lines),
        added_line_count=added_line_count,
        removed_line_count=removed_line_count,
        diff_preview="\n".join(preview_lines),
    )
