# API Contract

## Purpose

This document defines the versioned public surface for `ds-workspace-mcp`.

Starting with `v1.0.0`, the names and high-level result shapes listed here are treated as the public contract. Internal modules, helper functions, log messages, and undocumented implementation details are not part of that contract.

## Versioning Rules

The project follows semantic versioning.

- Patch releases may fix bugs, tighten validation, improve documentation, and add non-breaking fields to structured responses.
- Minor releases may add new MCP tools, resources, prompts, CLI commands, environment variables, and optional response fields.
- Major releases may rename or remove public capabilities, change required arguments, or change existing response semantics.

The following are considered breaking changes and require a major release:

- Renaming or removing a documented MCP tool, resource, prompt, CLI command, or environment variable.
- Changing a response field name or removing a documented field.
- Changing an argument name, making an optional argument required, or narrowing accepted values incompatibly.
- Changing a result from structured data to plain text, or vice versa, for an existing capability.

The following are considered non-breaking:

- Adding a new tool, resource, prompt, CLI command, or optional environment variable.
- Adding optional fields to structured responses.
- Improving wording inside heuristic warning descriptions.
- Tightening invalid-input validation where previously undefined behavior existed.

## Public MCP Surface

### Resources

#### `datasets://catalog`

- Stable name: `datasets://catalog`
- Return type: text payload
- Stable behavior: returns newline-separated CSV file names visible under `MCP_DATA_ROOT`
- Empty-state behavior: returns the sentence `No CSV datasets found in the configured data directory.`

#### `databases://sqlite`

- Stable name: `databases://sqlite`
- Return type: text payload
- Stable behavior: returns newline-separated SQLite database file names visible under `MCP_DATA_ROOT`
- Empty-state behavior: returns the sentence `No SQLite databases found in the configured data directory.`

#### `reports://modeling`

- Stable name: `reports://modeling`
- Return type: text payload
- Stable behavior: returns newline-separated markdown report file names visible under the local `reports/` directory
- Empty-state behavior: returns the sentence `No modeling reports found in the local reports directory.`

#### `reports://modeling/latest`

- Stable name: `reports://modeling/latest`
- Return type: text payload
- Stable behavior: returns the markdown content of the most recently modified saved modeling report
- Empty-state behavior: returns the sentence `No modeling reports found in the local reports directory.`

#### `reports://modeling/{output_name}`

- Stable name: `reports://modeling/{output_name}`
- Return type: text payload
- Stable behavior: returns the markdown content of one saved modeling report identified by `output_name`
- Stable parameter:
  - `output_name: str`
- Stable behavior notes:
  - `output_name` must be a single markdown file name inside the configured reports root
  - traversal-style paths are rejected
  - missing reports fail clearly

#### `reports://modeling/latest/sections`

- Stable name: `reports://modeling/latest/sections`
- Return type: structured JSON payload
- Stable behavior: returns section headings from the most recently modified saved modeling report
- Stable item fields:
  - `heading: str`
  - `level: int`
- Stable behavior notes:
  - fails clearly when no saved modeling reports exist

#### `reports://modeling/{output_name}/sections`

- Stable name: `reports://modeling/{output_name}/sections`
- Return type: structured JSON payload
- Stable behavior: returns section headings from one saved modeling report identified by `output_name`
- Stable parameter:
  - `output_name: str`
- Stable item fields:
  - `heading: str`
  - `level: int`
- Stable behavior notes:
  - `output_name` must be a single markdown file name inside the configured reports root
  - traversal-style paths are rejected
  - missing reports fail clearly

#### `reports://modeling/latest/sections/{section_heading}`

- Stable name: `reports://modeling/latest/sections/{section_heading}`
- Return type: text payload
- Stable behavior: returns one section from the most recently modified saved modeling report as markdown
- Stable parameter:
  - `section_heading: str`
- Stable behavior notes:
  - `section_heading` must be a non-empty string
  - fails clearly when no saved modeling reports exist
  - fails clearly when the requested section is not present

#### `reports://modeling/{output_name}/sections/{section_heading}`

- Stable name: `reports://modeling/{output_name}/sections/{section_heading}`
- Return type: text payload
- Stable behavior: returns one section from a saved modeling report as markdown
- Stable parameters:
  - `output_name: str`
  - `section_heading: str`
- Stable behavior notes:
  - `output_name` must be a single markdown file name inside the configured reports root
  - `section_heading` must be a non-empty string
  - traversal-style paths are rejected
  - missing reports fail clearly
  - fails clearly when the requested section is not present

### Tools

#### `summarize_dataset(file_name: str)`

- Stable name: `summarize_dataset`
- Purpose: return a compact first-pass overview of a CSV dataset
- Stable result fields:
  - `file_name: str`
  - `row_count: int`
  - `column_count: int`
  - `sample_columns: list[str]`
  - `numeric_column_count: int`
  - `categorical_column_count: int`
  - `boolean_column_count: int`
  - `datetime_column_count: int`
  - `columns_with_missing_values: list[str]`
  - `high_missingness_columns: list[str]`
  - `possible_identifier_columns: list[str]`
  - `top_correlations: list[CorrelationPair]`
  - `recommended_next_tools: list[str]`
  - `summary: str`
- Heuristic notes:
  - this tool is a compact orchestration of existing profiling, issue-detection, and correlation logic
  - `summary` is intentionally human-readable and may change wording without changing the contract
  - issue highlights and recommended next tools are guidance, not strict prescriptions

#### `compare_datasets(left_file_name: str, right_file_name: str)`

- Stable name: `compare_datasets`
- Purpose: compare two supported datasets for schema changes and lightweight drift diagnostics
- Stable result fields:
  - `left_file_name: str`
  - `right_file_name: str`
  - `schema_diff: DatasetSchemaDiff`
  - `drift: DatasetDriftDiagnostics`
  - `sampling: DatasetComparisonSampling`
- Stable schema-diff fields:
  - `added_columns: list[str]`
  - `removed_columns: list[str]`
  - `dtype_changes: list[ColumnTypeChange]`
  - `null_rate_changes: list[NullRateChange]`
  - `row_count: RowCountChange`
  - `cardinality_changes: list[CardinalityChange]`
- Stable drift fields:
  - `numeric: list[NumericDrift]`
  - `categorical: list[CategoricalDrift]`
  - `timestamp_ranges: list[TimestampRangeChange]`
