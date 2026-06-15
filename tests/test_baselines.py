from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.ml.baselines import evaluate_baseline_model_dataset


def write_baseline_dataset(root: Path, name: str, df: pd.DataFrame) -> Path:
    """Write a baseline-evaluation fixture dataset."""

    path = root / name
    df.to_csv(path, index=False)
    return path


def test_evaluate_baseline_model_regression(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "feature": list(range(20)),
            "target": [value * 1.5 for value in range(20)],
        }
    )
    write_baseline_dataset(tmp_path, "regression.csv", df)

    result = evaluate_baseline_model_dataset(
        file_name="regression.csv",
        target_column="target",
        task_type="regression",
    )

    assert result.regression_metrics is not None
    assert result.classification_metrics is None
    assert result.test_rows > 0


def test_evaluate_baseline_model_binary_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "feature": list(range(20)),
            "target": ["yes" if value % 2 == 0 else "no" for value in range(20)],
        }
    )
    write_baseline_dataset(tmp_path, "binary.csv", df)

    result = evaluate_baseline_model_dataset(
        file_name="binary.csv",
        target_column="target",
        task_type="binary_classification",
    )

    assert result.classification_metrics is not None
    assert result.regression_metrics is None


def test_evaluate_baseline_model_multiclass_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "feature": list(range(30)),
            "target": [f"class_{value % 3}" for value in range(30)],
        }
    )
    write_baseline_dataset(tmp_path, "multiclass.csv", df)

    result = evaluate_baseline_model_dataset(
        file_name="multiclass.csv",
        target_column="target",
        task_type="multiclass_classification",
    )

    assert result.classification_metrics is not None
    assert result.task_type == "multiclass_classification"


def test_evaluate_baseline_model_missing_target_column(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame({"feature": list(range(12)), "value": list(range(12))})
    write_baseline_dataset(tmp_path, "missing.csv", df)

    with pytest.raises(ValueError, match="Unknown target column"):
        evaluate_baseline_model_dataset(
            file_name="missing.csv",
            target_column="target",
            task_type="regression",
        )


def test_evaluate_baseline_model_too_few_samples(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame({"feature": list(range(4)), "target": [1.0, 2.0, 3.0, 4.0]})
    write_baseline_dataset(tmp_path, "small.csv", df)

    with pytest.raises(ValueError, match="at least"):
        evaluate_baseline_model_dataset(
            file_name="small.csv",
            target_column="target",
            task_type="regression",
        )
