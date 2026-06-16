from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.targeting import suggest_target_columns_dataset


def write_targeting_dataset(root: Path, name: str = "targets.csv") -> Path:
    """Create a dataset that exercises target suggestions."""

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
                145.0,
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


def test_suggest_target_columns_ranks_plausible_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_targeting_dataset(tmp_path)

    result = suggest_target_columns_dataset("targets.csv")

    top_columns = [candidate.column for candidate in result.candidates]
    assert "revenue" in top_columns
    assert "churned" in top_columns
    assert result.candidates[0].suggested_task_type in {
        "regression",
        "binary_classification",
        "multiclass_classification",
    }
    assert "Top target candidate is" in result.summary


def test_suggest_target_columns_penalizes_identifier_and_datetime_columns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_targeting_dataset(tmp_path)

    result = suggest_target_columns_dataset("targets.csv")
    candidate_by_name = {candidate.column: candidate for candidate in result.candidates}

    assert candidate_by_name["record_id"].suggested_task_type == "regression"
    assert any("identifier" in reason for reason in candidate_by_name["record_id"].reasons)
    assert candidate_by_name["date"].suggested_task_type == "review_manually"
    assert any("time column" in reason for reason in candidate_by_name["date"].reasons)