- Stable sampling fields:
  - `strategy: str`
  - `max_rows_per_dataset: int`
  - `left_rows_analyzed: int`
  - `right_rows_analyzed: int`
  - `left_truncated: bool`
  - `right_truncated: bool`
  - `note: str`
- Heuristic notes:
  - schema changes and drift diagnostics are separate concepts
  - numeric drift reports effect sizes and sample-size evidence, not causal conclusions
  - categorical drift aligns a bounded set of categories and may include an `__other__` bucket
  - large datasets are bounded by the configured SQL row limit and disclose truncation

#### `suggest_target_columns(file_name: str)`

- Stable name: `suggest_target_columns`
- Purpose: suggest plausible target columns for modeling and forecasting workflows
- Stable result fields:
  - `file_name: str`
  - `candidates: list[TargetCandidate]`
  - `summary: str`
- Stable candidate fields:
  - `column: str`
  - `score: float`
  - `suggested_task_type: str`
  - `non_null_count: int`
  - `unique_count: int`
  - `missing_percentage: float`
  - `reasons: list[str]`
- Heuristic notes:
  - suggestions rank columns by practical modeling usefulness, not guaranteed business value
  - identifier-like and datetime-like columns may still appear in the list but are penalized and explained
  - `suggested_task_type` is advisory and should be reviewed against the real use case

#### `suggest_feature_columns(file_name: str, target_column: str)`

- Stable name: `suggest_feature_columns`
- Purpose: suggest which columns to include, review, or exclude for supervised modeling
- Stable result fields:
  - `file_name: str`
  - `target_column: str`
  - `include_columns: list[str]`
  - `review_columns: list[str]`
  - `exclude_columns: list[str]`
  - `suggestions: list[FeatureSuggestion]`
  - `summary: str`
- Stable suggestion fields:
  - `column: str`
  - `decision: str`
  - `missing_percentage: float`
  - `unique_count: int`
  - `reasons: list[str]`
- Heuristic notes:
  - the tool is designed for practical baseline readiness, not definitive feature engineering
  - exact target duplicates, constant columns, excessive missingness, and likely identifiers may be excluded from the default baseline feature set
  - target-name overlap and very high target correlation are review evidence by themselves, not automatic exclusion proof
  - datetime-like and moderately sparse columns are usually marked for review rather than automatic exclusion

#### `assess_modeling_readiness(file_name: str, target_column: str | None = None)`

- Stable name: `assess_modeling_readiness`
- Purpose: orchestrate target suggestion, feature selection, leakage review, and next-step guidance
- Stable result fields:
  - `file_name: str`
  - `target_column: str`
  - `target_source: str`
  - `suggested_task_type: str`
  - `validation_strategy: str`
  - `recommended_validation_strategy: str`
  - `recommended_time_column: str | null`
  - `recommended_group_column: str | null`
  - `target_candidate: TargetCandidate | null`
  - `target_suggestions: list[TargetCandidate]`
  - `feature_selection: FeatureSelectionResult`
  - `leakage_warnings: list[LeakageWarning]`
  - `recommended_next_tools: list[str]`
  - `summary: str`
- Heuristic notes:
  - when `target_column` is omitted, the tool uses the top suggested target candidate
  - `validation_strategy` preserves advisory readiness language, while `recommended_validation_strategy` maps to an executable baseline split strategy
  - time-series review maps to chronological baseline validation with `recommended_time_column` populated when a datetime column is detected
  - this tool summarizes downstream heuristics and does not replace manual target or feature judgment

#### `build_experiment_plan(file_name: str, target_column: str | None = None)`

- Stable name: `build_experiment_plan`
- Purpose: turn the modeling-readiness workflow into a concrete starter experiment plan
- Stable result fields:
  - `file_name: str`
  - `target_column: str`
  - `target_source: str`
  - `suggested_task_type: str`
  - `validation_strategy: str`
  - `recommended_validation_strategy: str`
  - `recommended_time_column: str | null`
  - `recommended_group_column: str | null`
  - `feature_columns: list[str]`
  - `review_columns: list[str]`
  - `risks: list[str]`
  - `baseline_models: list[ModelCandidate]`
  - `evaluation_metrics: list[str]`
  - `next_steps: list[str]`
  - `summary: str`
- Stable model-candidate fields:
  - `name: str`
  - `rationale: str`
- Heuristic notes:
  - model suggestions are planning guidance, not implemented training pipelines
  - baseline model names may refer to standard model families rather than built-in MCP execution capabilities
  - recommended validation fields are directly consumable by `evaluate_baseline_model` for tabular tasks and `evaluate_forecast_baselines` for time-series regression tasks
  - when `target_column` is omitted, the plan uses the top suggested target candidate

#### `build_modeling_report(file_name: str, target_column: str | None = None)`

- Stable name: `build_modeling_report`
- Purpose: render the experiment-planning workflow as a compact markdown artifact
- Stable result fields:
  - `file_name: str`
  - `target_column: str`
  - `headline: str`
  - `markdown: str`
- Heuristic notes:
  - markdown wording may evolve across patch and minor releases
  - the report is intended for human review and handoff rather than machine parsing
  - when `target_column` is omitted, the report uses the top suggested target candidate

#### `save_modeling_report(file_name: str, target_column: str | None = None, output_name: str | None = None, overwrite: bool = False)`

- Stable name: `save_modeling_report`
- Purpose: persist a markdown modeling report into the local `reports/` directory
- Stable result fields:
  - `file_name: str`
  - `target_column: str`
  - `output_path: str`
  - `headline: str`
- Stable behavior:
  - output is always written inside the local `reports/` directory
  - `output_name`, when provided, must be a single markdown file name ending in `.md`
  - existing reports are not overwritten unless `overwrite` is explicitly true
- Heuristic notes:
  - when `target_column` is omitted, the saved report uses the top suggested target candidate
  - default output names are derived from the dataset name and selected target

#### `list_modeling_reports()`

- Stable name: `list_modeling_reports`
- Purpose: list markdown modeling reports saved in the local `reports/` directory
- Stable result shape: `list[StoredModelingReport]`
- Stable item fields:
  - `output_name: str`
  - `output_path: str`
  - `size_bytes: int`
  - `created_at: str`
  - `modified_at: str`
  - `content_sha256: str | None`

