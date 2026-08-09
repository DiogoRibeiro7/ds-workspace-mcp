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
from sklearn.model_selection import (  # type: ignore[import-untyped]
    GroupShuffleSplit,
    train_test_split,
)

from ds_workspace_mcp.core import read_csv_dataset
from ds_workspace_mcp.exceptions import InsufficientDataError

TaskType = Literal["regression", "binary_classification", "multiclass_classification"]
ValidationStrategy = Literal["random", "stratified", "chronological", "grouped"]
MIN_BASELINE_ROWS = 10


class ValidationSplitConfig(BaseModel):
    """Configuration for baseline train/test splitting."""

    strategy: ValidationStrategy
    test_size: float = 0.2
    random_state: int | None = 42
    time_column: str | None = None
    group_column: str | None = None
    shuffle: bool = True


class ValidationSplitMetadata(BaseModel):
    """Metadata describing the train/test split used for evaluation."""

    strategy: ValidationStrategy
    test_size: float
    random_state: int | None = None
    shuffle: bool
    stratified: bool = False
    time_column: str | None = None
    group_column: str | None = None
    train_start_time: str | None = None
    train_end_time: str | None = None
    test_start_time: str | None = None
    test_end_time: str | None = None
    train_group_count: int | None = None
    test_group_count: int | None = None
    group_overlap: bool | None = None


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
    weighted_f1: float


class BaselineEvaluationResult(BaseModel):
    """Structured result for a baseline model evaluation."""

    file_name: str
    target_column: str
    task_type: TaskType
    train_rows: int = Field(ge=0)
    test_rows: int = Field(ge=0)
    regression_metrics: RegressionMetrics | None = None
    classification_metrics: ClassificationMetrics | None = None
    class_counts: dict[str, int] | None = None
    train_class_counts: dict[str, int] | None = None
    test_class_counts: dict[str, int] | None = None
    validation: ValidationSplitMetadata


