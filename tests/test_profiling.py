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


def test_profile_csv_dataset_includes_richer_numeric_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    pd.DataFrame({"value": [1] * 20 + [100]}).to_csv(tmp_path / "numeric.csv", index=False)

    profile = profile_csv_dataset("numeric.csv")
    numeric_profile = profile.numeric_columns[0]

    assert numeric_profile.iqr == 0.0
    assert numeric_profile.robust_spread == 0.0
    assert numeric_profile.histogram
    assert numeric_profile.skewness is not None
    assert numeric_profile.z_score_outlier_count is None
    assert any(signal.signal == "near_constant" for signal in numeric_profile.quality_signals)


def test_profile_csv_dataset_includes_categorical_quality_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    pd.DataFrame({"category": ["main"] * 20 + ["rare"]}).to_csv(
        tmp_path / "categorical.csv",
        index=False,
    )

    profile = profile_csv_dataset("categorical.csv")
    categorical_profile = profile.categorical_columns[0]

    assert categorical_profile.rare_category_count == 1
    assert categorical_profile.rare_category_mass > 0
    assert categorical_profile.entropy is not None
    assert categorical_profile.normalized_entropy is not None
    assert any(signal.signal == "near_constant" for signal in categorical_profile.quality_signals)


def test_profile_csv_dataset_includes_dataset_quality_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    pd.DataFrame(
        {
            "id": ["a", "b", "c", "d", "e"],
            "group": ["x", "x", "y", "y", "y"],
            "empty": [None, None, None, None, None],
            "constant": ["same", "same", "same", "same", "same"],
            "notes": [
                "long narrative text value for one row",
                "another long narrative text value",
                "third long narrative text value",
                "fourth long narrative text value",
                "fourth long narrative text value",
            ],
        }
    ).to_csv(tmp_path / "quality.csv", index=False)

    profile = profile_csv_dataset("quality.csv")

    assert profile.data_quality.duplicate_row_count == 0
    assert [item.column for item in profile.data_quality.empty_columns] == ["empty"]
    assert "constant" in {item.column for item in profile.data_quality.one_value_columns}
    assert any(item.column == "notes" for item in profile.data_quality.probable_free_text_columns)
    assert any(item.column == "id" for item in profile.data_quality.possible_identifier_columns)
    assert any(item.columns == ["id", "group"] for item in profile.data_quality.candidate_keys)


def test_profile_csv_dataset_reports_duplicate_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    pd.DataFrame({"left": [1, 1, 2], "right": ["a", "a", "b"]}).to_csv(
        tmp_path / "duplicates.csv",
        index=False,
    )

    profile = profile_csv_dataset("duplicates.csv")

    assert profile.data_quality.duplicate_row_count == 1
    assert profile.data_quality.duplicate_row_percentage == pytest.approx(33.33)