#### `search_modeling_reports(query: str)`

- Stable name: `search_modeling_reports`
- Purpose: list markdown modeling reports in the local `reports/` directory whose file names match a case-insensitive substring
- Stable result shape: `list[StoredModelingReport]`
- Stable item fields:
  - `output_name: str`
  - `output_path: str`
  - `size_bytes: int`
  - `created_at: str`
  - `modified_at: str`
  - `content_sha256: str | None`
- Stable behavior:
  - `query` must be a non-empty string

#### `search_modeling_report_content(query: str)`

- Stable name: `search_modeling_report_content`
- Purpose: list markdown modeling reports in the local `reports/` directory whose markdown content matches a case-insensitive text query
- Stable result shape: `list[ReportSearchMatch]`
- Stable item fields:
  - `output_name: str`
  - `output_path: str`
  - `headline: str`
  - `snippet: str`
- Stable behavior:
  - `query` must be a non-empty string
  - `snippet` is intentionally bounded and does not guarantee the full matching paragraph

#### `search_latest_modeling_report_content(query: str)`

- Stable name: `search_latest_modeling_report_content`
- Implementation note: the Python function is named `search_latest_modeling_report_content_tool`
- Purpose: list bounded content matches from the most recently modified saved modeling report
- Stable result shape: `list[ReportSearchMatch]`
- Stable item fields:
  - `output_name: str`
  - `output_path: str`
  - `headline: str`
  - `snippet: str`
- Stable behavior:
  - `query` must be a non-empty string
  - fails clearly when no saved modeling reports exist
  - `snippet` is intentionally bounded and does not guarantee the full matching paragraph

#### `search_modeling_report_sections(query: str)`

- Stable name: `search_modeling_report_sections`
- Purpose: list saved modeling report sections whose headings match a case-insensitive text query
- Stable result shape: `list[ModelingReportSectionMatch]`
- Stable item fields:
  - `output_name: str`
  - `output_path: str`
  - `heading: str`
  - `level: int`
  - `snippet: str`
- Stable behavior:
  - `query` must be a non-empty string
  - `snippet` is intentionally bounded and does not guarantee the full section

#### `search_latest_modeling_report_sections(query: str)`

- Stable name: `search_latest_modeling_report_sections`
- Implementation note: the Python function is named `search_latest_modeling_report_sections_tool`
- Purpose: list section-heading matches from the most recently modified saved modeling report
- Stable result shape: `list[ModelingReportSectionMatch]`
- Stable item fields:
  - `output_name: str`
  - `output_path: str`
  - `heading: str`
  - `level: int`
  - `snippet: str`
- Stable behavior:
  - `query` must be a non-empty string
  - fails clearly when no saved modeling reports exist
  - `snippet` is intentionally bounded and does not guarantee the full section

#### `summarize_modeling_report_sections()`

- Stable name: `summarize_modeling_report_sections`
- Purpose: summarize recurring section headings across saved modeling reports
- Stable result shape: `list[ModelingReportSectionSummary]`
- Stable item fields:
  - `heading: str`
  - `level: int`
  - `report_count: int`
  - `example_reports: list[str]`
- Stable behavior:
  - `example_reports` is intentionally bounded and does not list every matching report

#### `list_recent_modeling_reports(limit: int = 5)`

- Stable name: `list_recent_modeling_reports`
- Implementation note: the Python function is named `list_recent_modeling_reports_tool`
- Purpose: list the most recently modified markdown modeling reports in the local `reports/` directory
- Stable result shape: `list[StoredModelingReport]`
- Stable item fields:
  - `output_name: str`
  - `output_path: str`
  - `size_bytes: int`
  - `created_at: str`
  - `modified_at: str`
  - `content_sha256: str | None`
- Stable behavior:
  - `limit` must be greater than 0

#### `summarize_modeling_report_catalog(limit: int = 5)`

- Stable name: `summarize_modeling_report_catalog`
- Implementation note: the Python function is named `summarize_modeling_report_catalog_tool`
- Purpose: summarize the local markdown modeling report catalog with counts, storage size, and recent entries
- Stable result fields:
  - `report_count: int`
  - `total_size_bytes: int`
  - `most_recent_reports: list[StoredModelingReport]`
- Stable behavior:
  - `limit` must be greater than 0

#### `read_modeling_report(output_name: str)`

- Stable name: `read_modeling_report`
- Purpose: load one markdown modeling report saved in the local `reports/` directory
- Stable result fields:
  - `output_name: str`
  - `output_path: str`
  - `markdown: str`
- Stable behavior:
  - `output_name` must be a single markdown file name inside `reports/`
  - traversal-style paths are rejected

#### `list_modeling_report_sections(output_name: str)`

- Stable name: `list_modeling_report_sections`
- Purpose: list markdown headings discovered inside one saved modeling report
- Stable result shape: `list[ModelingReportSection]`
- Stable item fields:
  - `heading: str`
  - `level: int`
- Stable behavior:
  - `output_name` must be a single markdown file name inside `reports/`
  - traversal-style paths are rejected

#### `list_latest_modeling_report_sections()`

- Stable name: `list_latest_modeling_report_sections`
- Implementation note: the Python function is named `list_latest_modeling_report_sections_tool`
- Purpose: list markdown headings discovered inside the most recently modified saved modeling report
- Stable result shape: `list[ModelingReportSection]`
- Stable item fields:
  - `heading: str`
  - `level: int`
- Stable behavior:
  - fails clearly when no saved modeling reports exist

#### `read_modeling_report_section(output_name: str, section_heading: str)`

- Stable name: `read_modeling_report_section`
- Purpose: load one markdown section from a saved modeling report
- Stable result fields:
  - `output_name: str`
  - `output_path: str`
  - `heading: str`
  - `level: int`
  - `markdown: str`
- Stable behavior:
  - `output_name` must be a single markdown file name inside `reports/`
  - `section_heading` must be a non-empty string
  - traversal-style paths are rejected
  - fails clearly when the requested section is not present

#### `read_latest_modeling_report_section(section_heading: str)`

- Stable name: `read_latest_modeling_report_section`
- Implementation note: the Python function is named `read_latest_modeling_report_section_tool`
- Purpose: load one markdown section from the most recently modified saved modeling report
- Stable result fields:
  - `output_name: str`
  - `output_path: str`
  - `heading: str`
  - `level: int`
  - `markdown: str`
