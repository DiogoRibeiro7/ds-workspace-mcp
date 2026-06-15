from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.core import profile_csv_dataset


def write_profile_dataset(root: Path, name: str = "profile.csv") -> Path:
    """Create a dataset that exercises richer profiling paths."""

    path = root / name
    df = pd.DataFrame(
        {
            "numeric_value": [1.0, 2.0, 3.0, 4.0],
            "category": ["north", "north", "south", None],
            "is_active": [True, False, True, None],
            "event_date": ["2024-01-01", "2024-01-02", None, "2024-01-04"],
            "mixed_missing": [1.0, None, None, 4.0],
        }
    )
    df.to_csv(path, index=False)
    return path


def test_profile_csv_dataset_includes_numeric_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_profile_dataset(tmp_path)

    profile = profile_csv_dataset("profile.csv")
    numeric_profile = next(
        item for item in profile.numeric_columns if item.column == "numeric_value"
    )

    assert numeric_profile.count == 4
    assert numeric_profile.mean == 2.5
    assert numeric_profile.median == 2.5
    assert numeric_profile.max == 4.0


def test_profile_csv_dataset_includes_categorical_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_MAX_CATEGORICAL_VALUES", "1")
    write_profile_dataset(tmp_path)

    profile = profile_csv_dataset("profile.csv")
    categorical_profile = next(
        item for item in profile.categorical_columns if item.column == "category"
    )

    assert categorical_profile.count == 3
    assert categorical_profile.unique_count == 2
    assert categorical_profile.top_value == "north"
    assert categorical_profile.top_value_frequency == 2
    assert len(categorical_profile.top_values) == 1
    assert profile.profiling_limits.max_categorical_values == 1


def test_profile_csv_dataset_includes_boolean_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_profile_dataset(tmp_path)

    profile = profile_csv_dataset("profile.csv")
    boolean_profile = next(item for item in profile.boolean_columns if item.column == "is_active")

    assert boolean_profile.true_count == 2
    assert boolean_profile.false_count == 1
    assert boolean_profile.missing_count == 1


def test_profile_csv_dataset_includes_datetime_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_profile_dataset(tmp_path)

    profile = profile_csv_dataset("profile.csv")
    datetime_profile = next(
        item for item in profile.datetime_columns if item.column == "event_date"
    )

    assert datetime_profile.count == 3
    assert datetime_profile.min == "2024-01-01T00:00:00"
    assert datetime_profile.max == "2024-01-04T00:00:00"


def test_profile_csv_dataset_keeps_missing_value_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_profile_dataset(tmp_path)

    profile = profile_csv_dataset("profile.csv")

    assert profile.missing_values["mixed_missing"] == 2
    assert profile.missing_percentage["mixed_missing"] == 50.0
