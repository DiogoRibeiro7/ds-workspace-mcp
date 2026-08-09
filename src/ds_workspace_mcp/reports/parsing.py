from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .constants import (
    MAX_REPORT_SEARCH_SNIPPET_LENGTH,
    MAX_REPORT_SECTION_SNIPPET_LINES,
)


@dataclass(frozen=True)
class ParsedMarkdownSection:
    """Internal markdown section representation with captured lines."""

    heading: str
    level: int
    lines: list[str]


@dataclass(frozen=True)
class _HeadingPosition:
    line_index: int
    heading: str
    level: int


@dataclass(frozen=True)
class _FenceMarker:
    character: str
    length: int


_ATX_HEADING_PATTERN = re.compile(r" {0,3}(#{1,6})(?:[ \t]+|$)(.*)$")
_FENCE_PATTERN = re.compile(r" {0,3}(`{3,}|~{3,})")


def extract_markdown_sections(lines: Iterable[str]) -> list[ParsedMarkdownSection]:
    """Parse markdown ATX heading sections while ignoring fenced code blocks."""

    materialized_lines = list(lines)
    headings = _find_heading_positions(materialized_lines)
    sections: list[ParsedMarkdownSection] = []

    for index, heading in enumerate(headings):
        end_index = len(materialized_lines)
        for next_heading in headings[index + 1 :]:
            if next_heading.level <= heading.level:
                end_index = next_heading.line_index
                break
        sections.append(
            ParsedMarkdownSection(
                heading=heading.heading,
                level=heading.level,
                lines=materialized_lines[heading.line_index : end_index],
            )
        )

    return sections


def parse_markdown_heading(line: str) -> tuple[int, str] | None:
    """Return heading level and title for one ATX heading line."""

    match = _ATX_HEADING_PATTERN.fullmatch(line.rstrip())
    if match is None:
        return None

    title = _strip_closing_hashes(match.group(2).strip())
    if not title:
        return None
    return len(match.group(1)), title


def extract_headline(lines: Iterable[str]) -> str:
    """Extract a human-readable report headline from markdown lines."""

    for section in extract_markdown_sections(lines):
        if section.level == 1:
            return section.heading
    return "Untitled modeling report"


def build_search_snippet(markdown: str, match_index: int, query_length: int) -> str:
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


def build_section_snippet(lines: Iterable[str]) -> str:
    """Build a bounded markdown snippet for one parsed section."""

    return "\n".join(list(lines)[:MAX_REPORT_SECTION_SNIPPET_LINES])


def _find_heading_positions(lines: list[str]) -> list[_HeadingPosition]:
    headings: list[_HeadingPosition] = []
    active_fence: _FenceMarker | None = None

    for index, line in enumerate(lines):
        fence_marker = _parse_fence_marker(line)
        if active_fence is not None:
            if (
                fence_marker is not None
                and fence_marker.character == active_fence.character
                and fence_marker.length >= active_fence.length
            ):
                active_fence = None
            continue

        if fence_marker is not None:
            active_fence = fence_marker
            continue

        heading = parse_markdown_heading(line)
        if heading is None:
            continue
        level, title = heading
        headings.append(_HeadingPosition(line_index=index, heading=title, level=level))

    return headings


def _parse_fence_marker(line: str) -> _FenceMarker | None:
    match = _FENCE_PATTERN.match(line)
    if match is None:
        return None

    marker = match.group(1)
    return _FenceMarker(character=marker[0], length=len(marker))


def _strip_closing_hashes(title: str) -> str:
    if not title:
        return title
    return re.sub(r"[ \t]+#+[ \t]*$", "", title).strip()
