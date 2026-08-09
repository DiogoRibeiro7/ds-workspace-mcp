from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp import cli
from ds_workspace_mcp.forecasting import evaluate_forecast_baselines_dataset


def write_forecast_dataset(root: Path, name: str, df: pd.DataFrame) -> Path:
    """Write a forecast-baseline fixture dataset."""

    path = root / name
    df.to_csv(path, index=False)
    return path


def test_evaluate_forecast_baselines_regular_daily_series(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    values = [10 + (index % 7) + (index * 0.5) for index in range(35)]
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=35, freq="D"),
            "target": values,
        }
    )
    write_forecast_dataset(tmp_path, "daily.csv", df)

    result = evaluate_forecast_baselines_dataset(
        file_name="daily.csv",
        time_column="date",
        target_column="target",
        test_size=0.2,
    )

    assert result.frequency.frequency == "1D"
    assert result.forecast_horizon == 1
    assert result.seasonal_period == 7
    assert result.metric_notes.mase
    baseline_names = {baseline.baseline_name for baseline in result.baselines}
    assert baseline_names == {"drift", "last_value_naive", "seasonal_naive"}
    seasonal = next(item for item in result.baselines if item.baseline_name == "seasonal_naive")
    assert seasonal.seasonal_period == 7
    assert seasonal.evaluated_points == 7
    assert seasonal.training_start == "2024-01-01T00:00:00"
    assert seasonal.training_end < seasonal.test_start
    assert seasonal.metrics.mase is not None
    assert seasonal.metrics.smape >= 0
    assert result.evaluation_manifest.dataset_name == "daily.csv"
    assert result.evaluation_manifest.selected_target == "target"
    assert result.evaluation_manifest.validation_strategy == "chronological_rolling_origin"
    assert result.evaluation_manifest.time_column == "date"
    assert result.evaluation_manifest.train_test_boundaries.evaluated_points == 7
    assert "smape" in result.evaluation_manifest.metric_definitions


def test_evaluate_forecast_baselines_supports_grouped_series(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    dates = list(pd.date_range("2024-01-01", periods=21, freq="D"))
    df = pd.DataFrame(
        {
            "clinic": ["a"] * 21 + ["b"] * 21,
            "date": dates + dates,
            "target": [float(index) for index in range(21)]
            + [float(index + 5) for index in range(21)],
        }
    )
    write_forecast_dataset(tmp_path, "grouped.csv", df)

    result = evaluate_forecast_baselines_dataset(
        file_name="grouped.csv",
        time_column="date",
        target_column="target",
        group_column="clinic",
        seasonal_period=7,
        test_size=0.25,
    )

    assert result.group_column == "clinic"
    assert result.frequency.frequency == "1D"
    assert len(result.group_results) == 2
    assert {group.group for group in result.group_results} == {"a", "b"}
    assert result.evaluation_manifest.group_column == "clinic"
    assert result.evaluation_manifest.train_test_boundaries.evaluated_points == 12
    assert {baseline.baseline_name for baseline in result.baselines} == {
        "drift",
        "last_value_naive",
        "seasonal_naive",
    }
    assert all(group.baselines for group in result.group_results)


def test_evaluate_forecast_baselines_rejects_irregular_series(
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
                "2024-01-16",
                "2024-01-22",
                "2024-01-29",
                "2024-02-07",
                "2024-02-19",
            ],
            "target": list(range(10)),
        }
    )
    write_forecast_dataset(tmp_path, "irregular.csv", df)

    with pytest.raises(ValueError, match="regular inferred frequency"):
        evaluate_forecast_baselines_dataset(
            file_name="irregular.csv",
            time_column="date",
            target_column="target",
        )


def test_cli_evaluate_forecast_baselines_outputs_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=20, freq="D"),
            "target": [float(index) for index in range(20)],
        }
    )
    write_forecast_dataset(tmp_path, "cli.csv", df)

    exit_code = cli.main(
        [
            "evaluate-forecast-baselines",
            "cli.csv",
            "--time-column",
            "date",
            "--target-column",
            "target",
            "--seasonal-period",
            "7",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["file_name"] == "cli.csv"
    assert payload["target_column"] == "target"
    assert payload["evaluation_manifest"]["dataset_name"] == "cli.csv"
    assert any(item["baseline_name"] == "last_value_naive" for item in payload["baselines"])
