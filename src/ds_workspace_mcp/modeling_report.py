from __future__ import annotations

from pydantic import BaseModel

from ds_workspace_mcp.evaluation_manifest import EvaluationManifest
from ds_workspace_mcp.experiment_plan import ExperimentPlanResult, build_experiment_plan_dataset


class ModelingReportResult(BaseModel):
    """A reviewable modeling report artifact for one dataset."""

    file_name: str
    target_column: str
    headline: str
    markdown: str
    evaluation_manifest: EvaluationManifest


def build_modeling_report_dataset(
    file_name: str,
    target_column: str | None = None,
) -> ModelingReportResult:
    """Build a markdown modeling report from the experiment-planning workflow."""

    plan = build_experiment_plan_dataset(
        file_name=file_name,
        target_column=target_column,
    )
    headline = _build_headline(plan)
    return ModelingReportResult(
        file_name=file_name,
        target_column=plan.target_column,
        headline=headline,
        markdown=_build_markdown(plan, headline),
        evaluation_manifest=plan.evaluation_manifest,
    )


def _build_headline(plan: ExperimentPlanResult) -> str:
    """Create a short decision-oriented report headline."""

    return (
        f"{plan.suggested_task_type} plan for `{plan.target_column}` "
        f"with {len(plan.feature_columns)} default features"
    )


def _build_markdown(plan: ExperimentPlanResult, headline: str) -> str:
    """Render the experiment plan as compact markdown."""

    feature_columns = _format_list(plan.feature_columns)
    review_columns = _format_list(plan.review_columns)
    metrics = _format_list(plan.evaluation_metrics)
    risks = _format_bullets(plan.risks)
    next_steps = _format_bullets(plan.next_steps)
    models = "\n".join(
        f"- `{candidate.name}`: {candidate.rationale}" for candidate in plan.baseline_models
    )

    return "\n".join(
        [
            f"# {headline}",
            "",
            "## Summary",
            plan.summary,
            "",
            "## Setup",
            f"- Dataset: `{plan.file_name}`",
            f"- Target: `{plan.target_column}` ({plan.target_source})",
            f"- Task type: `{plan.suggested_task_type}`",
            f"- Validation strategy: `{plan.validation_strategy}`",
            "",
            "## Feature Scope",
            f"- Default feature columns: {feature_columns}",
            f"- Review columns: {review_columns}",
            "",
            "## Baseline Models",
            models,
            "",
            "## Evaluation Metrics",
            f"- Metrics: {metrics}",
            "",
            "## Evaluation Manifest",
            _format_manifest(plan),
            "",
            "## Risks",
            risks,
            "",
            "## Next Steps",
            next_steps,
        ]
    )


def _format_manifest(plan: ExperimentPlanResult) -> str:
    """Render compact provenance details for saved markdown reports."""

    manifest = plan.evaluation_manifest
    return "\n".join(
        [
            f"- Dataset fingerprint: `{manifest.dataset_fingerprint}`",
            f"- Executable validation strategy: `{manifest.validation_strategy}`",
            f"- Random seed: `{manifest.random_seed}`",
            f"- Time column: `{manifest.time_column}`",
            f"- Group column: `{manifest.group_column}`",
            f"- Selected features: {len(manifest.selected_features)}",
            f"- Review features: {len(manifest.review_features)}",
            f"- Excluded features: {len(manifest.excluded_features)}",
            f"- Package/Python: `{manifest.package_version}` / `{manifest.python_version}`",
            f"- Generated at: `{manifest.generated_at}`",
        ]
    )


def _format_list(values: list[str]) -> str:
    """Format a short inline list for markdown."""

    if not values:
        return "none"
    return ", ".join(f"`{value}`" for value in values)


def _format_bullets(values: list[str]) -> str:
    """Format markdown bullets from free-text items."""

    if not values:
        return "- None."
    return "\n".join(f"- {value}" for value in values)
