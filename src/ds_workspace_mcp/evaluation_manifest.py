from __future__ import annotations

import platform
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from ds_workspace_mcp import __version__
from ds_workspace_mcp.config import get_settings
from ds_workspace_mcp.core import get_dataset_registry
from ds_workspace_mcp.datasets import DatasetRef
from ds_workspace_mcp.feature_selection import FeatureSuggestion


class ManifestFeatureDecision(BaseModel):
    """Feature decision metadata retained for reproducibility."""

    column: str
    decision: str
    reasons: list[str] = Field(default_factory=list)


class ManifestTrainTestBoundaries(BaseModel):
    """Train/test boundary metadata without storing dataset records."""

    train_start_time: str | None = None
    train_end_time: str | None = None
    test_start_time: str | None = None
    test_end_time: str | None = None
    train_rows: int | None = Field(default=None, ge=0)
    test_rows: int | None = Field(default=None, ge=0)
    evaluated_points: int | None = Field(default=None, ge=0)


class ManifestConfigBounds(BaseModel):
    """Relevant runtime bounds that can affect evaluation or report output."""

    max_preview_rows: int
    max_sql_rows: int
    max_sql_query_length: int
    sql_timeout_ms: int
    max_categorical_values: int
    max_dataset_bytes: int
    profile_cache_enabled: bool
    profile_cache_max_entries: int


class EvaluationManifest(BaseModel):
    """Serializable metadata explaining how an evaluation design was produced."""

    dataset_fingerprint: str
    dataset_name: str
    selected_target: str
    selected_features: list[str] = Field(default_factory=list)
    review_features: list[ManifestFeatureDecision] = Field(default_factory=list)
    excluded_features: list[ManifestFeatureDecision] = Field(default_factory=list)
    task_type: str
    validation_strategy: str
    random_seed: int | None = None
    time_column: str | None = None
    group_column: str | None = None
    train_test_boundaries: ManifestTrainTestBoundaries
    baseline_definition: str
    metric_definitions: dict[str, str] = Field(default_factory=dict)
    package_version: str
    python_version: str
    config_bounds: ManifestConfigBounds
    generated_at: str


def build_evaluation_manifest(
    *,
    file_name: str,
    selected_target: str,
    selected_features: list[str],
    review_features: list[ManifestFeatureDecision] | None = None,
    excluded_features: list[ManifestFeatureDecision] | None = None,
    task_type: str,
    validation_strategy: str,
    random_seed: int | None,
    time_column: str | None,
    group_column: str | None,
    train_test_boundaries: ManifestTrainTestBoundaries,
    baseline_definition: str,
    metric_definitions: dict[str, str],
) -> EvaluationManifest:
    """Build path-free evaluation provenance for a dataset workflow."""

    fingerprint = get_dataset_registry().fingerprint(DatasetRef(file_name=file_name))
    return EvaluationManifest(
        dataset_fingerprint=fingerprint.cache_token,
        dataset_name=file_name,
        selected_target=selected_target,
        selected_features=selected_features,
        review_features=review_features or [],
        excluded_features=excluded_features or [],
        task_type=task_type,
        validation_strategy=validation_strategy,
        random_seed=random_seed,
        time_column=time_column,
        group_column=group_column,
        train_test_boundaries=train_test_boundaries,
        baseline_definition=baseline_definition,
        metric_definitions=metric_definitions,
        package_version=__version__,
        python_version=platform.python_version(),
        config_bounds=_manifest_config_bounds(),
        generated_at=datetime.now(UTC).isoformat(),
    )


def manifest_decisions_from_feature_suggestions(
    suggestions: list[FeatureSuggestion],
    *,
    decision: str,
) -> list[ManifestFeatureDecision]:
    """Extract feature decision metadata for one decision type."""

    return [
        ManifestFeatureDecision(
            column=suggestion.column,
            decision=suggestion.decision,
            reasons=suggestion.reasons,
        )
        for suggestion in suggestions
        if suggestion.decision == decision
    ]


def _manifest_config_bounds() -> ManifestConfigBounds:
    settings = get_settings()
    return ManifestConfigBounds(
        max_preview_rows=settings.mcp_max_preview_rows,
        max_sql_rows=settings.mcp_max_sql_rows,
        max_sql_query_length=settings.mcp_max_sql_query_length,
        sql_timeout_ms=settings.mcp_sql_timeout_ms,
        max_categorical_values=settings.mcp_max_categorical_values,
        max_dataset_bytes=settings.mcp_max_dataset_bytes,
        profile_cache_enabled=settings.mcp_profile_cache_enabled,
        profile_cache_max_entries=settings.mcp_profile_cache_max_entries,
    )
