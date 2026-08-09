from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.diagnostics import (
    detect_possible_target_leakage_dataset,
    summarize_correlations_dataset,
)


def write_diagnostics_dataset(root: Path, name: str = "diagnostics.csv") -> Path:
    """Create a dataset that exercises correlation and leakage diagnostics."""

    path = root / name
    df = pd.DataFrame(
        {
            "target": [0, 1, 2, 3, 4, 5],
            "target_score": [0, 1, 2, 3, 4, 5],
            "feature_linear": [0, 2, 4, 6, 8, 10],
            "feature_inverse": [10, 8, 6, 4, 2, 0],
            "record_id": [101, 102, 103, 104, 105, 106],
            "prediction_time": [
                "2024-01-01",
                "2024-01-02",
                "2024-01-03",
                "2024-01-04",
                "2024-01-05",
                "2024-01-06",
            ],
            "category": ["a", "a", "b", "b", "c", "c"],
        }
    )
    df.to_csv(path, index=False)
    return path


def test_summarize_correlations_ranks_numeric_pairs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_diagnostics_dataset(tmp_path)

    summary = summarize_correlations_dataset("diagnostics.csv")

    assert summary.method == "pearson"
    assert "target" in summary.numeric_columns
    assert summary.top_correlations[0].absolute_correlation == 1.0
    assert {
        summary.top_correlations[0].left_column,
        summary.top_correlations[0].right_column,
    } == {"target", "target_score"}


def test_summarize_correlations_rejects_invalid_method(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_diagnostics_dataset(tmp_path)

    with pytest.raises(ValueError, match="method must be one of"):
        summarize_correlations_dataset("diagnostics.csv", method="cosine")


def test_detect_possible_target_leakage_rejects_missing_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_diagnostics_dataset(tmp_path)

    with pytest.raises(ValueError, match="Unknown target column"):
        detect_possible_target_leakage_dataset("diagnostics.csv", target_column="missing")


def test_detect_possible_target_leakage_flags_name_overlap_and_identifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_diagnostics_dataset(tmp_path)

    summary = detect_possible_target_leakage_dataset("diagnostics.csv", target_column="target")
    warning_pairs = {(warning.column, warning.warning_type) for warning in summary.warnings}

    assert ("target_score", "suspicious_name_overlap") in warning_pairs
    assert ("record_id", "likely_identifier") in warning_pairs


def test_detect_possible_target_leakage_flags_evidence_types(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_diagnostics_dataset(tmp_path)

    summary = detect_possible_target_leakage_dataset("diagnostics.csv", target_column="target")
    warning_pairs = {(warning.column, warning.warning_type) for warning in summary.warnings}
    warning_by_pair = {
        (warning.column, warning.warning_type): warning for warning in summary.warnings
    }

    assert ("feature_linear", "very_high_correlation") in warning_pairs
    assert ("target_score", "exact_target_duplicate") in warning_pairs
    assert ("prediction_time", "temporal_review") in warning_pairs
    assert warning_by_pair[("target_score", "exact_target_duplicate")].severity == "high"
    assert warning_by_pair[("target_score", "exact_target_duplicate")].confidence == 1.0
    assert warning_by_pair[("feature_linear", "very_high_correlation")].severity == "medium"
