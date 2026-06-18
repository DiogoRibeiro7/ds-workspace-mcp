from __future__ import annotations

from ds_workspace_mcp.server import dataset_analysis_prompt, modeling_report_review_prompt


def test_dataset_analysis_prompt_includes_file_name_and_objective() -> None:
    prompt = dataset_analysis_prompt(
        file_name="sample_clinic_usage.csv",
        objective="forecast clinic usage and staffing demand",
    )

    assert "sample_clinic_usage.csv" in prompt
    assert "forecast clinic usage and staffing demand" in prompt
    assert "1. Inspecting the dataset schema." in prompt
    assert "5. Explaining risks, assumptions, and validation strategy." in prompt


def test_modeling_report_review_prompt_latest_uses_latest_tools() -> None:
    prompt = modeling_report_review_prompt()

    assert "most recently modified saved modeling report" in prompt
    assert "inspect_latest_modeling_report" in prompt
    assert "read_latest_modeling_report" in prompt
    assert "list_latest_modeling_report_sections" in prompt
    assert "model critique and next steps" in prompt


def test_modeling_report_review_prompt_named_report_uses_named_tools() -> None:
    prompt = modeling_report_review_prompt(
        output_name="clinic-usage-report.md",
        focus="decide whether the report is ready for stakeholder review",
    )

    assert "saved modeling report `clinic-usage-report.md`" in prompt
    assert "inspect_modeling_report" in prompt
    assert "read_modeling_report" in prompt
    assert "compare_modeling_report_sections" in prompt
    assert "decide whether the report is ready for stakeholder review" in prompt