def evaluate_baseline_model_dataset(
    file_name: str,
    target_column: str,
    task_type: str,
    test_size: float = 0.2,
    random_state: int = 42,
    validation_strategy: str | None = None,
    time_column: str | None = None,
    group_column: str | None = None,
    shuffle: bool | None = None,
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

    class_counts = (
        _validate_classification_target_support(
            y=cleaned[target_column],
            task_type=validated_task_type,
            test_size=test_size,
        )
        if validated_task_type != "regression"
        else None
    )

    split_config = _build_validation_split_config(
        df=cleaned,
        target_column=target_column,
        task_type=validated_task_type,
        test_size=test_size,
        random_state=random_state,
        validation_strategy=validation_strategy,
        time_column=time_column,
        group_column=group_column,
        shuffle=shuffle,
    )
    X_train, X_test, y_train, y_test, split_metadata = _split_dataset(
        df=cleaned,
        target_column=target_column,
        config=split_config,
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
            validation=split_metadata,
        )

    assert class_counts is not None
    return _evaluate_classification(
        file_name=file_name,
        target_column=target_column,
        task_type=validated_task_type,
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        validation=split_metadata,
        class_counts=class_counts,
    )


def _build_validation_split_config(
    df: pd.DataFrame,
    target_column: str,
    task_type: TaskType,
    test_size: float,
    random_state: int,
    validation_strategy: str | None,
    time_column: str | None,
    group_column: str | None,
    shuffle: bool | None,
) -> ValidationSplitConfig:
    """Build a coherent split configuration from backward-compatible arguments."""

    validated_strategy = _select_validation_strategy(
        df=df,
        target_column=target_column,
        task_type=task_type,
        requested_strategy=validation_strategy,
        time_column=time_column,
        group_column=group_column,
        test_size=test_size,
    )
    effective_shuffle = shuffle if shuffle is not None else validated_strategy != "chronological"
    if validated_strategy == "chronological" and effective_shuffle:
        raise ValueError("chronological validation cannot use shuffle=True.")
    if validated_strategy in {"random", "stratified"} and effective_shuffle is False:
        raise ValueError(f"{validated_strategy} validation requires shuffle=True.")

    return ValidationSplitConfig(
        strategy=validated_strategy,
        test_size=test_size,
        random_state=random_state if validated_strategy != "chronological" else None,
        time_column=time_column,
        group_column=group_column,
        shuffle=effective_shuffle,
    )


def _select_validation_strategy(
    df: pd.DataFrame,
    target_column: str,
    task_type: TaskType,
    requested_strategy: str | None,
    time_column: str | None,
    group_column: str | None,
    test_size: float,
) -> ValidationStrategy:
    """Select and validate the split strategy."""

    if requested_strategy is not None:
        validated_strategy = _validate_validation_strategy(requested_strategy)
        _validate_strategy_arguments(
            strategy=validated_strategy,
            task_type=task_type,
            time_column=time_column,
            group_column=group_column,
        )
        return validated_strategy

    if group_column is not None:
        if time_column is not None:
            raise ValueError("Only one validation column can be supplied.")
        return "grouped"
    if time_column is not None:
        return "chronological"
    if task_type in {"binary_classification", "multiclass_classification"} and _can_stratify(
        df[target_column],
        test_size=test_size,
    ):
        return "stratified"
    return "random"


def _split_dataset(
    df: pd.DataFrame,
    target_column: str,
    config: ValidationSplitConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series[Any], pd.Series[Any], ValidationSplitMetadata]:
    """Split a dataset according to the configured validation strategy."""

    if config.strategy == "chronological":
        return _split_chronological(df=df, target_column=target_column, config=config)
    if config.strategy == "grouped":
        return _split_grouped(df=df, target_column=target_column, config=config)

    y = df[target_column]
    X = df.drop(columns=[target_column])
    stratify = y if config.strategy == "stratified" else None
    if config.strategy == "stratified":
        _validate_stratification_feasibility(y, test_size=config.test_size)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=config.test_size,
        random_state=config.random_state,
        shuffle=config.shuffle,
        stratify=stratify,
    )
    metadata = ValidationSplitMetadata(
        strategy=config.strategy,
        test_size=config.test_size,
        random_state=config.random_state,
        shuffle=config.shuffle,
        stratified=config.strategy == "stratified",
    )
    return X_train, X_test, y_train, y_test, metadata


def _split_chronological(
    df: pd.DataFrame,
    target_column: str,
    config: ValidationSplitConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series[Any], pd.Series[Any], ValidationSplitMetadata]:
    """Split by sorted timestamp, holding out the newest observations."""

    if config.time_column is None:
        raise ValueError("chronological validation requires time_column.")
    _validate_column_exists(df, config.time_column)

    parsed_time = pd.to_datetime(df[config.time_column], errors="coerce")
    if parsed_time.isna().any():
        raise ValueError("chronological validation requires parseable non-null timestamps.")

    ordered = df.assign(__validation_time=parsed_time).sort_values(
        "__validation_time",
        kind="mergesort",
    )
    split_index = _resolve_split_index(row_count=len(ordered), test_size=config.test_size)
    train = ordered.iloc[:split_index].drop(columns=["__validation_time"])
    test = ordered.iloc[split_index:].drop(columns=["__validation_time"])
    train_time = parsed_time.loc[train.index]
    test_time = parsed_time.loc[test.index]
    metadata = ValidationSplitMetadata(
        strategy="chronological",
        test_size=config.test_size,
        random_state=None,
        shuffle=False,
        time_column=config.time_column,
        train_start_time=_format_timestamp(train_time.min()),
        train_end_time=_format_timestamp(train_time.max()),
        test_start_time=_format_timestamp(test_time.min()),
        test_end_time=_format_timestamp(test_time.max()),
    )
    return _split_xy(train, test, target_column, metadata)


