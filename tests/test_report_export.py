from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.exceptions import InvalidDatasetNameError, PathTraversalError
from ds_workspace_mcp.report_export import (
    list_saved_modeling_reports,
    read_saved_modeling_report,
    resolve_report_output_path,
    save_modeling_report_dataset,
)


def write_report_export_dataset(root: Path, name: str = "report_export.csv") -> Path:
    """Create a dataset that exercises report export behavior."""

    path = root / name
    pd.DataFrame(
        {
            "feature": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            "target": [10, 12, 11, 13, 12, 14, 15, 16, 15, 17, 18, 18],
        }
    ).to_csv(path, index=False)
    return path


def test_resolve_report_output_path_rejects_traversal() -> None:
    with pytest.raises(PathTraversalError, match="inside the reports directory"):
        resolve_report_output_path(
            file_name="sample.csv",
            target_column="target",
            output_name="../escape.md",
        )


def test_resolve_report_output_path_rejects_non_markdown_name() -> None:
    with pytest.raises(InvalidDatasetNameError, match="must end with .md"):
        resolve_report_output_path(
            file_name="sample.csv",
            target_column="target",
            output_name="report.txt",
        )


def test_save_modeling_report_dataset_writes_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_report_export_dataset(tmp_path)

    result = save_modeling_report_dataset(
        "report_export.csv",
        target_column="target",
        output_name="custom-report.md",
    )

    saved_path = Path(result.output_path)
    assert saved_path.exists()
    assert saved_path.name == "custom-report.md"
    assert saved_path.parent.name == "reports"
    assert "## Summary" in saved_path.read_text(encoding="utf-8")


def test_list_saved_modeling_reports_returns_sorted_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "b-report.md").write_text("b", encoding="utf-8")
    (reports_dir / "a-report.md").write_text("aa", encoding="utf-8")

    reports = list_saved_modeling_reports()

    assert [report.output_name for report in reports] == ["a-report.md", "b-report.md"]
    assert reports[0].size_bytes == 2


def test_read_saved_modeling_report_returns_markdown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    report_path = reports_dir / "a-report.md"
    report_path.write_text("# Example\n\nBody", encoding="utf-8")

    report = read_saved_modeling_report("a-report.md")

    assert report.output_name == "a-report.md"
    assert report.output_path == str(report_path.resolve())
    assert "# Example" in report.markdown


def test_read_saved_modeling_report_rejects_traversal() -> None:
    with pytest.raises(PathTraversalError, match="inside the reports directory"):
        read_saved_modeling_report("../escape.md")
