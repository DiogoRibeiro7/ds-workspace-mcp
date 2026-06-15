from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.timeseries import validate_time_series_dataset


def write_timeseries_dataset(root: Path, name: str, df: pd.DataFrame) -> Path:
    """Write a time-series dataset fixture."""

    path = root / name
    df.to_csv(path, index=False)
    return path


def test_validate_time_series_dataset_regular_daily_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=12, freq="D"),
            "target": range(12),
        }
    )
    write_timeseries_dataset(tmp_path, "regular.csv", df)

    result = validate_time_series_dataset("regular.csv", time_column="date", target_column="target")

    assert result.inferred_frequency == "1D"
    assert result.missing_intervals == 0
    assert result.duplicate_timestamps == 0
    assert result.is_sorted is True
    assert result.missing_target_values == 0


def test_validate_time_series_dataset_irregular_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-02", "2024-01-04", "2024-01-05"],
            "target": [1, 2, 3, 4],
        }
    )
    write_timeseries_dataset(tmp_path, "irregular.csv", df)

    result = validate_time_series_dataset(
        "irregular.csv",
        time_column="date",
        target_column="target",
    )
    warning_types = {warning.warning_type for warning in result.warnings}

    assert result.missing_intervals == 1
    assert "missing_intervals" in warning_types


def test_validate_time_series_dataset_duplicate_timestamps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-03"],
            "target": [1, 2, 3, 4],
        }
    )
    write_timeseries_dataset(tmp_path, "duplicates.csv", df)

    result = validate_time_series_dataset("duplicates.csv", time_column="date")
    warning_types = {warning.warning_type for warning in result.warnings}

    assert result.duplicate_timestamps == 1
    assert "duplicate_timestamps" in warning_types


def test_validate_time_series_dataset_grouped_series(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "clinic": ["a", "a", "a", "b", "b", "b"],
            "date": [
                "2024-01-01",
                "2024-01-02",
                "2024-01-04",
                "2024-01-01",
                "2024-01-02",
                "2024-01-03",
            ],
            "target": [1, 2, 3, 4, 5, 6],
        }
    )
    write_timeseries_dataset(tmp_path, "grouped.csv", df)

    result = validate_time_series_dataset(
        "grouped.csv",
        time_column="date",
        target_column="target",
        group_column="clinic",
    )

    assert len(result.group_summaries) == 2
    group_a = next(item for item in result.group_summaries if item.group == "a")
    assert group_a.missing_intervals == 1


def test_validate_time_series_dataset_invalid_time_column(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame({"date": ["not-a-date", "still-not-a-date"], "target": [1, 2]})
    write_timeseries_dataset(tmp_path, "invalid.csv", df)

    with pytest.raises(ValueError, match="could not be parsed"):
        validate_time_series_dataset("invalid.csv", time_column="date")