- Stable behavior:
  - `section_heading` must be a non-empty string
  - fails clearly when no saved modeling reports exist
  - fails clearly when the requested section is not present

#### `save_modeling_report_section(output_name: str, section_heading: str, new_output_name: str | None = None, overwrite: bool = False)`

- Stable name: `save_modeling_report_section`
- Implementation note: the Python function is named `save_modeling_report_section_tool`
- Purpose: save one markdown section from a saved modeling report as a new markdown artifact inside `reports/`
- Stable result fields:
  - `source_output_name: str`
  - `section_heading: str`
  - `output_path: str`
- Stable behavior:
  - `output_name` must be a single markdown file name inside `reports/`
  - `section_heading` must be a non-empty string
  - `new_output_name`, when provided, must be a single markdown file name inside `reports/`
  - fails clearly when the requested section is not present
  - existing reports are not overwritten unless `overwrite` is explicitly true

#### `save_latest_modeling_report_section(section_heading: str, new_output_name: str | None = None, overwrite: bool = False)`

- Stable name: `save_latest_modeling_report_section`
- Implementation note: the Python function is named `save_latest_modeling_report_section_tool`
- Purpose: save one markdown section from the most recently modified saved modeling report as a new markdown artifact inside `reports/`
- Stable result fields:
  - `source_output_name: str`
  - `section_heading: str`
  - `output_path: str`
- Stable behavior:
  - `section_heading` must be a non-empty string
  - `new_output_name`, when provided, must be a single markdown file name inside `reports/`
  - fails clearly when no saved modeling reports exist
  - fails clearly when the requested section is not present
  - existing reports are not overwritten unless `overwrite` is explicitly true

#### `compare_modeling_report_sections(output_name: str, other_output_name: str, section_heading: str)`

- Stable name: `compare_modeling_report_sections`
- Purpose: return a bounded diff summary between matching sections in two saved modeling reports
- Stable result fields:
  - `output_name: str`
  - `other_output_name: str`
  - `section_heading: str`
  - `changed: bool`
  - `added_line_count: int`
  - `removed_line_count: int`
  - `diff_preview: str`
- Stable behavior:
  - `output_name` and `other_output_name` must be single markdown file names inside `reports/`
  - `section_heading` must be a non-empty string
  - fails clearly when the requested section is not present in either report
  - `diff_preview` is intentionally bounded and does not guarantee a full diff

#### `compare_latest_modeling_report_sections(section_heading: str)`

- Stable name: `compare_latest_modeling_report_sections`
- Implementation note: the Python function is named `compare_latest_modeling_report_sections_tool`
- Purpose: return a bounded diff summary for one section across the two most recently modified saved modeling reports
- Stable result fields:
  - `output_name: str`
  - `other_output_name: str`
  - `section_heading: str`
  - `changed: bool`
  - `added_line_count: int`
  - `removed_line_count: int`
  - `diff_preview: str`
- Stable behavior:
  - `section_heading` must be a non-empty string
  - fails clearly when fewer than two saved modeling reports exist
  - fails clearly when the requested section is not present in either report
  - `diff_preview` is intentionally bounded and does not guarantee a full diff

#### `read_latest_modeling_report()`

- Stable name: `read_latest_modeling_report`
- Implementation note: the Python function is named `read_latest_modeling_report_tool`
- Purpose: load the most recently modified markdown modeling report saved in the local `reports/` directory
- Stable result fields:
  - `output_name: str`
  - `output_path: str`
  - `markdown: str`
- Stable behavior:
  - fails clearly when no saved modeling reports exist

#### `delete_modeling_report(output_name: str)`

- Stable name: `delete_modeling_report`
- Purpose: remove one markdown modeling report saved in the local `reports/` directory
- Stable result fields:
  - `output_name: str`
  - `output_path: str`
- Stable behavior:
  - `output_name` must be a single markdown file name inside `reports/`
  - traversal-style paths are rejected

#### `rename_modeling_report(output_name: str, new_output_name: str, overwrite: bool = False)`

- Stable name: `rename_modeling_report`
- Purpose: rename one markdown modeling report saved in the local `reports/` directory
- Stable result fields:
  - `old_output_name: str`
  - `new_output_name: str`
  - `old_output_path: str`
  - `new_output_path: str`
- Stable behavior:
  - `output_name` and `new_output_name` must be single markdown file names inside `reports/`
  - traversal-style paths are rejected
  - existing reports are not overwritten unless `overwrite` is explicitly true

#### `rename_latest_modeling_report(new_output_name: str, overwrite: bool = False)`

- Stable name: `rename_latest_modeling_report`
- Implementation note: the Python function is named `rename_latest_modeling_report_tool`
- Purpose: rename the most recently modified markdown modeling report saved in the local `reports/` directory
- Stable result fields:
  - `old_output_name: str`
  - `new_output_name: str`
  - `old_output_path: str`
  - `new_output_path: str`
- Stable behavior:
  - `new_output_name` must be a single markdown file name inside `reports/`
  - fails clearly when no saved modeling reports exist
  - existing reports are not overwritten unless `overwrite` is explicitly true

#### `copy_modeling_report(output_name: str, new_output_name: str, overwrite: bool = False)`

- Stable name: `copy_modeling_report`
- Purpose: copy one markdown modeling report saved in the local `reports/` directory
- Stable result fields:
  - `source_output_name: str`
  - `new_output_name: str`
  - `source_output_path: str`
  - `new_output_path: str`
- Stable behavior:
  - `output_name` and `new_output_name` must be single markdown file names inside `reports/`
  - existing reports are not overwritten unless `overwrite` is explicitly true
  - traversal-style paths are rejected

#### `inspect_modeling_report(output_name: str)`

- Stable name: `inspect_modeling_report`
- Purpose: inspect metadata for one markdown modeling report saved in the local `reports/` directory
- Stable result fields:
  - `output_name: str`
  - `output_path: str`
  - `size_bytes: int`
  - `created_at: str`
  - `metadata_changed_at: str`
  - `modified_at: str`
  - `content_sha256: str`
- Stable behavior:
  - `output_name` must be a single markdown file name inside `reports/`
  - traversal-style paths are rejected

#### `inspect_latest_modeling_report()`

