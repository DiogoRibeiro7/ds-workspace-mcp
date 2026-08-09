from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.feature_selection import suggest_feature_columns_dataset


def write_feature_selection_dataset(root: Path, name: str = "feature_selection.csv") -> Path:
    """Create a dataset that exercises feature-selection decisions."""

    path = root / name
    pd.DataFrame(
        {
            "target": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
            "good_numeric": [12, 15, 14, 18, 11, 19, 13, 17, 10, 16, 12, 18],
            "good_category": ["a", "b", "a", "c", "b", "c", "a", "b", "a", "c", "b", "a"],
            "legit_predictor": [0.1, 0.9, 0.2, 0.8, 0.1, 0.9, 0.2, 0.8, 0.1, 0.9, 0.2, 0.8],
            "event_date": pd.date_range("2024-01-01", periods=12, freq="D"),
            "record_id": list(range(100, 112)),
            "target_copy": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
            "target_score": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
            "target_hint": ["low", "high", "low", "high", "low", "high"] * 2,
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
            "half_missing": [1, None, 3, None, 5, None, 7, None, 9, None, 11, None],
            "constant_flag": ["same"] * 12,
        }
    ).to_csv(path, index=False)
    return path


def test_suggest_feature_columns_rejects_unknown_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_feature_selection_dataset(tmp_path)

    with pytest.raises(ValueError, match="Unknown target column"):
        suggest_feature_columns_dataset("feature_selection.csv", target_column="missing")


def test_suggest_feature_columns_separates_include_review_and_exclude(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_feature_selection_dataset(tmp_path)

    result = suggest_feature_columns_dataset("feature_selection.csv", target_column="target")
    suggestion_by_name = {item.column: item for item in result.suggestions}

    assert "good_numeric" in result.include_columns
    assert "good_category" in result.include_columns

    assert "event_date" in result.review_columns
    assert "legit_predictor" in result.review_columns
    assert "target_hint" in result.review_columns
    assert suggestion_by_name["event_date"].decision == "review"
    assert any(
        "feature engineering" in reason for reason in suggestion_by_name["event_date"].reasons
    )

    assert "record_id" in result.exclude_columns
    assert "target_copy" in result.exclude_columns
    assert "target_score" in result.exclude_columns
    assert "mostly_missing" in result.exclude_columns
    assert "constant_flag" in result.exclude_columns
    assert any("identifier" in reason for reason in suggestion_by_name["record_id"].reasons)
    assert any(
        "exact_target_duplicate" in reason for reason in suggestion_by_name["target_copy"].reasons
    )
    assert any(
        "exact_target_duplicate" in reason for reason in suggestion_by_name["target_score"].reasons
    )
    assert any(
        "very_high_correlation" in reason
        for reason in suggestion_by_name["legit_predictor"].reasons
    )
    assert any(
        "suspicious_name_overlap" in reason for reason in suggestion_by_name["target_hint"].reasons
    )

    assert "half_missing" in result.review_columns
    assert suggestion_by_name["half_missing"].decision == "review"
    assert any("imputation" in reason for reason in suggestion_by_name["half_missing"].reasons)

    assert "include 2 columns" in result.summary
