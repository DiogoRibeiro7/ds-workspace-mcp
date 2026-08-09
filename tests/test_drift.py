from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp import cli
from ds_workspace_mcp.drift import compare_datasets_dataset


def write_drift_pair(root: Path) -> None:
    """Create two dataset versions with structural and statistical changes."""

    left = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5, 6],
            "value": [10, 11, 12, 13, 14, 15],
            "category": ["a", "a", "b", "b", "c", "c"],
            "event_date": pd.date_range("2024-01-01", periods=6, freq="D"),
            "removed": ["legacy"] * 6,
            "nullable": [1, 2, 3, 4, 5, 6],
        }
    )
    right = pd.DataFrame(
        {
            "id": ["1", "2", "3", "4", "5", "6", "7"],
            "value": [30, 31, 32, 33, 34, 35, 36],
            "category": ["a", "b", "b", "b", "b", "b", "b"],
            "event_date": pd.date_range("2024-02-01", periods=7, freq="D"),
            "nullable": [1, None, None, 4, 5, 6, 7],
            "added": ["new"] * 7,
        }
    )
    left.to_csv(root / "left.csv", index=False)
    right.to_csv(root / "right.csv", index=False)


def test_compare_datasets_reports_schema_and_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_drift_pair(tmp_path)

    comparison = compare_datasets_dataset("left.csv", "right.csv")

    assert comparison.left_file_name == "left.csv"
    assert comparison.right_file_name == "right.csv"
    assert comparison.schema_diff.added_columns == ["added"]
    assert comparison.schema_diff.removed_columns == ["removed"]
    assert comparison.schema_diff.row_count.change == 1
    assert comparison.schema_diff.row_count.exact is True
    assert [change.column for change in comparison.schema_diff.dtype_changes] == ["nullable"]
    assert comparison.schema_diff.null_rate_changes[0].column == "nullable"
    assert comparison.schema_diff.cardinality_changes[0].column == "category"
    numeric_drift = next(item for item in comparison.drift.numeric if item.column == "value")
    assert numeric_drift.column == "value"
    assert numeric_drift.standardized_mean_difference is not None
    assert numeric_drift.effect_size == "large"
    categorical_drift = comparison.drift.categorical[0]
    assert categorical_drift.column == "category"
    assert categorical_drift.total_variation_distance > 0
    assert categorical_drift.jensen_shannon_divergence > 0
    timestamp_drift = comparison.drift.timestamp_ranges[0]
    assert timestamp_drift.column == "event_date"
    assert timestamp_drift.min_shift_seconds is not None
    assert timestamp_drift.min_shift_seconds > 0


def test_compare_datasets_reports_bounded_sampling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_MAX_SQL_ROWS", "3")
    pd.DataFrame({"value": [1, 2, 3, 4]}).to_csv(tmp_path / "left.csv", index=False)
    pd.DataFrame({"value": [1, 2, 3, 4, 5]}).to_csv(tmp_path / "right.csv", index=False)

    comparison = compare_datasets_dataset("left.csv", "right.csv")

    assert comparison.sampling.strategy == "head"
    assert comparison.sampling.max_rows_per_dataset == 3
    assert comparison.sampling.left_rows_analyzed == 3
    assert comparison.sampling.right_rows_analyzed == 3
    assert comparison.sampling.left_truncated is True
    assert comparison.sampling.right_truncated is True
    assert comparison.schema_diff.row_count.exact is False


def test_cli_compare_datasets_outputs_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_drift_pair(tmp_path)

    exit_code = cli.main(["compare-datasets", "left.csv", "right.csv"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["left_file_name"] == "left.csv"
    assert payload["right_file_name"] == "right.csv"
    assert payload["schema_diff"]["added_columns"] == ["added"]
    assert any(item["column"] == "value" for item in payload["drift"]["numeric"])
