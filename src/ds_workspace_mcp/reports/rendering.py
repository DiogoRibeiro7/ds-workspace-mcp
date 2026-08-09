from __future__ import annotations

from ds_workspace_mcp.modeling_report import build_modeling_report_dataset

from .models import SavedModelingReport
from .paths import get_report_storage, resolve_report_output_path


def save_modeling_report_dataset(
    file_name: str,
    target_column: str | None = None,
    output_name: str | None = None,
    overwrite: bool = False,
) -> SavedModelingReport:
    """Build and persist a modeling report inside the local reports directory."""

    report = build_modeling_report_dataset(
        file_name=file_name,
        target_column=target_column,
    )
    output_path = resolve_report_output_path(
        file_name=file_name,
        target_column=report.target_column,
        output_name=output_name,
    )
    output_path = get_report_storage().write_text(
        output_path.name,
        report.markdown,
        overwrite=overwrite,
    )
    return SavedModelingReport(
        file_name=file_name,
        target_column=report.target_column,
        output_path=str(output_path),
        headline=report.headline,
    )
