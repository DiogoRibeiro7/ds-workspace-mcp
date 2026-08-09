from __future__ import annotations

import logging

from ds_workspace_mcp.mcp.app import _mcp_prompt
from ds_workspace_mcp.tracing import traced_operation

logger = logging.getLogger(__name__)


@_mcp_prompt()
def dataset_analysis_prompt(file_name: str, objective: str = "exploratory analysis") -> str:
    """
    Create a reusable analysis prompt for a dataset.

    Args:
        file_name: Dataset file name.
        objective: Analysis objective.

    Returns:
        A prompt that an MCP-compatible assistant can use.
    """

    with traced_operation(
        "prompt.dataset_analysis_prompt",
        {
            "prompt.name": "dataset_analysis_prompt",
            "dataset.file_name": file_name,
            "prompt.objective_length": len(objective),
        },
    ):
        logger.info(
            "Prompt dataset_analysis_prompt created file_name=%s objective_length=%s",
            file_name,
            len(objective),
        )
        return f"""
You are analysing the dataset `{file_name}`.

Objective:
{objective}

Start by:
1. Inspecting the dataset schema.
2. Checking missing values and suspicious columns.
3. Suggesting useful target variables.
4. Proposing baseline statistical and machine learning approaches.
5. Explaining risks, assumptions, and validation strategy.

Keep the analysis practical and reproducible.
""".strip()


@_mcp_prompt()
def modeling_report_review_prompt(
    output_name: str = "latest",
    focus: str = "model critique and next steps",
) -> str:
    """
    Create a reusable review prompt for a saved modeling report.

    Args:
        output_name: Saved report file name inside `reports/`, or `latest`.
        focus: Review objective.

    Returns:
        A prompt that an MCP-compatible assistant can use.
    """

    with traced_operation(
        "prompt.modeling_report_review_prompt",
        {
            "prompt.name": "modeling_report_review_prompt",
            "tool.output_name": output_name,
            "prompt.focus_length": len(focus),
        },
    ):
        logger.info(
            "Prompt modeling_report_review_prompt created output_name=%s focus_length=%s",
            output_name,
            len(focus),
        )
        if output_name.strip().lower() == "latest":
            report_steps = (
                "1. Use `inspect_latest_modeling_report` to confirm freshness and metadata.\n"
                "2. Use `read_latest_modeling_report` to review the full artifact.\n"
                "3. Use `preview_latest_modeling_report` if a bounded summary helps "
                "orient the review."
            )
            section_steps = (
                "Use `list_latest_modeling_report_sections`, "
                "`read_latest_modeling_report_section`, and "
                "`compare_latest_modeling_report_sections` when section-level review is useful."
            )
            report_reference = "the most recently modified saved modeling report"
        else:
            report_steps = (
                f"1. Use `inspect_modeling_report` for `{output_name}` to confirm metadata.\n"
                f"2. Use `read_modeling_report` for `{output_name}` to review the full "
                f"artifact.\n"
                f"3. Use `preview_modeling_report` for `{output_name}` if a bounded "
                f"summary helps orient the review."
            )
            section_steps = (
                f"Use `list_modeling_report_sections`, `read_modeling_report_section`, "
                f"and `compare_modeling_report_sections` for `{output_name}` when "
                f"section-level review is useful."
            )
            report_reference = f"the saved modeling report `{output_name}`"

        return f"""
You are reviewing {report_reference}.

Focus:
{focus}

Start with:
{report_steps}

Review checklist:
1. Confirm the target variable, task framing, and whether the report still
   matches the current dataset reality.
2. Evaluate feature logic, leakage risk, validation strategy, and whether the
   baseline choices are defensible.
3. Identify weak assumptions, missing diagnostics, thin sections, or
   recommendations that are not operationally specific.
4. {section_steps}
5. Recommend concrete next experiments, documentation improvements, and
   whether the report should be copied or renamed before further edits.

Keep the review practical, specific, and reproducible.
""".strip()
