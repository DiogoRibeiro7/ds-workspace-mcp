from __future__ import annotations

import os
from pathlib import Path

import pytest

from ds_workspace_mcp.exceptions import InvalidDatasetNameError
from ds_workspace_mcp.server import (
    latest_modeling_report_resource,
    latest_modeling_report_section_resource,
    latest_modeling_report_sections_resource,
    list_datasets,
    list_modeling_reports_resource,
    modeling_report_section_resource,
    modeling_report_sections_resource,
    read_modeling_report_resource,
)


def test_list_datasets_resource_returns_empty_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))

    payload = list_datasets()

    assert payload == "No CSV datasets found in the configured data directory."


def test_list_modeling_reports_resource_returns_names(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "alpha.md").write_text("# Alpha", encoding="utf-8")
    (reports_dir / "beta.md").write_text("# Beta", encoding="utf-8")

    payload = list_modeling_reports_resource()

    assert payload.splitlines() == ["alpha.md", "beta.md"]


def test_latest_modeling_report_resource_returns_markdown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("# Older\n\nBody", encoding="utf-8")
    newer.write_text("# Newer\n\nLatest body", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    payload = latest_modeling_report_resource()

    assert payload == "# Newer\n\nLatest body"


def test_read_modeling_report_resource_returns_markdown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    report_path = reports_dir / "sample.md"
    report_path.write_text("# Sample\n\nBody", encoding="utf-8")

    payload = read_modeling_report_resource("sample.md")

    assert payload == "# Sample\n\nBody"


def test_read_modeling_report_resource_rejects_unknown_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(InvalidDatasetNameError, match="Modeling report not found"):
        read_modeling_report_resource("missing.md")


def test_latest_modeling_report_sections_resource_returns_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("# Older\n\n## Summary\nOld", encoding="utf-8")
    newer.write_text("# Newer\n\n## Summary\nNew\n\n## Risks\n- Risk", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    payload = latest_modeling_report_sections_resource()

    assert [(section.heading, section.level) for section in payload] == [
        ("Newer", 1),
        ("Summary", 2),
        ("Risks", 2),
    ]


def test_modeling_report_sections_resource_returns_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    report_path = reports_dir / "sample.md"
    report_path.write_text("# Sample\n\n## Summary\nBody\n\n## Risks\n- Risk", encoding="utf-8")

    payload = modeling_report_sections_resource("sample.md")

    assert [(section.heading, section.level) for section in payload] == [
        ("Sample", 1),
        ("Summary", 2),
        ("Risks", 2),
    ]


def test_latest_modeling_report_section_resource_returns_markdown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("# Older\n\n## Summary\nOld", encoding="utf-8")
    newer.write_text("# Newer\n\n## Summary\nNew\n\n## Risks\n- Risk", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    payload = latest_modeling_report_section_resource("summary")

    assert payload == "## Summary\nNew\n"


def test_modeling_report_section_resource_returns_markdown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    report_path = reports_dir / "sample.md"
    report_path.write_text("# Sample\n\n## Summary\nBody\n\n## Risks\n- Risk", encoding="utf-8")

    payload = modeling_report_section_resource("sample.md", "risks")

    assert payload == "## Risks\n- Risk"
