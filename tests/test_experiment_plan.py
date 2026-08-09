from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.experiment_plan import build_experiment_plan_dataset


def write_experiment_plan_dataset(root: Path, name: str = "modeling_readiness.csv") -> Path:
    """Create a dataset that exercises the experiment-plan workflow."""

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


def test_build_experiment_plan_uses_suggested_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_experiment_plan_dataset(tmp_path)

    result = build_experiment_plan_dataset("modeling_readiness.csv")

    assert result.target_column == "revenue"
    assert result.target_source == "suggested"
    assert result.validation_strategy == "time_series_review"
    assert result.recommended_validation_strategy == "chronological"
    assert result.recommended_time_column == "date"
    assert result.recommended_group_column is None
    assert "record_id" not in result.feature_columns
    assert "date" in result.review_columns
    assert result.baseline_models[0].name == "seasonal_naive_baseline"
    assert "mae" in result.evaluation_metrics
    assert any("Datetime context" in risk for risk in result.risks)
    assert any("chronological validation" in step for step in result.next_steps)
    assert "seasonal_naive_baseline" in result.summary


def test_build_experiment_plan_respects_requested_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_experiment_plan_dataset(tmp_path)

    result = build_experiment_plan_dataset(
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
    assert result.baseline_models[0].name == "dummy_classifier_most_frequent"
    assert "macro_f1" in result.evaluation_metrics
    assert any("leakage" in step for step in result.next_steps)
