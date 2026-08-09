from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.exceptions import InsufficientDataError
from ds_workspace_mcp.ml.baselines import (
    ValidationSplitConfig,
    _split_dataset,
    evaluate_baseline_model_dataset,
)


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
    assert result.validation.strategy == "random"
    assert result.validation.random_state == 42


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
    assert result.classification_metrics.weighted_f1 >= 0
    assert result.regression_metrics is None
    assert result.class_counts == {"no": 10, "yes": 10}
    assert result.train_class_counts == {"no": 8, "yes": 8}
    assert result.test_class_counts == {"no": 2, "yes": 2}
    assert result.validation.strategy == "stratified"
    assert result.validation.stratified is True


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
    assert result.class_counts == {"class_0": 10, "class_1": 10, "class_2": 10}
    assert result.train_class_counts == {"class_0": 8, "class_1": 8, "class_2": 8}
    assert result.test_class_counts == {"class_0": 2, "class_1": 2, "class_2": 2}
    assert result.validation.strategy == "stratified"


def test_random_validation_split_is_deterministic_for_fixed_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "feature": list(range(40)),
            "target": [float(value) for value in range(40)],
        }
    )
    write_baseline_dataset(tmp_path, "deterministic.csv", df)

    first = evaluate_baseline_model_dataset(
        file_name="deterministic.csv",
        target_column="target",
        task_type="regression",
        validation_strategy="random",
        random_state=7,
    )
    second = evaluate_baseline_model_dataset(
        file_name="deterministic.csv",
        target_column="target",
        task_type="regression",
        validation_strategy="random",
        random_state=7,
    )

    assert first.model_dump() == second.model_dump()


def test_classification_validation_split_is_deterministic_for_fixed_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "feature": list(range(40)),
            "target": ["yes" if value % 2 == 0 else "no" for value in range(40)],
        }
    )
    write_baseline_dataset(tmp_path, "classification_deterministic.csv", df)

    first = evaluate_baseline_model_dataset(
        file_name="classification_deterministic.csv",
        target_column="target",
        task_type="binary_classification",
        validation_strategy="stratified",
        random_state=13,
    )
    second = evaluate_baseline_model_dataset(
        file_name="classification_deterministic.csv",
        target_column="target",
        task_type="binary_classification",
        validation_strategy="stratified",
        random_state=13,
    )

    assert first.model_dump() == second.model_dump()


def test_highly_imbalanced_binary_classification_reports_represented_holdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "feature": list(range(50)),
            "target": ["majority"] * 45 + ["minority"] * 5,
        }
    )
    write_baseline_dataset(tmp_path, "imbalanced.csv", df)

    result = evaluate_baseline_model_dataset(
        file_name="imbalanced.csv",
        target_column="target",
        task_type="binary_classification",
        test_size=0.2,
        random_state=23,
    )

    assert result.validation.strategy == "stratified"
    assert result.class_counts == {"majority": 45, "minority": 5}
    assert result.train_class_counts == {"majority": 36, "minority": 4}
    assert result.test_class_counts == {"majority": 9, "minority": 1}


def test_stratified_classification_split_preserves_class_distribution() -> None:
    df = pd.DataFrame(
        {
            "feature": list(range(100)),
            "target": ["yes" if value % 2 == 0 else "no" for value in range(100)],
        }
    )

    _, _, y_train, y_test, metadata = _split_dataset(
        df=df,
        target_column="target",
        config=ValidationSplitConfig(
            strategy="stratified",
            test_size=0.2,
            random_state=3,
            shuffle=True,
        ),
    )

    assert metadata.strategy == "stratified"
    assert metadata.stratified is True
    assert y_train.value_counts().to_dict() == {"yes": 40, "no": 40}
    assert y_test.value_counts().to_dict() == {"yes": 10, "no": 10}


def test_chronological_validation_holds_out_newest_observations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=24, freq="D"),
            "feature": list(range(24)),
            "target": [float(value) for value in range(24)],
        }
    ).sample(frac=1.0, random_state=11)
    write_baseline_dataset(tmp_path, "chronological.csv", df)

    result = evaluate_baseline_model_dataset(
        file_name="chronological.csv",
        target_column="target",
        task_type="regression",
        validation_strategy="chronological",
        time_column="date",
        test_size=0.25,
    )

    assert result.validation.strategy == "chronological"
    assert result.validation.shuffle is False
    assert result.validation.random_state is None
    assert result.validation.train_end_time is not None
    assert result.validation.test_start_time is not None
    assert result.validation.train_end_time < result.validation.test_start_time