- Stable name: `inspect_latest_modeling_report`
- Implementation note: the Python function is named `inspect_latest_modeling_report_tool`
- Purpose: inspect metadata for the most recently modified markdown modeling report saved in the local `reports/` directory
- Stable result fields:
  - `output_name: str`
  - `output_path: str`
  - `size_bytes: int`
  - `created_at: str`
  - `metadata_changed_at: str`
  - `modified_at: str`
  - `content_sha256: str`
- Stable behavior:
  - fails clearly when no saved modeling reports exist

#### `copy_latest_modeling_report(new_output_name: str, overwrite: bool = False)`

- Stable name: `copy_latest_modeling_report`
- Implementation note: the Python function is named `copy_latest_modeling_report_tool`
- Purpose: copy the most recently modified markdown modeling report saved in the local `reports/` directory
- Stable result fields:
  - `source_output_name: str`
  - `new_output_name: str`
  - `source_output_path: str`
  - `new_output_path: str`
- Stable behavior:
  - `new_output_name` must be a single markdown file name inside `reports/`
  - fails clearly when no saved modeling reports exist
  - existing reports are not overwritten unless `overwrite` is explicitly true

#### `preview_modeling_report(output_name: str)`

- Stable name: `preview_modeling_report`
- Purpose: return a bounded preview of one markdown modeling report saved in the local `reports/` directory
- Stable result fields:
  - `output_name: str`
  - `output_path: str`
  - `headline: str`
  - `preview_markdown: str`
  - `line_count: int`
- Stable behavior:
  - `output_name` must be a single markdown file name inside `reports/`
  - traversal-style paths are rejected
  - `preview_markdown` is intentionally bounded and does not contain the full report

#### `compare_modeling_reports(output_name: str, other_output_name: str)`

- Stable name: `compare_modeling_reports`
- Purpose: return a bounded unified diff summary between two markdown modeling reports saved in the local `reports/` directory
- Stable result fields:
  - `output_name: str`
  - `other_output_name: str`
  - `changed: bool`
  - `added_line_count: int`
  - `removed_line_count: int`
  - `diff_preview: str`
- Stable behavior:
  - `output_name` and `other_output_name` must be single markdown file names inside `reports/`
  - traversal-style paths are rejected
  - `diff_preview` is intentionally bounded and does not guarantee a full diff

#### `compare_latest_modeling_reports()`

- Stable name: `compare_latest_modeling_reports`
- Implementation note: the Python function is named `compare_latest_modeling_reports_tool`
- Purpose: return a bounded unified diff summary between the two most recently modified markdown modeling reports saved in the local `reports/` directory
- Stable result fields:
  - `output_name: str`
  - `other_output_name: str`
  - `changed: bool`
  - `added_line_count: int`
  - `removed_line_count: int`
  - `diff_preview: str`
- Stable behavior:
  - fails clearly when fewer than two saved modeling reports exist
  - `diff_preview` is intentionally bounded and does not guarantee a full diff

#### `preview_latest_modeling_report()`

- Stable name: `preview_latest_modeling_report`
- Implementation note: the Python function is named `preview_latest_modeling_report_tool`
- Purpose: return a bounded preview of the most recently modified markdown modeling report saved in the local `reports/` directory
- Stable result fields:
  - `output_name: str`
  - `output_path: str`
  - `headline: str`
  - `preview_markdown: str`
  - `line_count: int`
- Stable behavior:
  - fails clearly when no saved modeling reports exist
  - `preview_markdown` is intentionally bounded and does not contain the full report

#### `preview_csv(file_name: str, rows: int = 5)`

- Stable name: `preview_csv`
- Purpose: preview the first rows of a CSV file inside `MCP_DATA_ROOT`
- Stable result fields:
  - `file_name: str`
  - `columns: list[str]`
  - `rows: list[dict[str, object | null]]`
  - `row_count: int`
- Stable behavior:
  - `rows` is bounded by the validated `rows` argument and runtime limits
  - scalar values are returned in JSON-friendly form

#### `profile_csv(file_name: str)`

- Stable name: `profile_csv`
- Purpose: return a bounded structural profile for one CSV dataset
- Stable result fields:
  - `file_name: str`
  - `row_count: int`
  - `column_count: int`
  - `columns: list[str]`
  - `dtypes: dict[str, str]`
  - `missing_values: dict[str, int]`
  - `missing_percentage: dict[str, float]`
  - `numeric_columns: list[NumericColumnProfile]`
  - `categorical_columns: list[CategoricalColumnProfile]`
  - `boolean_columns: list[BooleanColumnProfile]`
  - `datetime_columns: list[DatetimeColumnProfile]`
  - `data_quality: DatasetQualityDiagnostics`
  - `profiling_limits.max_categorical_values: int`
  - `profiling_limits.max_histogram_bins: int`
  - `profiling_limits.max_candidate_key_columns: int`
  - `profiling_limits.max_candidate_key_combinations: int`
- Stable profile item fields:
  - `NumericColumnProfile`: `column`, `count`, `mean`, `std`, `min`, `q25`, `median`, `q75`, `max`, `iqr`, `robust_spread`, `histogram`, `iqr_outlier_count`, `z_score_outlier_count`, `skewness`, `quality_signals`
  - `NumericHistogramBin`: `lower_bound`, `upper_bound`, `count`
  - `CategoricalColumnProfile`: `column`, `count`, `unique_count`, `top_value`, `top_value_frequency`, `top_values`, `rare_category_count`, `rare_category_mass`, `entropy`, `normalized_entropy`, `quality_signals`
  - `ValueFrequency`: `value`, `count`
  - `BooleanColumnProfile`: `column`, `true_count`, `false_count`, `missing_count`
  - `DatetimeColumnProfile`: `column`, `count`, `min`, `max`
  - `ProfileHeuristicSignal`: `signal`, `reason`, `severity`, `confidence`
  - `ColumnQualitySignal`: `column`, `signal`, `reason`, `severity`, `confidence`
  - `DatasetQualityDiagnostics`: `duplicate_row_count`, `duplicate_row_percentage`, `candidate_keys`, `empty_columns`, `one_value_columns`, `probable_free_text_columns`, `possible_identifier_columns`
  - `CandidateKeyProfile`: `columns`, `uniqueness_ratio`, `missing_count`, `reason`, `confidence`
