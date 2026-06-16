from __future__ import annotations

from pydantic import BaseModel, Field

from ds_workspace_mcp.core import detect_csv_dataset_issues, profile_csv_dataset
from ds_workspace_mcp.diagnostics import CorrelationPair, summarize_correlations_dataset

MAX_OVERVIEW_COLUMNS = 8
MAX_OVERVIEW_CORRELATIONS = 3
MAX_OVERVIEW_ISSUES = 5


class DatasetOverview(BaseModel):
    """Compact first-pass overview for a dataset."""

    file_name: str
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    sample_columns: list[str]
    numeric_column_count: int = Field(ge=0)
    categorical_column_count: int = Field(ge=0)
    boolean_column_count: int = Field(ge=0)
    datetime_column_count: int = Field(ge=0)
    columns_with_missing_values: list[str]
    high_missingness_columns: list[str]
    possible_identifier_columns: list[str]
    top_correlations: list[CorrelationPair]
    recommended_next_tools: list[str]
    summary: str


def summarize_dataset_overview(file_name: str) -> DatasetOverview:
    """Build a concise overview from the existing profiling and diagnostics tools."""

    profile = profile_csv_dataset(file_name)
    issues = detect_csv_dataset_issues(file_name)
    correlations = summarize_correlations_dataset(file_name)

    columns_with_missing_values = sorted(
        column for column, missing_count in profile.missing_values.items() if missing_count > 0
    )
    high_missingness_columns = sorted(
        issue.column for issue in issues if issue.issue_type == "high_missingness"
    )
    possible_identifier_columns = sorted(
        issue.column for issue in issues if issue.issue_type == "possible_identifier"
    )

    recommended_next_tools = _build_recommended_next_tools(
        has_numeric=bool(profile.numeric_columns),
        has_datetime=bool(profile.datetime_columns),
        has_possible_identifier=bool(possible_identifier_columns),
    )

    top_correlation_pairs = correlations.top_correlations[:MAX_OVERVIEW_CORRELATIONS]
    summary = _build_summary(
        row_count=profile.row_count,
        column_count=profile.column_count,
        numeric_column_count=len(profile.numeric_columns),
        columns_with_missing_values=columns_with_missing_values,
        high_missingness_columns=high_missingness_columns,
        possible_identifier_columns=possible_identifier_columns,
        top_correlations=top_correlation_pairs,
    )

    return DatasetOverview(
        file_name=file_name,
        row_count=profile.row_count,
        column_count=profile.column_count,
        sample_columns=profile.columns[:MAX_OVERVIEW_COLUMNS],
        numeric_column_count=len(profile.numeric_columns),
        categorical_column_count=len(profile.categorical_columns),
        boolean_column_count=len(profile.boolean_columns),
        datetime_column_count=len(profile.datetime_columns),
        columns_with_missing_values=columns_with_missing_values,
        high_missingness_columns=high_missingness_columns[:MAX_OVERVIEW_ISSUES],
        possible_identifier_columns=possible_identifier_columns[:MAX_OVERVIEW_ISSUES],
        top_correlations=top_correlation_pairs,
        recommended_next_tools=recommended_next_tools,
        summary=summary,
    )


def _build_recommended_next_tools(
    has_numeric: bool,
    has_datetime: bool,
    has_possible_identifier: bool,
) -> list[str]:
    """Recommend the next most useful MCP tools for exploration."""

    recommendations = ["profile_csv", "detect_csv_issues", "suggest_target_columns"]
    if has_numeric:
        recommendations.append("summarize_correlations")
    if has_datetime:
        recommendations.append("validate_time_series_dataset")
    if has_possible_identifier:
        recommendations.append("query_csv_with_duckdb")
    return recommendations


def _build_summary(
    row_count: int,
    column_count: int,
    numeric_column_count: int,
    columns_with_missing_values: list[str],
    high_missingness_columns: list[str],
    possible_identifier_columns: list[str],
    top_correlations: list[CorrelationPair],
) -> str:
    """Create a readable one-paragraph summary."""

    parts = [f"Dataset has {row_count} rows and {column_count} columns."]
    parts.append(f"Detected {numeric_column_count} numeric columns.")

    if columns_with_missing_values:
        parts.append(
            f"{len(columns_with_missing_values)} columns contain missing values."
        )
    else:
        parts.append("No missing values were detected.")

    if high_missingness_columns:
        high_missingness_text = ", ".join(high_missingness_columns[:MAX_OVERVIEW_ISSUES])
        parts.append(
            f"High-missingness columns: {high_missingness_text}."
        )

    if possible_identifier_columns:
        parts.append(
            "Possible identifier columns: "
            + ", ".join(possible_identifier_columns[:MAX_OVERVIEW_ISSUES])
            + "."
        )

    if top_correlations:
        strongest = top_correlations[0]
        parts.append(
            "Strongest numeric relationship: "
            f"{strongest.left_column} vs {strongest.right_column} "
            f"({strongest.correlation:.2f})."
        )

    return " ".join(parts)
