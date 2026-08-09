from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.modeling_readiness import assess_modeling_readiness_dataset


def write_modeling_readiness_dataset(root: Path, name: str = "modeling_readiness.csv") -> Path:
    """Create a dataset that exercises the modeling-readiness orchestration."""

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
            "churned": [
                "yes",
                "no",
                "no",
                "yes",
                "no",
                "no",
                "yes",
                "no",
                "no",
                "yes",
                "no",
                "no",
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


def test_assess_modeling_readiness_uses_top_suggested_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_modeling_readiness_dataset(tmp_path)

    result = assess_modeling_readiness_dataset("modeling_readiness.csv")

    assert result.target_column == "revenue"
    assert result.target_source == "suggested"
    assert result.suggested_task_type == "regression"
    assert result.validation_strategy == "time_series_review"
    assert result.recommended_validation_strategy == "chronological"
    assert result.recommended_time_column == "date"
    assert result.recommended_group_column is None
    assert "validate_time_series_dataset" in result.recommended_next_tools
    assert "evaluate_forecast_baselines" in result.recommended_next_tools
    assert "evaluate_baseline_model" not in result.recommended_next_tools
    assert "record_id" in result.feature_selection.exclude_columns
    assert result.target_candidate is not None
    assert result.target_candidate.column == "revenue"
    assert "top suggested target" in result.summary


def test_assess_modeling_readiness_respects_requested_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_modeling_readiness_dataset(tmp_path)

    result = assess_modeling_readiness_dataset(
        "modeling_readiness.csv",
        target_column="churned",
    )

    assert result.target_column == "churned"
    assert result.target_source == "requested"
    assert result.suggested_task_type == "binary_classification"
    assert result.validation_strategy == "standard_train_test_split"
    assert result.recommended_validation_strategy == "stratified"
    assert result.recommended_time_column is None
    assert result.recommended_group_column is None
    assert "validate_time_series_dataset" not in result.recommended_next_tools
    assert "detect_possible_target_leakage" in result.recommended_next_tools
    assert "date" in result.feature_selection.review_columns
    assert "requested target" in result.summary


def test_assess_modeling_readiness_rejects_unknown_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_modeling_readiness_dataset(tmp_path)

    with pytest.raises(ValueError, match="Unknown target column"):
        assess_modeling_readiness_dataset(
            "modeling_readiness.csv",
            target_column="missing",
        )