- Heuristic notes:
  - categorical top values are intentionally bounded
  - numeric histograms are intentionally capped and should not be interpreted as exact density estimates
  - candidate key combinations are searched only within documented column and combination caps
  - quality signals are advisory and always include reason plus confidence/severity metadata
  - datetime detection is conservative and may leave ambiguous text columns in categorical output

#### `detect_csv_issues(file_name: str)`

- Stable name: `detect_csv_issues`
- Purpose: return simple data-quality issues for a CSV dataset
- Stable result shape: `list[DatasetIssue]`
- Stable item fields:
  - `column: str`
  - `issue_type: str`
  - `description: str`
- Heuristic notes:
  - issue detection is intentionally conservative
  - warnings are review signals, not proof of unusable data

#### `query_csv_with_duckdb(file_name: str, sql: str, limit: int | None = None)`

- Stable name: `query_csv_with_duckdb`
- Purpose: run one bounded read-only DuckDB query against the temporary table `dataset`
- Stable result fields:
  - `file_name: str`
  - `columns: list[str]`
  - `rows: list[dict[str, object | null]]`
  - `row_count: int`
  - `limit_applied: int`
- Stable behavior:
  - only a single `SELECT` or `WITH` statement is accepted
  - queries must reference the table name `dataset`
  - external file-access and schema-changing SQL are rejected

#### `list_sqlite_databases()`

- Stable name: `list_sqlite_databases`
- Implementation note: the Python function is named `list_sqlite_databases_tool`, but the MCP tool name exposed to clients is `list_sqlite_databases`
- Stable result shape: `list[SQLiteDatabaseInfo]`
- Stable item fields:
  - `file_name: str`

#### `list_sqlite_tables(file_name: str)`

- Stable name: `list_sqlite_tables`
- Stable result shape: `list[str]`

#### `describe_sqlite_table(file_name: str, table_name: str)`

- Stable name: `describe_sqlite_table`
- Stable result fields:
  - `file_name: str`
  - `table_name: str`
  - `columns: list[SQLiteColumnInfo]`
- Stable column fields:
  - `cid: int`
  - `name: str`
  - `data_type: str`
  - `not_null: bool`
  - `default_value: str | null`
  - `is_primary_key: bool`

#### `query_sqlite(file_name: str, sql: str, limit: int | None = None)`

- Stable name: `query_sqlite`
- Stable result fields:
  - `file_name: str`
  - `columns: list[str]`
  - `rows: list[dict[str, object | null]]`
  - `row_count: int`
  - `limit_applied: int`
- Stable behavior:
  - only a single `SELECT` or `WITH` statement is accepted
  - database access is read-only
  - schema-changing SQL is rejected

#### `summarize_correlations(file_name: str, method: str = "pearson")`

- Stable name: `summarize_correlations`
- Supported `method` values:
  - `pearson`
  - `spearman`
  - `kendall`
- Stable result fields:
  - `file_name: str`
  - `method: str`
  - `numeric_columns: list[str]`
  - `top_correlations: list[CorrelationPair]`
- Stable pair fields:
  - `left_column: str`
  - `right_column: str`
  - `correlation: float`
  - `absolute_correlation: float`
- Heuristic notes:
  - results are capped to the top ranked pairs
  - the ranking is descriptive only and does not imply causality

#### `detect_possible_target_leakage(file_name: str, target_column: str)`

- Stable name: `detect_possible_target_leakage`
- Stable result fields:
  - `file_name: str`
  - `target_column: str`
  - `warnings: list[LeakageWarning]`
- Stable warning fields:
  - `column: str`
  - `warning_type: str`
  - `description: str`
  - `severity: str`
  - `confidence: float`
- Heuristic notes:
  - warnings such as `suspicious_name_overlap`, `likely_identifier`, `very_high_correlation`, `exact_target_duplicate`, and `temporal_review` are review signals with severity and confidence
  - high correlation and target-name overlap alone are evidence, not proof of leakage
  - warning descriptions may evolve without changing the contract
  - absence of warnings is not proof that leakage is impossible

#### `validate_time_series_dataset(file_name: str, time_column: str, target_column: str | None = None, group_column: str | None = None)`

- Stable MCP name: `validate_time_series_dataset`
- Implementation note: the Python function is named `validate_time_series_dataset_tool`
- Stable result fields:
  - `file_name: str`
  - `time_column: str`
  - `target_column: str | null`
  - `group_column: str | null`
  - `row_count: int`
  - `parsed_timestamp_count: int`
  - `duplicate_timestamps: int`
  - `is_sorted: bool`
  - `inferred_frequency: str | null`
  - `missing_intervals: int`
  - `frequency: FrequencyInferenceResult`
  - `missing_target_values: int | null`
  - `group_summaries: list[GroupTimeSeriesSummary]`
  - `warnings: list[TimeSeriesWarning]`
- Stable group summary fields:
  - `group: str`
  - `row_count: int`
  - `duplicate_timestamps: int`
  - `missing_intervals: int`
  - `inferred_frequency: str | null`
  - `frequency: FrequencyInferenceResult`
- Stable frequency inference fields:
  - `frequency: str | null`
  - `frequency_kind: str`
  - `confidence: float`
  - `support_ratio: float`
  - `candidate_interval: str | null`
  - `is_regular: bool`
  - `is_irregular: bool`
  - `missing_interval_count: int`
- Stable warning fields:
  - `warning_type: str`
  - `description: str`
  - `group: str | null`
- Heuristic notes:
  - `frequency_kind` distinguishes `regular`, `approximately_regular`, `irregular`, `insufficient_data`, and grouped `heterogeneous` outcomes
  - missing intervals are counted only for regular or approximately regular fixed-interval series
  - grouped validation infers frequency per group and does not force one global frequency when groups disagree
  - history sufficiency warnings are baseline-readiness guidance, not modeling guarantees

#### `evaluate_forecast_baselines(file_name: str, time_column: str, target_column: str, group_column: str | None = None, forecast_horizon: int = 1, test_size: float = 0.2, seasonal_period: int | None = None)`

