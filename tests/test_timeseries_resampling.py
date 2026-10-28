"""Behavior and resource-limit tests for read-only time-series resampling."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from ds_workspace_mcp.timeseries_resampling import FillMethod, resample_time_series_dataset


def write_dataset(root: Path, frame: pd.DataFrame) -> Path:
    """Write a CSV fixture inside a controlled data directory."""

    path = root / "series.csv"
    frame.to_csv(path, index=False)
    return path


def test_resample_daily_gap_without_filling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    source = write_dataset(
        tmp_path,
        pd.DataFrame({"date": ["2024-01-01", "2024-01-02", "2024-01-04"], "value": [1, 2, 4]}),
    )

    result = resample_time_series_dataset("series.csv", "date", "value", "1D")

    assert result.source_rows == 3
    assert result.group_count == 1
    assert result.generated_intervals == 4
    assert result.missing_intervals == 1
    assert result.filled_intervals == 0
    assert result.preview_rows[2].timestamp == "2024-01-03T00:00:00+00:00"
    assert result.preview_rows[2].value is None
    assert result.preview_rows[2].observed_rows == 0
    assert result.preview_rows[2].filled is False
    assert result.missing_interval_examples[0].timestamp == result.preview_rows[2].timestamp
    assert {suggestion.method for suggestion in result.fill_suggestions} == {
        "none",
        "forward_fill",
        "linear_interpolation",
        "zero",
    }
    assert list(tmp_path.iterdir()) == [source]  # Resampling never writes to the data root.


def test_resample_duplicate_timestamps_and_downsample_aggregation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_dataset(
        tmp_path,
        pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-03"],
                "value": [2, 6, 4, 8],
            }
        ),
    )

    daily = resample_time_series_dataset("series.csv", "date", "value", "1D")
    two_day = resample_time_series_dataset("series.csv", "date", "value", "2D", aggregation="sum")

    assert daily.preview_rows[0].value == 4.0
    assert daily.preview_rows[0].observed_rows == 2
    assert two_day.generated_intervals == 2
    assert [row.value for row in two_day.preview_rows] == [12.0, 8.0]


def test_resample_forward_fill_preserves_observed_nulls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_dataset(
        tmp_path,
        pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-02", "2024-01-04"],
                "value": [1.0, None, 4.0],
            }
        ),
    )

    result = resample_time_series_dataset(
        "series.csv", "date", "value", "1D", fill_method="forward_fill"
    )

    assert result.source_missing_values == 1
    assert result.missing_intervals == 1
    assert result.filled_intervals == 1
    assert result.preview_rows[1].value is None
    assert result.preview_rows[1].observed_rows == 1
    assert result.preview_rows[1].filled is False
    assert result.preview_rows[2].value == 1.0
    assert result.preview_rows[2].filled is True
    assert "does not impute" in result.warnings[0]


@pytest.mark.parametrize(
    ("method", "expected", "future_warning"),
    [
        ("none", None, False),
        ("forward_fill", 0.0, False),
        ("backward_fill", 10.0, True),
        ("linear_interpolation", 5.0, True),
        ("zero", 0.0, False),
    ],
)
def test_resample_fill_policy_is_explicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method: FillMethod,
    expected: float | None,
    future_warning: bool,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_dataset(
        tmp_path,
        pd.DataFrame({"date": ["2024-01-01", "2024-01-03"], "value": [0.0, 10.0]}),
    )

    result = resample_time_series_dataset("series.csv", "date", "value", "1D", fill_method=method)

    assert result.preview_rows[1].value == expected
    assert result.filled_intervals == (0 if method == "none" else 1)
    assert any("look-ahead leakage" in warning for warning in result.warnings) == future_warning


def test_resample_grouped_data_tracks_gaps_per_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_dataset(
        tmp_path,
        pd.DataFrame(
            {
                "clinic": ["a", "a", "b", "b", "b"],
                "date": ["2024-01-01", "2024-01-03", "2024-01-01", "2024-01-02", "2024-01-03"],
                "value": [1, 3, 4, 5, 6],
            }
        ),
    )

    result = resample_time_series_dataset(
        "series.csv", "date", "value", "1D", group_column="clinic", rows=4
    )

    assert result.group_count == 2
    assert result.generated_intervals == 6
    assert result.missing_intervals == 1
    assert result.preview_truncated is True
    assert [row.group for row in result.preview_rows] == ["a", "a", "a", "b"]
    assert result.missing_interval_examples[0].group == "a"


def test_resample_monthly_and_timezone_normalization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_dataset(
        tmp_path,
        pd.DataFrame({"date": ["2024-01-01", "2024-03-01"], "value": [1, 3]}),
    )

    monthly = resample_time_series_dataset("series.csv", "date", "value", "1MS")
    assert monthly.missing_intervals == 1
    assert monthly.preview_rows[1].timestamp == "2024-02-01T00:00:00+00:00"

    write_dataset(
        tmp_path,
        pd.DataFrame(
            {
                "date": ["2024-03-31T00:00:00+00:00", "2024-04-01T01:00:00+01:00"],
                "value": [2, 4],
            }
        ),
    )
    utc = resample_time_series_dataset("series.csv", "date", "value", "1D")
    assert utc.generated_intervals == 2
    assert utc.preview_rows[1].timestamp == "2024-04-01T00:00:00+00:00"


@pytest.mark.parametrize("file_format", ["json", "xlsx", "parquet"])
def test_resample_supports_other_safe_dataset_formats(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, file_format: str
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    frame = pd.DataFrame({"date": ["2024-01-01", "2024-01-03"], "value": [10.0, 30.0]})
    file_name = f"series.{file_format}"
    if file_format == "json":
        frame.to_json(tmp_path / file_name, orient="records")
    elif file_format == "xlsx":
        frame.to_excel(tmp_path / file_name, sheet_name="Observations", index=False)
        file_name += "#Observations"
    else:
        # DuckDB writes Parquet without a pyarrow runtime requirement.
        with duckdb.connect(database=":memory:") as connection:
            connection.execute("CREATE TABLE observations AS SELECT * FROM frame")
            connection.execute(
                "COPY observations TO ? (FORMAT PARQUET)", [str(tmp_path / file_name)]
            )

    result = resample_time_series_dataset(file_name, "date", "value", "1D")

    assert result.generated_intervals == 3
    assert result.missing_intervals == 1
    assert result.preview_rows[1].observed_rows == 0


def test_resample_rejects_unbounded_grid_before_expansion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_MAX_RESAMPLE_INTERVALS", "4")
    write_dataset(
        tmp_path,
        pd.DataFrame({"date": ["2024-01-01", "2024-02-01"], "value": [1, 2]}),
    )

    with pytest.raises(ValueError, match="MCP_MAX_RESAMPLE_INTERVALS"):
        resample_time_series_dataset("series.csv", "date", "value", "1s")


def test_resample_rejects_too_many_groups(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_dataset(
        tmp_path,
        pd.DataFrame(
            {"group": [f"g{i}" for i in range(21)], "date": ["2024-01-01"] * 21, "value": [1] * 21}
        ),
    )

    with pytest.raises(ValueError, match="at most 20 groups"):
        resample_time_series_dataset("series.csv", "date", "value", "1D", group_column="group")


@pytest.mark.parametrize("frequency", ["0D", "1ns", "1W-MON", "1000D", "-1D", "1day"])
def test_resample_rejects_unsupported_frequency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frequency: str
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))

    with pytest.raises(ValueError, match="frequency must be"):
        resample_time_series_dataset("series.csv", "date", "value", frequency)


def test_resample_enforces_preview_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_MAX_PREVIEW_ROWS", "2")

    with pytest.raises(ValueError, match="MCP_MAX_PREVIEW_ROWS"):
        resample_time_series_dataset("series.csv", "date", "value", "1D", rows=3)


@pytest.mark.parametrize(
    ("dates", "values", "error"),
    [
        (["2024-01-01", "not-a-date"], [1, 2], "invalid timestamps"),
        (["2024-01-01", "2024-01-02"], [1, "oops"], "nonnumeric values"),
        (["2024-01-01", "2024-01-02"], [None, None], "no numeric observations"),
        (["2024-01-01", "2024-01-02"], [1.0, float("inf")], "non-finite values"),
    ],
)
def test_resample_rejects_invalid_source_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dates: list[str],
    values: list[object],
    error: str,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_dataset(tmp_path, pd.DataFrame({"date": dates, "value": values}))

    with pytest.raises(ValueError, match=error):
        resample_time_series_dataset("series.csv", "date", "value", "1D")


def test_resample_cannot_read_files_outside_data_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setenv("MCP_DATA_ROOT", str(data_root))
    write_dataset(
        tmp_path,
        pd.DataFrame({"date": ["2024-01-01"], "value": [1]}),
    )

    with pytest.raises(ValueError, match="path|file|escape|directory"):
        resample_time_series_dataset("../series.csv", "date", "value", "1D")
