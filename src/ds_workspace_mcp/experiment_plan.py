from __future__ import annotations

from pydantic import BaseModel, Field

from ds_workspace_mcp.modeling_readiness import (
    ModelingReadinessResult,
    assess_modeling_readiness_dataset,
)


class ModelCandidate(BaseModel):
    """One suggested model family for an initial experiment cycle."""

    name: str
    rationale: str


class ExperimentPlanResult(BaseModel):
    """Structured first-pass experiment plan for a dataset."""

    file_name: str
    target_column: str
    target_source: str
    suggested_task_type: str
    validation_strategy: str
    recommended_validation_strategy: str
    recommended_time_column: str | None = None
    recommended_group_column: str | None = None
    feature_columns: list[str] = Field(default_factory=list)
    review_columns: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    baseline_models: list[ModelCandidate] = Field(default_factory=list)
    evaluation_metrics: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    summary: str


def build_experiment_plan_dataset(
    file_name: str,
    target_column: str | None = None,
) -> ExperimentPlanResult:
    """Build a practical first modeling plan from the readiness workflow."""

    readiness = assess_modeling_readiness_dataset(
        file_name=file_name,
        target_column=target_column,
    )

    baseline_models = _build_baseline_models(readiness)
    evaluation_metrics = _build_evaluation_metrics(readiness)
    risks = _build_risks(readiness)
    next_steps = _build_next_steps(readiness)

    return ExperimentPlanResult(
        file_name=file_name,
        target_column=readiness.target_column,
        target_source=readiness.target_source,
        suggested_task_type=readiness.suggested_task_type,
        validation_strategy=readiness.validation_strategy,
        recommended_validation_strategy=readiness.recommended_validation_strategy,
        recommended_time_column=readiness.recommended_time_column,
        recommended_group_column=readiness.recommended_group_column,
        feature_columns=readiness.feature_selection.include_columns,
        review_columns=readiness.feature_selection.review_columns,
        risks=risks,
        baseline_models=baseline_models,
        evaluation_metrics=evaluation_metrics,
        next_steps=next_steps,
        summary=_build_summary(readiness, baseline_models, risks),
    )


def _build_baseline_models(readiness: ModelingReadinessResult) -> list[ModelCandidate]:
    """Suggest realistic starter models for the detected task."""

    if readiness.validation_strategy == "time_series_review":
        return [
            ModelCandidate(
                name="seasonal_naive_baseline",
                rationale="Sets a time-aware floor before feature-based forecasting models.",
            ),
            ModelCandidate(
                name="linear_regression_with_lags",
                rationale=(
                    "Provides an interpretable regression baseline "
                    "once lag features are engineered."
                ),
            ),
            ModelCandidate(
                name="tree_boosting_regressor",
                rationale=(
                    "Captures nonlinear effects after the time split "
                    "and feature pipeline are stable."
                ),
            ),
        ]

    if readiness.suggested_task_type == "regression":
        return [
            ModelCandidate(
                name="dummy_regressor_mean",
                rationale="Quantifies the minimum bar that learned regressors must beat.",
            ),
            ModelCandidate(
                name="linear_regression",
                rationale=(
                    "Fast interpretable baseline for numeric targets with mixed feature types."
                ),
            ),
            ModelCandidate(
                name="random_forest_regressor",
                rationale="Useful nonlinear baseline when interactions may matter.",
            ),
        ]

    if readiness.suggested_task_type == "binary_classification":
        return [
            ModelCandidate(
                name="dummy_classifier_most_frequent",
                rationale="Sets the minimum bar against majority-class prediction.",
            ),
            ModelCandidate(
                name="logistic_regression",
                rationale="Strong interpretable first learned baseline for binary labels.",
            ),
            ModelCandidate(
                name="random_forest_classifier",
                rationale="Useful nonlinear comparison once leakage risks are handled.",
            ),
        ]

    if readiness.suggested_task_type == "multiclass_classification":
        return [
            ModelCandidate(
                name="dummy_classifier_most_frequent",
                rationale="Sets the minimum bar before multiclass learning starts.",
            ),
            ModelCandidate(
                name="multinomial_logistic_regression",
                rationale="Simple interpretable multiclass baseline for encoded tabular features.",
            ),
            ModelCandidate(
                name="gradient_boosted_trees",
                rationale=(
                    "Strong tabular benchmark after label quality and feature encoding are stable."
                ),
            ),
        ]

    return [
        ModelCandidate(
            name="manual_problem_framing_review",
            rationale="Target semantics should be clarified before model implementation starts.",
        )
    ]


def _build_evaluation_metrics(readiness: ModelingReadinessResult) -> list[str]:
    """Return the most useful starter metrics for the detected task."""

    if readiness.suggested_task_type == "regression":
        return ["mae", "rmse", "r2"]

    if readiness.suggested_task_type == "binary_classification":
        return ["accuracy", "balanced_accuracy", "macro_f1", "precision_recall_review"]

    if readiness.suggested_task_type == "multiclass_classification":
        return ["accuracy", "balanced_accuracy", "macro_f1", "confusion_matrix_review"]

    return ["manual_target_review"]


def _build_risks(readiness: ModelingReadinessResult) -> list[str]:
    """Summarize the most important modeling risks from readiness checks."""

    risks: list[str] = []

    if readiness.validation_strategy == "time_series_review":
        risks.append("Datetime context is present, so random splits may overstate performance.")

    if readiness.feature_selection.review_columns:
        review_columns = ", ".join(readiness.feature_selection.review_columns[:5])
        risks.append(f"Some features need review before modeling: {review_columns}.")

    if readiness.leakage_warnings:
        warning_columns = sorted({warning.column for warning in readiness.leakage_warnings})
        risks.append(
            "Potential leakage signals were detected in: " + ", ".join(warning_columns[:5]) + "."
        )

    if not readiness.feature_selection.include_columns:
        risks.append("No clean default feature set was identified yet.")

    if not risks:
        risks.append("No major heuristic blockers were detected for a first baseline iteration.")

    return risks


def _build_next_steps(readiness: ModelingReadinessResult) -> list[str]:
    """Convert readiness results into a concrete execution sequence."""

    steps: list[str] = []

    if readiness.feature_selection.review_columns:
        steps.append("Review and transform flagged columns before training.")

    if readiness.validation_strategy == "time_series_review":
        steps.append(
            "Run the built-in baseline evaluation with chronological validation and then "
            "engineer lag or calendar features."
        )

    steps.append(
        "Run the built-in baseline evaluation for the chosen target using "
        f"`{readiness.recommended_validation_strategy}` validation."
    )
    steps.append("Compare the baseline against one linear model and one tree-based model.")

    if readiness.leakage_warnings:
        steps.append("Exclude or justify every leakage warning before reporting results.")

    return steps


def _build_summary(
    readiness: ModelingReadinessResult,
    baseline_models: list[ModelCandidate],
    risks: list[str],
) -> str:
    """Create a short human-readable experiment-plan summary."""

    top_model = baseline_models[0].name if baseline_models else "manual_review"
    return (
        f"Plan a {readiness.suggested_task_type} experiment for `{readiness.target_column}` "
        f"using {len(readiness.feature_selection.include_columns)} default features, "
        f"`{top_model}` as the first baseline family, "
        f"and {len(risks)} key risks to monitor."
    )
