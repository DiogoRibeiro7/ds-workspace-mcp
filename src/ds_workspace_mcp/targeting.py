from __future__ import annotations

from typing import Any, Literal

import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
    is_string_dtype,
)
from pydantic import BaseModel, Field

from ds_workspace_mcp.core import read_csv_dataset

SuggestedTaskType = Literal[
    "regression",
    "binary_classification",
    "multiclass_classification",
    "review_manually",
]
MAX_TARGET_CANDIDATES = 10


class TargetCandidate(BaseModel):
    """One suggested target column for downstream modeling."""

    column: str
    score: float
    suggested_task_type: SuggestedTaskType
    non_null_count: int = Field(ge=0)
    unique_count: int = Field(ge=0)
    missing_percentage: float = Field(ge=0.0, le=100.0)
    reasons: list[str]


class TargetSuggestionResult(BaseModel):
    """Ranked target suggestions for a dataset."""

    file_name: str
    candidates: list[TargetCandidate]
    summary: str


def suggest_target_columns_dataset(file_name: str) -> TargetSuggestionResult:
    """Suggest plausible target columns for modeling and forecasting workflows."""

    df = read_csv_dataset(file_name)
    candidates = [_build_target_candidate(df, column) for column in df.columns]
    ranked_candidates = sorted(
        candidates,
        key=lambda candidate: (candidate.score, candidate.unique_count, candidate.non_null_count),
        reverse=True,
    )[:MAX_TARGET_CANDIDATES]

    summary = _build_summary(ranked_candidates)
    return TargetSuggestionResult(
        file_name=file_name,
        candidates=ranked_candidates,
        summary=summary,
    )


def _build_target_candidate(df: pd.DataFrame, column: object) -> TargetCandidate:
    """Build one scored target candidate from a dataframe column."""

    column_name = str(column)
    series = df[column]
    non_null = series.dropna()
    non_null_count = int(non_null.count())
    unique_count = int(non_null.nunique())
    missing_percentage = round(float(series.isna().mean() * 100), 2)

    score = 0.0
    reasons: list[str] = []

    if non_null_count >= 10:
        score += 2.0
        reasons.append("enough non-null rows for baseline evaluation")
    else:
        reasons.append("limited non-null rows")

    if missing_percentage == 0:
        score += 1.0
        reasons.append("no missing target values")
    elif missing_percentage <= 10:
        score += 0.5
        reasons.append("low missingness")
    elif missing_percentage >= 30:
        score -= 1.0
        reasons.append("high missingness")

    if _is_identifier_like(series):
        score -= 3.0
        reasons.append("looks like an identifier rather than an outcome")

    if _is_datetime_like(series):
        score -= 2.0
        reasons.append("looks like a time column and is better used as context")

    task_type = _suggest_task_type(series)
    if task_type == "regression":
        score += 1.5
        reasons.append("numeric target suitable for regression")
    elif task_type == "binary_classification":
        score += 1.5
        reasons.append("two classes suitable for binary classification")
    elif task_type == "multiclass_classification":
        score += 1.0
        reasons.append("manageable class count for multiclass classification")
    else:
        reasons.append("task type should be reviewed manually")

    return TargetCandidate(
        column=column_name,
        score=round(score, 2),
        suggested_task_type=task_type,
        non_null_count=non_null_count,
        unique_count=unique_count,
        missing_percentage=missing_percentage,
        reasons=reasons,
    )


def _suggest_task_type(series: pd.Series[Any]) -> SuggestedTaskType:
    """Infer a plausible modeling task type from the column shape."""

    non_null = series.dropna()
    unique_count = int(non_null.nunique())

    if unique_count < 2:
        return "review_manually"

    if _is_datetime_like(series):
        return "review_manually"

    if _is_boolean_like(series) or unique_count == 2:
        return "binary_classification"

    if _is_numeric_like(series):
        if unique_count >= 10:
            return "regression"
        if 3 <= unique_count <= 20:
            return "multiclass_classification"
        return "review_manually"

    if 3 <= unique_count <= 20:
        return "multiclass_classification"

    return "review_manually"


def _is_numeric_like(series: pd.Series[Any]) -> bool:
    """Return whether a series behaves like a numeric target."""

    return bool(is_numeric_dtype(series) and not is_bool_dtype(series))


def _is_boolean_like(series: pd.Series[Any]) -> bool:
    """Return whether a series behaves like a boolean target."""

    if is_bool_dtype(series):
        return True

    values = [str(value).strip().lower() for value in series.dropna().tolist()]
    if not values:
        return False
    return all(value in {"true", "false", "yes", "no", "0", "1"} for value in values)


def _is_identifier_like(series: pd.Series[Any]) -> bool:
    """Return whether a column looks more like an identifier than an outcome."""

    non_null = series.dropna()
    if non_null.empty:
        return False
    unique_ratio = float(non_null.nunique() / max(len(series), 1))
    return unique_ratio > 0.95


def _is_datetime_like(series: pd.Series[Any]) -> bool:
    """Conservatively detect datetime-like columns."""

    if is_datetime64_any_dtype(series):
        return True

    if _is_numeric_like(series):
        return False

    if not (is_object_dtype(series) or is_string_dtype(series)):
        return False

    non_null = series.dropna()
    if non_null.empty:
        return False

    values = [str(value).strip() for value in non_null.tolist()]
    if not any(any(marker in value for marker in ("-", "/", ":", "T")) for value in values):
        return False

    parsed = pd.to_datetime(non_null, errors="coerce")
    return bool(not parsed.isna().any())


def _build_summary(candidates: list[TargetCandidate]) -> str:
    """Create a short human-readable summary of ranked target suggestions."""

    if not candidates:
        return "No target candidates were identified."

    top_candidate = candidates[0]
    return (
        f"Top target candidate is `{top_candidate.column}` "
        f"for {top_candidate.suggested_task_type} "
        f"with score {top_candidate.score:.2f}."
    )