- Stable name: `evaluate_forecast_baselines`
- Purpose: evaluate transparent forecasting baselines with chronological rolling-origin backtesting
- Stable result fields:
  - `file_name: str`
  - `time_column: str`
  - `target_column: str`
  - `group_column: str | null`
  - `frequency: FrequencyInferenceResult`
  - `forecast_horizon: int`
  - `test_size: float`
  - `seasonal_period: int | null`
  - `evaluated_points: int`
  - `baselines: list[ForecastBaselineResult]`
  - `group_results: list[GroupForecastBaselineResult]`
  - `warnings: list[str]`
  - `metric_notes: ForecastMetricNotes`
- Stable baseline result fields:
  - `baseline_name: str`
  - `baseline_definition: str`
  - `forecast_horizon: int`
  - `seasonal_period: int | null`
  - `training_start: str`
  - `training_end: str`
  - `test_start: str`
  - `test_end: str`
  - `evaluated_points: int`
  - `metrics: ForecastBaselineMetrics`
- Stable metric fields:
  - `mae: float`
  - `rmse: float`
  - `mase: float | null`
  - `smape: float`
- Stable group result fields:
  - `group: str`
  - `row_count: int`
  - `frequency: FrequencyInferenceResult`
  - `baselines: list[ForecastBaselineResult]`
- Stable metric note fields:
  - `mae: str`
  - `rmse: str`
  - `mase: str`
  - `smape: str`
- Heuristic and mathematical notes:
  - only regular inferred frequencies are scored initially; irregular series fail clearly
  - grouped evaluation is bounded to a fixed maximum number of groups
  - last-value naive predicts from the most recent value available at the rolling origin
  - seasonal naive runs only when the explicit or inferred seasonal period is valid for the horizon and training history
  - drift extends a straight line from the first observed value to each rolling origin
  - MASE uses the relevant training-difference denominator and returns null when it is zero or unavailable
  - sMAPE uses `200*abs(actual-prediction)/(abs(actual)+abs(prediction))`; terms where actual and prediction are both zero contribute `0`

#### `evaluate_baseline_model(file_name: str, target_column: str, task_type: str, test_size: float = 0.2, random_state: int = 42, validation_strategy: str | None = None, time_column: str | None = None, group_column: str | None = None, shuffle: bool | None = None)`

- Stable name: `evaluate_baseline_model`
- Supported `task_type` values:
  - `regression`
  - `binary_classification`
  - `multiclass_classification`
- Stable result fields:
  - `file_name: str`
  - `target_column: str`
  - `task_type: str`
  - `train_rows: int`
  - `test_rows: int`
  - `regression_metrics: RegressionMetrics | null`
  - `classification_metrics: ClassificationMetrics | null`
  - `class_counts: dict[str, int] | null`
  - `train_class_counts: dict[str, int] | null`
  - `test_class_counts: dict[str, int] | null`
  - `validation: ValidationSplitMetadata`
- Supported `validation_strategy` values:
  - `random`
  - `stratified`
  - `chronological`
  - `grouped`
- Stable validation metadata fields:
  - `strategy: str`
  - `test_size: float`
  - `random_state: int | null`
  - `shuffle: bool`
  - `stratified: bool`
  - `time_column: str | null`
  - `group_column: str | null`
  - `train_start_time: str | null`
  - `train_end_time: str | null`
  - `test_start_time: str | null`
  - `test_end_time: str | null`
  - `train_group_count: int | null`
  - `test_group_count: int | null`
  - `group_overlap: bool | null`
- Stable regression metric fields:
  - `mae: float`
  - `rmse: float`
  - `r2: float`
- Stable classification metric fields:
  - `accuracy: float`
  - `balanced_accuracy: float`
  - `macro_f1: float`
  - `weighted_f1: float`
- Heuristic notes:
  - this tool uses dummy baselines only
  - classification defaults to stratified validation when class support and split size make it feasible
  - classification validates class count, minimum class support, split size, and train/test representation before returning metrics
  - chronological validation requires `time_column`, sorts stably, never shuffles, and holds out the newest observations
  - grouped validation requires `group_column` and reports whether group membership overlaps across train and test
  - metric values are comparison baselines, not target production quality thresholds

### Prompts

#### `dataset_analysis_prompt(file_name: str, objective: str = "exploratory analysis")`

- Stable name: `dataset_analysis_prompt`
- Stable return type: text prompt
- Stable behavior:
  - references the requested `file_name`
  - includes the requested `objective`
  - instructs the client to inspect schema, missingness, suspicious columns, target ideas, baseline approaches, and validation concerns
- Contract note:
  - exact prose may change across patch and minor releases
  - the prompt remains a reusable analysis scaffold, not a machine-parseable schema

#### `modeling_report_review_prompt(output_name: str = "latest", focus: str = "model critique and next steps")`

- Stable name: `modeling_report_review_prompt`
- Stable return type: text prompt
- Stable behavior:
  - references the requested `output_name`
  - supports `output_name="latest"` to target the most recently modified saved modeling report
  - includes the requested `focus`
  - instructs the client to inspect metadata, read the report, review section-level details, and recommend concrete next actions
- Contract note:
  - exact prose may change across patch and minor releases
  - the prompt remains a reusable report-review scaffold, not a machine-parseable schema

## CLI Contract

The `ds-workspace-mcp` console script is public.

### Commands

- `ds-workspace-mcp`
  - default behavior: equivalent to `ds-workspace-mcp serve`
- `ds-workspace-mcp serve`
  - starts the MCP server using configured transport settings
- `ds-workspace-mcp list-datasets`
  - prints CSV file names, one per line
- `ds-workspace-mcp profile-dataset <file_name>`
  - prints the `profile_csv` result as JSON
- `ds-workspace-mcp compare-datasets <left_file_name> <right_file_name>`
  - prints the `compare_datasets` result as JSON
- `ds-workspace-mcp plan-modeling <file_name> [--target-column]`
  - prints the `build_experiment_plan` result as JSON
- `ds-workspace-mcp report-modeling <file_name> [--target-column]`
  - prints the `build_modeling_report` markdown output
- `ds-workspace-mcp save-modeling-report <file_name> [--target-column] [--output-name]`
  - writes the `save_modeling_report` artifact and prints the saved path
- `ds-workspace-mcp list-modeling-reports`
  - prints saved modeling report file names, one per line
- `ds-workspace-mcp search-modeling-reports <query>`
  - prints matching saved modeling report file names, one per line
- `ds-workspace-mcp search-modeling-report-content <query>`
  - prints bounded saved modeling report content matches as JSON
