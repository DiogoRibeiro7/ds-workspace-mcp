from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.overview import summarize_dataset_overview


def write_overview_dataset(root: Path, name: str = "overview.csv") -> Path:
    """Create a dataset that exercises the dataset overview tool."""

    path = root / name
    df = pd.DataFrame(
        {
            "record_id": [101, 102, 103, 104, 105, 106],
            "date": [
                "2024-01-01",
                "2024-01-02",
                "2024-01-03",
                "2024-01-04",
                "2024-01-05",
                "2024-01-06",
            ],
            "target": [10, 12, 14, 16, 18, 20],
            "target_shadow": [10, 12, 14, 16, 18, 20],
            "feature": [1, 2, 3, 4, 5, 6],
            "mostly_missing": [None, None, None, "known", None, None],
        }
    )
    df.to_csv(path, index=False)
    return path


def test_summarize_dataset_overview_returns_compact_readout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_overview_dataset(tmp_path)

    overview = summarize_dataset_overview("overview.csv")

    assert overview.file_name == "overview.csv"
    assert overview.row_count == 6
    assert overview.column_count == 6
    assert overview.numeric_column_count >= 3
    assert "mostly_missing" in overview.columns_with_missing_values
    assert "mostly_missing" in overview.high_missingness_columns
    assert "record_id" in overview.possible_identifier_columns
    assert overview.top_correlations
    assert "summarize_correlations" in overview.recommended_next_tools
    assert "validate_time_series_dataset" in overview.recommended_next_tools
    assert "Strongest numeric relationship" in overview.summary


def test_summarize_dataset_overview_handles_dataset_without_missing_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    path = tmp_path / "clean.csv"
    pd.DataFrame(
        {
            "value": [1, 2, 3],
            "score": [2, 4, 6],
        }
    ).to_csv(path, index=False)

    overview = summarize_dataset_overview("clean.csv")

    assert overview.columns_with_missing_values == []
    assert overview.high_missingness_columns == []
    assert "No missing values were detected." in overview.summary