def _split_grouped(
    df: pd.DataFrame,
    target_column: str,
    config: ValidationSplitConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series[Any], pd.Series[Any], ValidationSplitMetadata]:
    """Split by holding out complete groups."""

    if config.group_column is None:
        raise ValueError("grouped validation requires group_column.")
    _validate_column_exists(df, config.group_column)
    if df[config.group_column].isna().any():
        raise ValueError("grouped validation requires non-null group values.")

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=config.test_size,
        random_state=config.random_state,
    )
    try:
        indices = list(
            splitter.split(
                df,
                df[target_column],
                groups=df[config.group_column],
            )
        )
    except ValueError as exc:
        raise InsufficientDataError(
            "grouped validation could not create a train/test split."
        ) from exc
    if not indices:
        raise InsufficientDataError("grouped validation could not create a train/test split.")
    train_index, test_index = indices[0]
    train = df.iloc[train_index]
    test = df.iloc[test_index]
    train_groups = {str(value) for value in train[config.group_column].dropna().unique().tolist()}
    test_groups = {str(value) for value in test[config.group_column].dropna().unique().tolist()}
    metadata = ValidationSplitMetadata(
        strategy="grouped",
        test_size=config.test_size,
        random_state=config.random_state,
        shuffle=True,
        group_column=config.group_column,
        train_group_count=len(train_groups),
        test_group_count=len(test_groups),
        group_overlap=bool(train_groups & test_groups),
    )
    return _split_xy(train, test, target_column, metadata)


def _split_xy(
    train: pd.DataFrame,
    test: pd.DataFrame,
    target_column: str,
    metadata: ValidationSplitMetadata,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series[Any], pd.Series[Any], ValidationSplitMetadata]:
    """Return feature and target splits with shared metadata."""

    return (
        train.drop(columns=[target_column]),
        test.drop(columns=[target_column]),
        train[target_column],
        test[target_column],
        metadata,
    )


def _evaluate_regression(
    file_name: str,
    target_column: str,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series[Any],
    y_test: pd.Series[Any],
    validation: ValidationSplitMetadata,
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
        validation=validation,
    )


