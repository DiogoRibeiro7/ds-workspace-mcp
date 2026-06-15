from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.core import (
    detect_csv_dataset_issues,
    list_csv_files,
    preview_csv_dataset,
    profile_csv_dataset,
    resolve_dataset_path,
)


def write_dataset(root: Path, name: str = "sample.csv") -> Path:
    """Create a small CSV dataset for tests."""

    path = root / name
    df = pd.DataFrame(
        {
            "id": ["a", "b", "c", "d"],
            "age": [33, 41, None, 52],
            "visits": [5, 8, 7, 10],
            "mostly_missing": [None, None, None, "known"],
        }
    )
    df.to_csv(path, index=False)
    return path


def test_list_csv_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_dataset(tmp_path, "b.csv")
    write_dataset(tmp_path, "a.csv")
    (tmp_path / "notes.txt").write_text("ignore me")

    assert list_csv_files() == ["a.csv", "b.csv"]


def test_resolve_dataset_path_rejects_path_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))

    with pytest.raises(ValueError, match="outside"):
        resolve_dataset_path("../secret.csv")


def test_resolve_dataset_path_rejects_non_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    path = tmp_path / "sample.txt"
    path.write_text("not,csv")

    with pytest.raises(ValueError, match="Only CSV"):
        resolve_dataset_path("sample.txt")


def test_preview_csv_dataset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_dataset(tmp_path)

    preview = preview_csv_dataset("sample.csv", rows=2)

    assert preview.file_name == "sample.csv"
    assert len(preview.rows) == 2
    assert preview.rows[0]["id"] == "a"


def test_preview_csv_dataset_rejects_invalid_row_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_dataset(tmp_path)

    with pytest.raises(ValueError, match="between 1 and 50"):
        preview_csv_dataset("sample.csv", rows=100)


def test_preview_csv_dataset_respects_configured_row_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_MAX_PREVIEW_ROWS", "3")
    write_dataset(tmp_path)

    with pytest.raises(ValueError, match="between 1 and 3"):
        preview_csv_dataset("sample.csv", rows=4)


def test_profile_csv_dataset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_dataset(tmp_path)

    profile = profile_csv_dataset("sample.csv")

    assert profile.row_count == 4
    assert profile.column_count == 4
    assert profile.missing_values["age"] == 1
    assert profile.missing_percentage["age"] == 25.0


def test_detect_csv_dataset_issues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_dataset(tmp_path)

    issues = detect_csv_dataset_issues("sample.csv")
    issue_types = {issue.issue_type for issue in issues}

    assert "high_missingness" in issue_types
    assert "possible_identifier" in issue_types
