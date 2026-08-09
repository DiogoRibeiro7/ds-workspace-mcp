from __future__ import annotations

from typing import Any, Literal

import pandas as pd
from pandas.api.types import (
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
    is_string_dtype,
)
from pydantic import BaseModel, Field

from ds_workspace_mcp.core import read_csv_dataset

FeatureDecisionType = Literal["include", "review", "exclude"]
MAX_FEATURE_SUGGESTIONS = 50
EXCLUDE_MISSINGNESS_THRESHOLD = 60.0
REVIEW_MISSINGNESS_THRESHOLD = 30.0
HIGH_CORRELATION_THRESHOLD = 0.9


class FeatureSuggestion(BaseModel):
    """A suggested modeling decision for one candidate feature column."""

    column: str
    decision: FeatureDecisionType
    missing_percentage: float = Field(ge=0.0, le=100.0)
    unique_count: int = Field(ge=0)
    reasons: list[str]


class FeatureSelectionResult(BaseModel):
    """Structured feature-selection guidance for one target column."""

    file_name: str
    target_column: str
    include_columns: list[str]
    review_columns: list[str]
    exclude_columns: list[str]
    suggestions: list[FeatureSuggestion]
    summary: str


def suggest_feature_columns_dataset(file_name: str, target_column: str) -> FeatureSelectionResult:
    """Suggest which columns to include, review, or exclude for a modeling target."""

    df = read_csv_dataset(file_name)
    if target_column not in df.columns:
        raise ValueError(f"Unknown target column: {target_column}")

    target_series = df[target_column]
    suggestions = [
        _build_feature_suggestion(
            df=df,
            column=column,
            target_column=target_column,
            target_series=target_series,
        )
        for column in df.columns
        if str(column) != target_column
    ]
    ordered_suggestions = sorted(
        suggestions,
        key=lambda suggestion: (
            _decision_rank(suggestion.decision),
            suggestion.missing_percentage,
            suggestion.column,
        ),
    )[:MAX_FEATURE_SUGGESTIONS]

    include_columns = [item.column for item in ordered_suggestions if item.decision == "include"]
    review_columns = [item.column for item in ordered_suggestions if item.decision == "review"]
    exclude_columns = [item.column for item in ordered_suggestions if item.decision == "exclude"]

    return FeatureSelectionResult(
        file_name=file_name,
        target_column=target_column,
        include_columns=include_columns,
        review_columns=review_columns,
        exclude_columns=exclude_columns,
        suggestions=ordered_suggestions,
        summary=_build_summary(
            target_column=target_column,
            include_columns=include_columns,
            review_columns=review_columns,
            exclude_columns=exclude_columns,
        ),
    )


def _build_feature_suggestion(
    df: pd.DataFrame,
    column: object,
    target_column: str,
    target_series: pd.Series[Any],
) -> FeatureSuggestion:
    """Classify one feature column for supervised modeling readiness."""

    column_name = str(column)
    series = df[column]
    non_null = series.dropna()
    unique_count = int(non_null.nunique())
    missing_percentage = round(float(series.isna().mean() * 100), 2)
    is_datetime_column = _is_datetime_like(series)

    reasons: list[str] = []
    decision: FeatureDecisionType = "include"

    if unique_count <= 1:
        decision = "exclude"
        reasons.append("constant or near-constant column adds no modeling signal")

    if _is_duplicate_column(series, target_series):
        decision = "exclude"
        reasons.append(
            "exact_target_duplicate: duplicates the target values and would leak the answer"
        )

    if _is_identifier_like(series, column_name=column_name) and not is_datetime_column:
        decision = "exclude"
        reasons.append("likely_identifier: looks like an identifier rather than a reusable feature")

    if _has_target_name_overlap(column_name, target_column) and decision != "exclude":
        decision = "review"
        reasons.append(
            "suspicious_name_overlap: column name overlaps with the target and needs review"
        )

    if _is_highly_correlated(series, target_series) and decision != "exclude":
        decision = "review"
        reasons.append(
            "very_high_correlation: strong target correlation is evidence for review, not proof"
        )

    if missing_percentage >= EXCLUDE_MISSINGNESS_THRESHOLD:
        decision = "exclude"
        reasons.append("missingness is too high for a default baseline feature set")
    elif missing_percentage >= REVIEW_MISSINGNESS_THRESHOLD and decision != "exclude":
        decision = "review"
        reasons.append("missingness is material and may require imputation")

    if is_datetime_column and decision != "exclude":
        decision = "review"
        reasons.append(
            "temporal_review: time-like column may need feature engineering before modeling"
        )

    if decision == "include" and unique_count > 0:
        reasons.append("looks usable as a baseline feature without immediate red flags")

    if decision == "review" and not reasons:
        reasons.append("feature needs manual review")

    return FeatureSuggestion(
        column=column_name,
        decision=decision,
        missing_percentage=missing_percentage,
        unique_count=unique_count,
        reasons=reasons,
    )


