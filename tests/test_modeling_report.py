from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.modeling_report import build_modeling_report_dataset


def write_modeling_report_dataset(root: Path, name: str = "reporting.csv") -> Path:
    """Create a dataset that exercises the modeling report workflow."""

    path = root / name
    pd.DataFrame(
        {
            "record_id": list(range(100, 112)),
            "date": pd.date_range("2024-01-01", periods=12, freq="D"),
            "revenue": [
                100.0,
                104.0,
                107.0,
                111.0,
                116.0,
                118.0,
                123.0,
                127.0,
                131.0,
                136.0,
                140.0,
                140.0,
            ],
            "segment": ["a", "b", "a", "c", "b", "a", "c", "b", "a", "c", "b", "a"],
            "mostly_missing": [
                None,
                None,
                None,
                None,
                "x",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ],
        }
    ).to_csv(path, index=False)
    return path


def test_build_modeling_report_returns_markdown_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_modeling_report_dataset(tmp_path)

    result = build_modeling_report_dataset("reporting.csv")

    assert result.target_column == "revenue"
    assert "revenue" in result.headline
    assert "# " in result.markdown
    assert "## Summary" in result.markdown
    assert "## Baseline Models" in result.markdown
    assert "## Evaluation Manifest" in result.markdown
    assert "Dataset fingerprint" in result.markdown
    assert "## Risks" in result.markdown
    assert "## Next Steps" in result.markdown
    assert "`revenue`" in result.markdown
    assert result.evaluation_manifest.dataset_name == "reporting.csv"
    assert result.evaluation_manifest.selected_target == "revenue"


def test_build_modeling_report_respects_requested_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_modeling_report_dataset(tmp_path)

    result = build_modeling_report_dataset(
        "reporting.csv",
        target_column="segment",
    )

    assert result.target_column == "segment"
    assert "multiclass_classification" in result.markdown
    assert "requested" in result.markdown
    assert result.evaluation_manifest.selected_target == "segment"
