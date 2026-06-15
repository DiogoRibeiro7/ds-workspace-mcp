from __future__ import annotations

from typing import Any, Literal, cast

import pandas as pd
from pydantic import BaseModel, Field
from sklearn.dummy import DummyClassifier, DummyRegressor  # type: ignore[import-untyped]
from sklearn.metrics import (  # type: ignore[import-untyped]
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split  # type: ignore[import-untyped]

from ds_workspace_mcp.core import read_csv_dataset
from ds_workspace_mcp.exceptions import InsufficientDataError

TaskType = Literal["regression", "binary_classification", "multiclass_classification"]
MIN_BASELINE_ROWS = 10


class RegressionMetrics(BaseModel):
    """Regression metrics for a baseline model."""

    mae: float
    rmse: float
    r2: float


class ClassificationMetrics(BaseModel):
    """Classification metrics for a baseline model."""

    accuracy: float
    balanced_accuracy: float
    macro_f1: float


class BaselineEvaluationResult(BaseModel):
    """Structured result for a baseline model evaluation."""

    file_name: str
    target_column: str
    task_type: TaskType
    train_rows: int = Field(ge=0)
    test_rows: int = Field(ge=0)
    regression_metrics: RegressionMetrics | None = None
    classification_metrics: ClassificationMetrics | None = None


def evaluate_baseline_model_dataset(
    file_name: str,
    target_column: str,
    task_type: str,
    test_size: float = 0.2,
    random_state: int = 42,
) -> BaselineEvaluationResult:
    """Evaluate a simple dummy baseline for the requested task."""

    validated_task_type = _validate_task_type(task_type)
    df = read_csv_dataset(file_name)
    _validate_target_column(df, target_column)
    _validate_test_size(test_size)

    cleaned = df.dropna(subset=[target_column]).copy()
    if len(cleaned) < MIN_BASELINE_ROWS:
        raise InsufficientDataError(
            f"Target column must have at least {MIN_BASELINE_ROWS} non-null rows for evaluation."
        )

    y = cleaned[target_column]
    X = cleaned.drop(columns=[target_column])
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
    )

    if len(X_test) == 0 or len(X_train) == 0:
        raise InsufficientDataError("test_size produced an empty train or test split.")

    if validated_task_type == "regression":
        return _evaluate_regression(
            file_name=file_name,
            target_column=target_column,
            X_train=X_train,
            X_test=X_test,
            y_train=y_train,
            y_test=y_test,
        )

    return _evaluate_classification(
        file_name=file_name,
        target_column=target_column,
        task_type=validated_task_type,
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
    )


def _evaluate_regression(
    file_name: str,
    target_column: str,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series[Any],
    y_test: pd.Series[Any],
) -> BaselineEvaluationResult:
    """Evaluate a dummy regressor baseline."""

    y_train_numeric = pd.to_numeric(y_train, errors="coerce")
    y_test_numeric = pd.to_numeric(y_test, errors="coerce")
    if y_train_numeric.isna().any() or y_test_numeric.isna().any():
        raise ValueError("Regression targets must be numeric.")

    model = DummyRegressor(strategy="mean")
    model.fit(X_train, y_train_numeric)
    predictions = cast(list[float], model.predict(X_test).tolist())
    y_true = cast(list[float], y_test_numeric.tolist())

    metrics = RegressionMetrics(
        mae=float(mean_absolute_error(y_true, predictions)),
        rmse=float(mean_squared_error(y_true, predictions) ** 0.5),
        r2=float(r2_score(y_true, predictions)),
    )
    return BaselineEvaluationResult(
        file_name=file_name,
        target_column=target_column,
        task_type="regression",
        train_rows=len(X_train),
        test_rows=len(X_test),
        regression_metrics=metrics,
    )


def _evaluate_classification(
    file_name: str,
    target_column: str,
    task_type: TaskType,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series[Any],
    y_test: pd.Series[Any],
) -> BaselineEvaluationResult:
    """Evaluate a dummy classifier baseline."""

    train_classes = pd.Series(y_train).dropna().unique().tolist()
    test_classes = pd.Series(y_test).dropna().unique().tolist()
    all_classes = sorted({str(value) for value in train_classes + test_classes})

    if task_type == "binary_classification" and len(all_classes) != 2:
        raise ValueError("Binary classification requires exactly 2 target classes.")
    if task_type == "multiclass_classification" and len(all_classes) < 3:
        raise ValueError("Multiclass classification requires at least 3 target classes.")

    model = DummyClassifier(strategy="most_frequent")
    model.fit(X_train, y_train)
    predictions = model.predict(X_test).tolist()
    y_true = cast(list[object], y_test.tolist())

    metrics = ClassificationMetrics(
        accuracy=float(accuracy_score(y_true, predictions)),
        balanced_accuracy=float(balanced_accuracy_score(y_true, predictions)),
        macro_f1=float(f1_score(y_true, predictions, average="macro")),
    )
    return BaselineEvaluationResult(
        file_name=file_name,
        target_column=target_column,
        task_type=task_type,
        train_rows=len(X_train),
        test_rows=len(X_test),
        classification_metrics=metrics,
    )


def _validate_task_type(task_type: str) -> TaskType:
    """Validate the requested task type."""

    valid_task_types: set[TaskType] = {
        "regression",
        "binary_classification",
        "multiclass_classification",
    }
    if task_type not in valid_task_types:
        raise ValueError(
            "task_type must be one of: regression, binary_classification, "
            "multiclass_classification."
        )
    return task_type


def _validate_target_column(df: pd.DataFrame, target_column: str) -> None:
    """Ensure the target column exists."""

    if target_column not in df.columns:
        raise ValueError(f"Unknown target column: {target_column}")


def _validate_test_size(test_size: float) -> None:
    """Validate the train/test split fraction."""

    if test_size <= 0 or test_size >= 1:
        raise ValueError("test_size must be greater than 0 and less than 1.")