def _decision_rank(decision: FeatureDecisionType) -> int:
    """Sort included features before review and excluded columns."""

    order = {"include": 0, "review": 1, "exclude": 2}
    return order[decision]


def _has_target_name_overlap(column_name: str, target_column: str) -> bool:
    """Return whether the feature name appears to contain the target name."""

    normalized_target = _normalize_name(target_column)
    normalized_column = _normalize_name(column_name)
    if not normalized_target:
        return False
    return normalized_target in normalized_column


def _normalize_name(value: str) -> str:
    """Normalize a column name for heuristic comparisons."""

    return "".join(character for character in value.lower() if character.isalnum())


def _is_identifier_like(series: pd.Series[Any], column_name: str) -> bool:
    """Return whether a column behaves like an identifier."""

    non_null = series.dropna()
    if non_null.empty:
        return False
    unique_ratio = float(non_null.nunique() / max(len(series), 1))
    if unique_ratio <= 0.95:
        return False
    if _has_identifier_name_marker(column_name):
        return True
    return not is_numeric_dtype(series)


def _has_identifier_name_marker(column_name: str) -> bool:
    """Return whether a column name carries identifier semantics."""

    normalized = _normalize_name(column_name)
    return (
        normalized in {"id", "uuid", "key"}
        or normalized.endswith("id")
        or normalized.endswith("uuid")
        or normalized.endswith("key")
    )


def _is_highly_correlated(left: pd.Series[Any], right: pd.Series[Any]) -> bool:
    """Return whether two numeric series are strongly correlated."""

    if not is_numeric_dtype(left) or not is_numeric_dtype(right):
        return False

    combined = pd.concat([left, right], axis=1).dropna()
    if len(combined) < 3:
        return False
    if combined.iloc[:, 0].nunique() <= 1 or combined.iloc[:, 1].nunique() <= 1:
        return False

    correlation = combined.iloc[:, 0].corr(combined.iloc[:, 1])
    if pd.isna(correlation):
        return False
    return abs(float(correlation)) >= HIGH_CORRELATION_THRESHOLD


def _is_duplicate_column(left: pd.Series[Any], right: pd.Series[Any]) -> bool:
    """Return whether two aligned columns have identical non-null values."""

    combined = pd.concat([left, right], axis=1).dropna()
    if combined.empty:
        return False
    return bool(combined.iloc[:, 0].equals(combined.iloc[:, 1]))


def _is_datetime_like(series: pd.Series[Any]) -> bool:
    """Conservatively detect datetime-like columns."""

    if is_datetime64_any_dtype(series):
        return True

    if is_numeric_dtype(series):
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


def _build_summary(
    target_column: str,
    include_columns: list[str],
    review_columns: list[str],
    exclude_columns: list[str],
) -> str:
    """Create a short human-readable feature-selection summary."""

    return (
        f"For target `{target_column}`, include {len(include_columns)} columns, "
        f"review {len(review_columns)}, and exclude {len(exclude_columns)}."
    )
