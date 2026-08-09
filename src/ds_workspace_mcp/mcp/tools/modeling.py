from __future__ import annotations

import logging

from ds_workspace_mcp.experiment_plan import ExperimentPlanResult, build_experiment_plan_dataset
from ds_workspace_mcp.feature_selection import (
    FeatureSelectionResult,
    suggest_feature_columns_dataset,
)
from ds_workspace_mcp.mcp.app import _mcp_tool
from ds_workspace_mcp.ml.baselines import BaselineEvaluationResult, evaluate_baseline_model_dataset
from ds_workspace_mcp.modeling_readiness import (
    ModelingReadinessResult,
    assess_modeling_readiness_dataset,
)
from ds_workspace_mcp.modeling_report import ModelingReportResult, build_modeling_report_dataset
from ds_workspace_mcp.report_export import SavedModelingReport, save_modeling_report_dataset
from ds_workspace_mcp.targeting import TargetSuggestionResult, suggest_target_columns_dataset
from ds_workspace_mcp.tracing import traced_operation

logger = logging.getLogger(__name__)


@_mcp_tool()
def suggest_target_columns(file_name: str) -> TargetSuggestionResult:
    """
    Suggest plausible target columns for modeling.

    Args:
        file_name: CSV file name inside the configured data directory.

    Returns:
        Ranked target candidates with suggested task types and reasoning.
    """

    with traced_operation(
        "tool.suggest_target_columns",
        {"tool.name": "suggest_target_columns", "dataset.file_name": file_name},
    ):
        logger.info("Tool suggest_target_columns invoked file_name=%s", file_name)
        return suggest_target_columns_dataset(file_name=file_name)


@_mcp_tool()
def suggest_feature_columns(file_name: str, target_column: str) -> FeatureSelectionResult:
    """
    Suggest which feature columns to include, review, or exclude for modeling.

    Args:
        file_name: CSV file name inside the configured data directory.
        target_column: Target column to protect against leakage and trivial features.

    Returns:
        Structured feature-selection guidance for a baseline modeling workflow.
    """

    with traced_operation(
        "tool.suggest_feature_columns",
        {
            "tool.name": "suggest_feature_columns",
            "dataset.file_name": file_name,
            "tool.target_column": target_column,
        },
    ):
        logger.info(
            "Tool suggest_feature_columns invoked file_name=%s target_column=%s",
            file_name,
            target_column,
        )
        return suggest_feature_columns_dataset(
            file_name=file_name,
            target_column=target_column,
        )


@_mcp_tool()
def assess_modeling_readiness(
    file_name: str,
    target_column: str | None = None,
) -> ModelingReadinessResult:
    """
    Assess whether a dataset is ready for a first supervised modeling iteration.

    Args:
        file_name: CSV file name inside the configured data directory.
        target_column: Optional target override. When omitted, the top suggested target is used.

    Returns:
        A compact orchestration of target selection, feature review, and leakage checks.
    """

    with traced_operation(
        "tool.assess_modeling_readiness",
        {
            "tool.name": "assess_modeling_readiness",
            "dataset.file_name": file_name,
            "tool.target_column": target_column,
        },
    ):
        logger.info(
            "Tool assess_modeling_readiness invoked file_name=%s target_column=%s",
            file_name,
            target_column,
        )
        return assess_modeling_readiness_dataset(
            file_name=file_name,
            target_column=target_column,
        )


@_mcp_tool()
def build_experiment_plan(
    file_name: str,
    target_column: str | None = None,
) -> ExperimentPlanResult:
    """
    Build a concrete first-pass modeling experiment plan for a dataset.

    Args:
        file_name: CSV file name inside the configured data directory.
        target_column: Optional target override. When omitted, the top suggested target is used.

    Returns:
        A structured experiment plan with starter models, risks, metrics, and next steps.
    """

    with traced_operation(
        "tool.build_experiment_plan",
        {
            "tool.name": "build_experiment_plan",
            "dataset.file_name": file_name,
            "tool.target_column": target_column,
        },
    ):
        logger.info(
            "Tool build_experiment_plan invoked file_name=%s target_column=%s",
            file_name,
            target_column,
        )
        return build_experiment_plan_dataset(
            file_name=file_name,
            target_column=target_column,
        )


@_mcp_tool()
def build_modeling_report(
    file_name: str,
    target_column: str | None = None,
) -> ModelingReportResult:
    """
    Build a markdown modeling report artifact for a dataset.

    Args:
        file_name: CSV file name inside the configured data directory.
        target_column: Optional target override. When omitted, the top suggested target is used.

    Returns:
        A compact markdown report suitable for review or handoff.
    """

    with traced_operation(
        "tool.build_modeling_report",
        {
            "tool.name": "build_modeling_report",
            "dataset.file_name": file_name,
            "tool.target_column": target_column,
        },
    ):
        logger.info(
            "Tool build_modeling_report invoked file_name=%s target_column=%s",
            file_name,
            target_column,
        )
        return build_modeling_report_dataset(
            file_name=file_name,
            target_column=target_column,
        )


@_mcp_tool()
def save_modeling_report(
    file_name: str,
    target_column: str | None = None,
    output_name: str | None = None,
    overwrite: bool = False,
) -> SavedModelingReport:
    """
    Save a modeling report artifact into the local reports directory.

    Args:
        file_name: CSV file name inside the configured data directory.
        target_column: Optional target override. When omitted, the top suggested target is used.
        output_name: Optional markdown file name inside `reports/`.
        overwrite: Replace an existing report with the same output name when true.

    Returns:
        Metadata about the saved report artifact.
    """

    with traced_operation(
        "tool.save_modeling_report",
        {
            "tool.name": "save_modeling_report",
            "dataset.file_name": file_name,
            "tool.target_column": target_column,
            "tool.output_name": output_name,
            "tool.overwrite": overwrite,
        },
    ):
        logger.info(
            "Tool save_modeling_report invoked file_name=%s target_column=%s "
            "output_name=%s overwrite=%s",
            file_name,
            target_column,
            output_name,
            overwrite,
        )
        return save_modeling_report_dataset(
            file_name=file_name,
            target_column=target_column,
            output_name=output_name,
            overwrite=overwrite,
        )


@_mcp_tool()
def evaluate_baseline_model(
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
    """Evaluate a dummy baseline model for a supervised learning task."""

    with traced_operation(
        "tool.evaluate_baseline_model",
        {
            "tool.name": "evaluate_baseline_model",
            "dataset.file_name": file_name,
            "tool.target_column": target_column,
            "tool.task_type": task_type,
            "tool.validation_strategy": validation_strategy,
        },
    ):
        logger.info(
            "Tool evaluate_baseline_model invoked file_name=%s target_column=%s "
            "task_type=%s validation_strategy=%s",
            file_name,
            target_column,
            task_type,
            validation_strategy,
        )
        return evaluate_baseline_model_dataset(
            file_name=file_name,
            target_column=target_column,
            task_type=task_type,
            test_size=test_size,
            random_state=random_state,
            validation_strategy=validation_strategy,
            time_column=time_column,
            group_column=group_column,
            shuffle=shuffle,
        )