- `ds-workspace-mcp search-latest-modeling-report-content <query>`
  - prints bounded content matches from the most recently modified saved modeling report as JSON
- `ds-workspace-mcp search-modeling-report-sections <query>`
  - prints bounded saved modeling report section matches as JSON
- `ds-workspace-mcp search-latest-modeling-report-sections <query>`
  - prints bounded section-heading matches from the most recently modified saved modeling report as JSON
- `ds-workspace-mcp summarize-modeling-report-sections`
  - prints a compact summary of recurring saved modeling report section headings as JSON
- `ds-workspace-mcp list-recent-modeling-reports [--limit]`
  - prints the most recently modified saved modeling report file names, one per line
- `ds-workspace-mcp summarize-modeling-reports [--limit]`
  - prints a compact summary of saved modeling reports as JSON
- `ds-workspace-mcp read-modeling-report <output_name>`
  - prints one saved modeling report as markdown
- `ds-workspace-mcp list-modeling-report-sections <output_name>`
  - prints markdown section headings from one saved modeling report as JSON
- `ds-workspace-mcp list-latest-modeling-report-sections`
  - prints markdown section headings from the most recently modified saved modeling report as JSON
- `ds-workspace-mcp read-modeling-report-section <output_name> <section_heading>`
  - prints one markdown section from a saved modeling report as JSON
- `ds-workspace-mcp read-latest-modeling-report-section <section_heading>`
  - prints one markdown section from the most recently modified saved modeling report as JSON
- `ds-workspace-mcp save-modeling-report-section <output_name> <section_heading> [--output-name]`
  - saves one markdown section from a saved modeling report and prints the saved path
- `ds-workspace-mcp save-latest-modeling-report-section <section_heading> [--output-name]`
  - saves one markdown section from the most recently modified saved modeling report and prints the saved path
- `ds-workspace-mcp compare-modeling-report-sections <output_name> <other_output_name> <section_heading>`
  - prints a bounded diff summary between matching report sections as JSON
- `ds-workspace-mcp compare-latest-modeling-report-sections <section_heading>`
  - prints a bounded diff summary for one section across the two most recently modified reports as JSON
- `ds-workspace-mcp read-latest-modeling-report`
  - prints the most recently modified saved modeling report as markdown
- `ds-workspace-mcp delete-modeling-report <output_name>`
  - deletes one saved modeling report and prints the deleted path
- `ds-workspace-mcp rename-modeling-report <output_name> <new_output_name>`
  - renames one saved modeling report and prints the new path
- `ds-workspace-mcp rename-latest-modeling-report <new_output_name>`
  - renames the most recently modified saved modeling report and prints the new path
- `ds-workspace-mcp copy-modeling-report <output_name> <new_output_name>`
  - copies one saved modeling report and prints the new path
- `ds-workspace-mcp copy-latest-modeling-report <new_output_name>`
  - copies the most recently modified saved modeling report and prints the new path
- `ds-workspace-mcp inspect-modeling-report <output_name>`
  - prints metadata for one saved modeling report as JSON
- `ds-workspace-mcp inspect-latest-modeling-report`
  - prints metadata for the most recently modified saved modeling report as JSON
- `ds-workspace-mcp preview-modeling-report <output_name>`
  - prints a bounded preview of one saved modeling report as JSON
- `ds-workspace-mcp compare-modeling-reports <output_name> <other_output_name>`
  - prints a bounded diff summary between two saved modeling reports as JSON
- `ds-workspace-mcp compare-latest-modeling-reports`
  - prints a bounded diff summary between the two most recently modified saved modeling reports as JSON
- `ds-workspace-mcp preview-latest-modeling-report`
  - prints a bounded preview of the most recently modified saved modeling report as JSON
- `ds-workspace-mcp evaluate-forecast-baselines <file_name> --time-column <column> --target-column <column> [--group-column] [--forecast-horizon] [--test-size] [--seasonal-period]`
  - prints the `evaluate_forecast_baselines` result as JSON
- `ds-workspace-mcp generate-sample-healthcare-data [--output] [--start-date] [--days] [--clinics] [--seed]`
  - writes a synthetic healthcare CSV and prints the output path

## Environment Variable Contract

These runtime settings are public and documented:

- `MCP_DATA_ROOT`
- `MCP_REPORTS_ROOT`
- `MCP_TRANSPORT`
- `MCP_HOST`
- `MCP_PORT`
- `MCP_MAX_PREVIEW_ROWS`
- `MCP_MAX_SQL_ROWS`
- `MCP_MAX_SQL_QUERY_LENGTH`
- `MCP_SQL_TIMEOUT_MS`
- `MCP_MAX_CATEGORICAL_VALUES`
- `MCP_MAX_DATASET_BYTES`
- `MCP_PROFILE_CACHE_ENABLED`
- `MCP_PROFILE_CACHE_MAX_ENTRIES`
- `MCP_LOG_LEVEL`
- `MCP_API_KEY`
- `MCP_TRACING_ENABLED`
- `MCP_TRACING_SERVICE_NAME`
- `MCP_TRACING_CONSOLE_EXPORTER`

Stable expectations:

- blank `MCP_API_KEY` disables HTTP bearer-token auth
- `MCP_TRANSPORT` supports `stdio` and `streamable-http`
- validation bounds on numeric settings may reject invalid values but will not silently reinterpret them
- CSV reads are rejected when the file exceeds `MCP_MAX_DATASET_BYTES`
- SQL query text is rejected when it exceeds `MCP_MAX_SQL_QUERY_LENGTH`
- SQL queries are interrupted when they exceed `MCP_SQL_TIMEOUT_MS`

## Error Contract

User-facing failures may surface through these stable exception categories:

- `InvalidDatasetNameError`
- `UnsupportedFileTypeError`
- `PathTraversalError`
- `DatasetNotFoundError`
- `DatasetTooLargeError`
- `DatasetReadError`
- `QueryTimeoutError`
- `InvalidSQLError`
- `ProfilingError`
- `InsufficientDataError`

Exact wording may change. Error category meaning is stable.

## Out of Scope

The following are not part of the versioned public contract:

- internal module layout
- helper function names not exposed through MCP or CLI
- log record structure and message wording
- trace span names and attributes
- exact ordering of heuristic warnings unless explicitly documented above