def test_grouped_validation_keeps_groups_disjoint() -> None:
    df = pd.DataFrame(
        {
            "group": [f"group_{value // 3}" for value in range(30)],
            "feature": list(range(30)),
            "target": [float(value) for value in range(30)],
        }
    )

    X_train, X_test, _, _, metadata = _split_dataset(
        df=df,
        target_column="target",
        config=ValidationSplitConfig(
            strategy="grouped",
            test_size=0.3,
            random_state=5,
            group_column="group",
            shuffle=True,
        ),
    )

    assert set(X_train["group"]).isdisjoint(set(X_test["group"]))
    assert metadata.group_overlap is False
    assert metadata.train_group_count is not None
    assert metadata.test_group_count is not None


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

    with pytest.raises(InsufficientDataError, match="at least"):
        evaluate_baseline_model_dataset(
            file_name="small.csv",
            target_column="target",
            task_type="regression",
        )


def test_chronological_validation_requires_time_column(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame({"feature": list(range(12)), "target": [float(value) for value in range(12)]})
    write_baseline_dataset(tmp_path, "missing_time.csv", df)

    with pytest.raises(ValueError, match="chronological validation requires time_column"):
        evaluate_baseline_model_dataset(
            file_name="missing_time.csv",
            target_column="target",
            task_type="regression",
            validation_strategy="chronological",
        )


def test_grouped_validation_requires_group_column(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame({"feature": list(range(12)), "target": [float(value) for value in range(12)]})
    write_baseline_dataset(tmp_path, "missing_group.csv", df)

    with pytest.raises(ValueError, match="grouped validation requires group_column"):
        evaluate_baseline_model_dataset(
            file_name="missing_group.csv",
            target_column="target",
            task_type="regression",
            validation_strategy="grouped",
        )


def test_stratified_validation_rejects_impossible_class_support(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "feature": list(range(20)),
            "target": ["majority"] * 19 + ["singleton"],
        }
    )
    write_baseline_dataset(tmp_path, "singleton.csv", df)

    with pytest.raises(InsufficientDataError, match="at least two rows per class"):
        evaluate_baseline_model_dataset(
            file_name="singleton.csv",
            target_column="target",
            task_type="binary_classification",
        )


def test_classification_validation_rejects_test_size_too_small_for_classes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "feature": list(range(20)),
            "target": [f"class_{value % 4}" for value in range(20)],
        }
    )
    write_baseline_dataset(tmp_path, "too_small_test.csv", df)

    with pytest.raises(InsufficientDataError, match="enough train and test rows"):
        evaluate_baseline_model_dataset(
            file_name="too_small_test.csv",
            target_column="target",
            task_type="multiclass_classification",
            test_size=0.1,
        )


def test_classification_validation_rejects_split_missing_test_classes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=30, freq="D"),
            "feature": list(range(30)),
            "target": ["class_a"] * 10 + ["class_b"] * 10 + ["class_c"] * 10,
        }
    )
    write_baseline_dataset(tmp_path, "missing_test_classes.csv", df)

    with pytest.raises(InsufficientDataError, match="every class in both train and test"):
        evaluate_baseline_model_dataset(
            file_name="missing_test_classes.csv",
            target_column="target",
            task_type="multiclass_classification",
            validation_strategy="chronological",
            time_column="date",
            test_size=0.2,
        )


def test_random_validation_rejects_non_shuffle_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    df = pd.DataFrame({"feature": list(range(12)), "target": [float(value) for value in range(12)]})
    write_baseline_dataset(tmp_path, "non_shuffle.csv", df)

    with pytest.raises(ValueError, match="random validation requires shuffle=True"):
        evaluate_baseline_model_dataset(
            file_name="non_shuffle.csv",
            target_column="target",
            task_type="regression",
            validation_strategy="random",
            shuffle=False,
        )
