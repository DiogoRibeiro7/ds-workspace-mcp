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
    assert result.frequency.frequency == "1D"
    assert result.frequency.frequency_kind == "regular"
    assert result.frequency.confidence == 1.0
    assert result.frequency.is_regular is True
    assert result.frequency.is_irregular is False
    assert result.missing_intervals == 0
    assert result.duplicate_timestamps == 0
    assert result.is_sorted is True
    assert result.missing_target_values == 0


def test_validate_time_series_dataset_daily_data_with_one_missing_date(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    dates = list(pd.date_range("2024-01-01", periods=12, freq="D"))
    dates.pop(5)
    df = pd.DataFrame(
        {
            "date": dates,
            "target": list(range(11)),
        }
    )
    write_timeseries_dataset(tmp_path, "missing_daily.csv", df)

    result = validate_time_series_dataset(
        "missing_daily.csv",
        time_column="date",
        target_column="target",
    )
    warning_types = {warning.warning_type for warning in result.warnings}

    assert result.inferred_frequency == "1D"
    assert result.frequency.frequency_kind == "approximately_regular"
    assert result.frequency.support_ratio >= 0.8
    assert result.missing_intervals == 1
    assert "missing_intervals" in warning_types


def test_validate_time_series_dataset_weekly_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=12, freq="W-MON"),
            "target": range(12),
        }
    )
    write_timeseries_dataset(tmp_path, "weekly.csv", df)

    result = validate_time_series_dataset("weekly.csv", time_column="date")

    assert result.inferred_frequency == "7D"
    assert result.frequency.frequency_kind == "regular"
    assert result.missing_intervals == 0


def test_validate_time_series_dataset_monthly_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=12, freq="MS"),
            "target": range(12),
        }
    )
    write_timeseries_dataset(tmp_path, "monthly.csv", df)

    result = validate_time_series_dataset("monthly.csv", time_column="date")

    assert result.inferred_frequency == "MS"
    assert result.frequency.frequency_kind == "regular"
    assert result.missing_intervals == 0


def test_validate_time_series_dataset_unsorted_timestamps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=12, freq="D"),
            "target": range(12),
        }
    ).sample(frac=1.0, random_state=9)
    write_timeseries_dataset(tmp_path, "unsorted.csv", df)

    result = validate_time_series_dataset("unsorted.csv", time_column="date")
    warning_types = {warning.warning_type for warning in result.warnings}

    assert result.is_sorted is False
    assert result.frequency.frequency_kind == "regular"
    assert "unsorted_timestamps" in warning_types


def test_validate_time_series_dataset_irregular_1234_day_gaps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "date": [
                "2024-01-01",
                "2024-01-02",
                "2024-01-04",
                "2024-01-07",
                "2024-01-11",
            ],
            "target": [1, 2, 3, 4, 5],
        }
    )
    write_timeseries_dataset(tmp_path, "irregular_1234.csv", df)

    result = validate_time_series_dataset("irregular_1234.csv", time_column="date")
    warning_types = {warning.warning_type for warning in result.warnings}

    assert result.inferred_frequency is None
    assert result.frequency.frequency_kind == "irregular"
    assert result.frequency.is_irregular is True
    assert result.missing_intervals == 0
    assert "irregular_frequency" in warning_types


def test_validate_time_series_dataset_mostly_daily_with_occasional_missing_intervals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    dates = list(pd.date_range("2024-01-01", periods=20, freq="D"))
    del dates[12]
    del dates[4]
    df = pd.DataFrame({"date": dates, "target": range(len(dates))})
    write_timeseries_dataset(tmp_path, "mostly_daily.csv", df)

    result = validate_time_series_dataset("mostly_daily.csv", time_column="date")

    assert result.inferred_frequency == "1D"
    assert result.frequency.frequency_kind == "approximately_regular"
    assert result.missing_intervals == 2


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
    assert result.frequency.frequency_kind == "regular"
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
    assert result.frequency.frequency_kind == "heterogeneous"
    assert result.inferred_frequency is None
    group_a = next(item for item in result.group_summaries if item.group == "a")
    assert group_a.missing_intervals == 0
    assert group_a.frequency.frequency_kind == "irregular"


def test_validate_time_series_dataset_grouped_consistent_frequency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "clinic": ["a"] * 12 + ["b"] * 12,
            "date": list(pd.date_range("2024-01-01", periods=12, freq="D"))
            + list(pd.date_range("2024-01-01", periods=12, freq="D")),
            "target": list(range(24)),
        }
    )
    write_timeseries_dataset(tmp_path, "grouped_consistent.csv", df)

    result = validate_time_series_dataset(
        "grouped_consistent.csv",
        time_column="date",
        group_column="clinic",
    )

    assert result.inferred_frequency == "1D"
    assert result.frequency.frequency_kind == "regular"
    assert {item.frequency.frequency for item in result.group_summaries} == {"1D"}


def test_validate_time_series_dataset_grouped_different_frequencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "clinic": ["daily"] * 12 + ["weekly"] * 12,
            "date": list(pd.date_range("2024-01-01", periods=12, freq="D"))
            + list(pd.date_range("2024-01-01", periods=12, freq="W-MON")),
            "target": list(range(24)),
        }
    )
    write_timeseries_dataset(tmp_path, "grouped_different.csv", df)

    result = validate_time_series_dataset(
        "grouped_different.csv",
        time_column="date",
        group_column="clinic",
    )
    warning_types = {warning.warning_type for warning in result.warnings}

    assert result.inferred_frequency is None
    assert result.frequency.frequency_kind == "heterogeneous"
    assert {item.frequency.frequency for item in result.group_summaries} == {"1D", "7D"}
    assert "heterogeneous_frequencies" in warning_types


def test_validate_time_series_dataset_invalid_time_column(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame({"date": ["not-a-date", "still-not-a-date"], "target": [1, 2]})
    write_timeseries_dataset(tmp_path, "invalid.csv", df)

    with pytest.raises(ValueError, match="could not be parsed"):
        validate_time_series_dataset("invalid.csv", time_column="date")
