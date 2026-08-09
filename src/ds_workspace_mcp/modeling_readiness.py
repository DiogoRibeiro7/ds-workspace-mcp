from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ds_workspace_mcp.core import profile_csv_dataset, read_csv_dataset
from ds_workspace_mcp.diagnostics import (
    LeakageWarning,
    detect_possible_target_leakage_dataset,
)
from ds_workspace_mcp.feature_selection import (
    FeatureSelectionResult,
    suggest_feature_columns_dataset,
)
from ds_workspace_mcp.targeting import (
    TargetCandidate,
    TargetSuggestionResult,
    suggest_target_columns_dataset,
)

ValidationStrategy = Literal["standard_train_test_split", "time_series_review"]


class ModelingReadinessResult(BaseModel):
    """High-level modeling readiness summary for one dataset and target choice."""

    file_name: str
    target_column: str
    target_source: Literal["requested", "suggested"]
    suggested_task_type: str
    validation_strategy: ValidationStrategy
    recommended_validation_strategy: str
    recommended_time_column: str | None = None
    recommended_group_column: str | None = None
    target_candidate: TargetCandidate | None = None
    target_suggestions: list[TargetCandidate] = Field(default_factory=list)
    feature_selection: FeatureSelectionResult
    leakage_warnings: list[LeakageWarning] = Field(default_factory=list)
    recommended_next_tools: list[str]
    summary: str


def assess_modeling_readiness_dataset(
    file_name: str,
    target_column: str | None = None,
) -> ModelingReadinessResult:
    """Assess how ready a dataset is for a first supervised modeling iteration."""

    df = read_csv_dataset(file_name)
    target_suggestions = suggest_target_columns_dataset(file_name)
    selected_target, target_source, target_candidate = _select_target_candidate(
        df_columns=[str(column) for column in df.columns],
        target_suggestions=target_suggestions,
        requested_target=target_column,
    )
    feature_selection = suggest_feature_columns_dataset(
        file_name=file_name,
        target_column=selected_target,
    )
    leakage_summary = detect_possible_target_leakage_dataset(
        file_name=file_name,
        target_column=selected_target,
    )
    profile = profile_csv_dataset(file_name)
    has_datetime_context = bool(profile.datetime_columns)
    suggested_task_type = (
        target_candidate.suggested_task_type if target_candidate is not None else "review_manually"
    )
    validation_strategy: ValidationStrategy = (
        "time_series_review"
        if has_datetime_context and suggested_task_type == "regression"
        else "standard_train_test_split"
    )
    recommended_time_column = (
        profile.datetime_columns[0].column if validation_strategy == "time_series_review" else None
    )
    recommended_validation_strategy = _build_recommended_validation_strategy(
        suggested_task_type=suggested_task_type,
        validation_strategy=validation_strategy,
    )
    recommended_next_tools = _build_recommended_next_tools(
        suggested_task_type=suggested_task_type,
        validation_strategy=validation_strategy,
        include_feature_count=len(feature_selection.include_columns),
        review_feature_count=len(feature_selection.review_columns),
    )

    return ModelingReadinessResult(
        file_name=file_name,
        target_column=selected_target,
        target_source=target_source,
        suggested_task_type=suggested_task_type,
        validation_strategy=validation_strategy,
        recommended_validation_strategy=recommended_validation_strategy,
        recommended_time_column=recommended_time_column,
        recommended_group_column=None,
        target_candidate=target_candidate,
        target_suggestions=target_suggestions.candidates,
        feature_selection=feature_selection,
        leakage_warnings=leakage_summary.warnings,
        recommended_next_tools=recommended_next_tools,
        summary=_build_summary(
            target_column=selected_target,
            target_source=target_source,
            suggested_task_type=suggested_task_type,
            include_feature_count=len(feature_selection.include_columns),
            review_feature_count=len(feature_selection.review_columns),
            leakage_warning_count=len(leakage_summary.warnings),
            validation_strategy=validation_strategy,
            recommended_validation_strategy=recommended_validation_strategy,
        ),
    )


def _select_target_candidate(
    df_columns: list[str],
    target_suggestions: TargetSuggestionResult,
    requested_target: str | None,
) -> tuple[str, Literal["requested", "suggested"], TargetCandidate | None]:
    """Pick the requested target or the top suggested target candidate."""

    if requested_target is not None:
        if requested_target not in df_columns:
            raise ValueError(f"Unknown target column: {requested_target}")
        for candidate in target_suggestions.candidates:
            if candidate.column == requested_target:
                return requested_target, "requested", candidate
        return requested_target, "requested", None

    if not target_suggestions.candidates:
        raise ValueError("No target candidates were identified.")

    top_candidate = target_suggestions.candidates[0]
    return top_candidate.column, "suggested", top_candidate


def _build_recommended_next_tools(
    suggested_task_type: str,
    validation_strategy: ValidationStrategy,
    include_feature_count: int,
    review_feature_count: int,
) -> list[str]:
    """Recommend the next most useful tools after the readiness summary."""

    recommendations: list[str] = []
    if review_feature_count > 0:
        recommendations.append("suggest_feature_columns")
    if validation_strategy == "time_series_review":
        recommendations.append("validate_time_series_dataset")
    recommendations.append("detect_possible_target_leakage")
    if suggested_task_type != "review_manually" and include_feature_count > 0:
        recommendations.append("evaluate_baseline_model")
    return recommendations


def _build_recommended_validation_strategy(
    suggested_task_type: str,
    validation_strategy: ValidationStrategy,
) -> str:
    """Map advisory readiness language to an executable baseline split strategy."""

    if validation_strategy == "time_series_review":
        return "chronological"
    if suggested_task_type in {"binary_classification", "multiclass_classification"}:
        return "stratified"
    return "random"


def _build_summary(
    target_column: str,
    target_source: Literal["requested", "suggested"],
    suggested_task_type: str,
    include_feature_count: int,
    review_feature_count: int,
    leakage_warning_count: int,
    validation_strategy: ValidationStrategy,
    recommended_validation_strategy: str,
) -> str:
    """Create a short human-readable readiness summary."""

    source_text = "requested" if target_source == "requested" else "top suggested"
    return (
        f"Using the {source_text} target `{target_column}` for {suggested_task_type}, "
        f"with {include_feature_count} included features, "
        f"{review_feature_count} features to review, "
        f"{leakage_warning_count} leakage warnings, "
        f"and {validation_strategy} as the validation default "
        f"mapped to `{recommended_validation_strategy}` baseline evaluation."
    )