def _evaluate_classification(
    file_name: str,
    target_column: str,
    task_type: TaskType,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series[Any],
    y_test: pd.Series[Any],
    validation: ValidationSplitMetadata,
    class_counts: dict[str, int],
) -> BaselineEvaluationResult:
    """Evaluate a dummy classifier baseline."""

    train_class_counts = _count_classes(y_train)
    test_class_counts = _count_classes(y_test)
    _validate_classification_split_representation(
        class_counts=class_counts,
        train_class_counts=train_class_counts,
        test_class_counts=test_class_counts,
    )

    model = DummyClassifier(strategy="most_frequent")
    model.fit(X_train, y_train)
    predictions = model.predict(X_test).tolist()
    y_true = cast(list[object], y_test.tolist())

    metrics = ClassificationMetrics(
        accuracy=float(accuracy_score(y_true, predictions)),
        balanced_accuracy=float(balanced_accuracy_score(y_true, predictions)),
        macro_f1=float(f1_score(y_true, predictions, average="macro", zero_division=0)),
        weighted_f1=float(f1_score(y_true, predictions, average="weighted", zero_division=0)),
    )
    return BaselineEvaluationResult(
        file_name=file_name,
        target_column=target_column,
        task_type=task_type,
        train_rows=len(X_train),
        test_rows=len(X_test),
        classification_metrics=metrics,
        class_counts=class_counts,
        train_class_counts=train_class_counts,
        test_class_counts=test_class_counts,
        validation=validation,
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


def _validate_validation_strategy(validation_strategy: str) -> ValidationStrategy:
    """Validate the requested validation strategy."""

    valid_strategies: set[ValidationStrategy] = {
        "random",
        "stratified",
        "chronological",
        "grouped",
    }
    if validation_strategy not in valid_strategies:
        raise ValueError(
            "validation_strategy must be one of: random, stratified, chronological, grouped."
        )
    return validation_strategy


def _validate_strategy_arguments(
    strategy: ValidationStrategy,
    task_type: TaskType,
    time_column: str | None,
    group_column: str | None,
) -> None:
    """Reject validation strategy arguments that cannot be applied coherently."""

    if strategy == "stratified" and task_type == "regression":
        raise ValueError("stratified validation requires a classification task_type.")
    if strategy == "chronological":
        if time_column is None:
            raise ValueError("chronological validation requires time_column.")
        if group_column is not None:
            raise ValueError("chronological validation cannot use group_column.")
        return
    if strategy == "grouped":
        if group_column is None:
            raise ValueError("grouped validation requires group_column.")
        if time_column is not None:
            raise ValueError("grouped validation cannot use time_column.")
        return
    if time_column is not None or group_column is not None:
        raise ValueError(f"{strategy} validation cannot use time_column or group_column.")


def _validate_target_column(df: pd.DataFrame, target_column: str) -> None:
    """Ensure the target column exists."""

    if target_column not in df.columns:
        raise ValueError(f"Unknown target column: {target_column}")


def _validate_column_exists(df: pd.DataFrame, column_name: str) -> None:
    """Ensure an optional split column exists."""

    if column_name not in df.columns:
        raise ValueError(f"Unknown validation column: {column_name}")


def _validate_test_size(test_size: float) -> None:
    """Validate the train/test split fraction."""

    if test_size <= 0 or test_size >= 1:
        raise ValueError("test_size must be greater than 0 and less than 1.")


def _validate_stratification_feasibility(y: pd.Series[Any], test_size: float) -> None:
    """Validate that stratified splitting can preserve class representation."""

    class_counts = y.value_counts(dropna=False)
    class_count = len(class_counts)
    test_rows = max(1, int(len(y) * test_size + 0.999999))
    train_rows = len(y) - test_rows
    if class_count < 2:
        raise InsufficientDataError("stratified validation requires at least two classes.")
    if class_counts.min() < 2:
        raise InsufficientDataError("stratified validation requires at least two rows per class.")
    if test_rows < class_count or train_rows < class_count:
        raise InsufficientDataError(
            "stratified validation requires enough train and test rows for every class."
        )


def _validate_classification_target_support(
    y: pd.Series[Any],
    task_type: TaskType,
    test_size: float,
) -> dict[str, int]:
    """Validate class support before creating any classification split."""

    class_counts = _count_classes(y)
    class_count = len(class_counts)

    if task_type == "binary_classification" and class_count != 2:
        raise ValueError("Binary classification requires exactly 2 target classes.")
    if task_type == "multiclass_classification" and class_count < 3:
        raise ValueError("Multiclass classification requires at least 3 target classes.")

    _validate_stratification_feasibility(y, test_size=test_size)
    return class_counts


def _validate_classification_split_representation(
    class_counts: dict[str, int],
    train_class_counts: dict[str, int],
    test_class_counts: dict[str, int],
) -> None:
    """Ensure classification metrics are computed on representative holdouts."""

    expected_classes = set(class_counts)
    if set(train_class_counts) != expected_classes or set(test_class_counts) != expected_classes:
        raise InsufficientDataError(
            "classification validation requires every class in both train and test splits."
        )


def _count_classes(y: pd.Series[Any]) -> dict[str, int]:
    """Return stable string-keyed class counts for JSON output."""

    counts = y.map(str).value_counts(dropna=False).sort_index()
    return {str(label): int(count) for label, count in counts.items()}


def _can_stratify(y: pd.Series[Any], test_size: float) -> bool:
    """Return whether stratified splitting is feasible."""

    try:
        _validate_stratification_feasibility(y, test_size=test_size)
    except InsufficientDataError:
        return False
    return True


def _resolve_split_index(row_count: int, test_size: float) -> int:
    """Return the chronological split index with non-empty train and test sets."""

    test_rows = max(1, int(row_count * test_size + 0.999999))
    split_index = row_count - test_rows
    if split_index <= 0 or split_index >= row_count:
        raise InsufficientDataError("test_size produced an empty train or test split.")
    return split_index


def _format_timestamp(value: pd.Timestamp) -> str:
    """Format split timestamp boundaries for JSON output."""

    return value.isoformat()
