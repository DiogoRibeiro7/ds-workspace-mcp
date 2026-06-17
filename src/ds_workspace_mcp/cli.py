from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from ds_workspace_mcp.core import list_csv_files, profile_csv_dataset
from ds_workspace_mcp.experiment_plan import build_experiment_plan_dataset
from ds_workspace_mcp.modeling_report import build_modeling_report_dataset
from ds_workspace_mcp.report_export import (
    delete_saved_modeling_report,
    inspect_saved_modeling_report,
    list_recent_modeling_reports,
    list_saved_modeling_reports,
    preview_saved_modeling_report,
    read_saved_modeling_report,
    rename_saved_modeling_report,
    save_modeling_report_dataset,
    search_saved_modeling_reports,
    summarize_modeling_report_catalog,
)
from ds_workspace_mcp.server import main as serve_main
from ds_workspace_mcp.synthetic.healthcare import (
    DEFAULT_CLINICS,
    DEFAULT_DAYS,
    DEFAULT_OUTPUT_NAME,
    DEFAULT_SEED,
    DEFAULT_START_DATE,
    GeneratorConfig,
    write_healthcare_dataset,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(description="Local development CLI for ds-workspace-mcp.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("serve", help="Run the MCP server.")
    subparsers.add_parser("list-datasets", help="List CSV datasets from the configured data root.")

    profile_parser = subparsers.add_parser(
        "profile-dataset",
        help="Profile a CSV dataset and print the result as JSON.",
    )
    profile_parser.add_argument("file_name", help="CSV dataset file name.")

    plan_parser = subparsers.add_parser(
        "plan-modeling",
        help="Build a first-pass modeling experiment plan and print the result as JSON.",
    )
    plan_parser.add_argument("file_name", help="CSV dataset file name.")
    plan_parser.add_argument(
        "--target-column",
        help="Optional target column override.",
    )

    report_parser = subparsers.add_parser(
        "report-modeling",
        help="Build a markdown modeling report for a dataset.",
    )
    report_parser.add_argument("file_name", help="CSV dataset file name.")
    report_parser.add_argument(
        "--target-column",
        help="Optional target column override.",
    )

    save_report_parser = subparsers.add_parser(
        "save-modeling-report",
        help="Save a markdown modeling report into the local reports directory.",
    )
    save_report_parser.add_argument("file_name", help="CSV dataset file name.")
    save_report_parser.add_argument(
        "--target-column",
        help="Optional target column override.",
    )
    save_report_parser.add_argument(
        "--output-name",
        help="Optional markdown file name inside reports/.",
    )

    subparsers.add_parser(
        "list-modeling-reports",
        help="List markdown modeling reports saved inside the local reports directory.",
    )

    search_report_parser = subparsers.add_parser(
        "search-modeling-reports",
        help="Search saved markdown modeling reports by file name substring.",
    )
    search_report_parser.add_argument("query", help="Case-insensitive substring to match.")

    recent_report_parser = subparsers.add_parser(
        "list-recent-modeling-reports",
        help="List the most recently modified saved modeling reports.",
    )
    recent_report_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of reports to print.",
    )

    summarize_report_parser = subparsers.add_parser(
        "summarize-modeling-reports",
        help="Print a compact summary of saved modeling reports as JSON.",
    )
    summarize_report_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of recent reports to include in the summary.",
    )

    read_report_parser = subparsers.add_parser(
        "read-modeling-report",
        help="Print one saved markdown modeling report from the local reports directory.",
    )
    read_report_parser.add_argument(
        "output_name",
        help="Markdown report file name inside reports/.",
    )

    delete_report_parser = subparsers.add_parser(
        "delete-modeling-report",
        help="Delete one saved markdown modeling report from the local reports directory.",
    )
    delete_report_parser.add_argument(
        "output_name",
        help="Markdown report file name inside reports/.",
    )

    rename_report_parser = subparsers.add_parser(
        "rename-modeling-report",
        help="Rename one saved markdown modeling report inside the local reports directory.",
    )
    rename_report_parser.add_argument(
        "output_name",
        help="Current markdown report file name inside reports/.",
    )
    rename_report_parser.add_argument(
        "new_output_name",
        help="New markdown report file name inside reports/.",
    )

    inspect_report_parser = subparsers.add_parser(
        "inspect-modeling-report",
        help="Print metadata for one saved markdown modeling report.",
    )
    inspect_report_parser.add_argument(
        "output_name",
        help="Markdown report file name inside reports/.",
    )

    preview_report_parser = subparsers.add_parser(
        "preview-modeling-report",
        help="Print a bounded preview of one saved markdown modeling report.",
    )
    preview_report_parser.add_argument(
        "output_name",
        help="Markdown report file name inside reports/.",
    )

    generate_parser = subparsers.add_parser(
        "generate-sample-healthcare-data",
        help="Generate a synthetic healthcare operations CSV.",
    )
    generate_parser.add_argument(
        "--output",
        type=Path,
        default=Path("data") / DEFAULT_OUTPUT_NAME,
        help="Output CSV path.",
    )
    generate_parser.add_argument(
        "--start-date",
        default=DEFAULT_START_DATE,
        help="Start date in YYYY-MM-DD format.",
    )
    generate_parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help="Number of daily observations per clinic.",
    )
    generate_parser.add_argument(
        "--clinics",
        type=int,
        default=DEFAULT_CLINICS,
        help="Number of clinics to simulate.",
    )
    generate_parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Random seed for reproducible generation.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI command."""

    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    command = args.command or "serve"

    if command == "serve":
        serve_main()
        return 0

    if command == "list-datasets":
        for file_name in list_csv_files():
            print(file_name)
        return 0

    if command == "profile-dataset":
        profile = profile_csv_dataset(args.file_name)
        print(json.dumps(profile.model_dump(mode="json"), indent=2))
        return 0

    if command == "plan-modeling":
        plan = build_experiment_plan_dataset(
            file_name=args.file_name,
            target_column=args.target_column,
        )
        print(json.dumps(plan.model_dump(mode="json"), indent=2))
        return 0

    if command == "report-modeling":
        report = build_modeling_report_dataset(
            file_name=args.file_name,
            target_column=args.target_column,
        )
        print(report.markdown)
        return 0

    if command == "save-modeling-report":
        saved_report_result = save_modeling_report_dataset(
            file_name=args.file_name,
            target_column=args.target_column,
            output_name=args.output_name,
        )
        print(saved_report_result.output_path)
        return 0

    if command == "list-modeling-reports":
        for listed_report in list_saved_modeling_reports():
            print(listed_report.output_name)
        return 0

    if command == "search-modeling-reports":
        for matched_report in search_saved_modeling_reports(args.query):
            print(matched_report.output_name)
        return 0

    if command == "list-recent-modeling-reports":
        for recent_report in list_recent_modeling_reports(limit=args.limit):
            print(recent_report.output_name)
        return 0

    if command == "summarize-modeling-reports":
        summary = summarize_modeling_report_catalog(limit=args.limit)
        print(json.dumps(summary.model_dump(mode="json"), indent=2))
        return 0

    if command == "read-modeling-report":
        read_report = read_saved_modeling_report(args.output_name)
        print(read_report.markdown)
        return 0

    if command == "delete-modeling-report":
        deleted_report = delete_saved_modeling_report(args.output_name)
        print(deleted_report.output_path)
        return 0

    if command == "rename-modeling-report":
        renamed_report = rename_saved_modeling_report(
            output_name=args.output_name,
            new_output_name=args.new_output_name,
        )
        print(renamed_report.new_output_path)
        return 0

    if command == "inspect-modeling-report":
        metadata = inspect_saved_modeling_report(args.output_name)
        print(json.dumps(metadata.model_dump(mode="json"), indent=2))
        return 0

    if command == "preview-modeling-report":
        preview = preview_saved_modeling_report(args.output_name)
        print(json.dumps(preview.model_dump(mode="json"), indent=2))
        return 0

    if command == "generate-sample-healthcare-data":
        if args.days < 1:
            print("--days must be greater than 0.")
            return 1
        if args.clinics < 1:
            print("--clinics must be greater than 0.")
            return 1

        config = GeneratorConfig(
            output_path=args.output,
            start_date=args.start_date,
            days=args.days,
            clinics=args.clinics,
            seed=args.seed,
        )
        output_path = write_healthcare_dataset(config)
        print(output_path)
        return 0

    parser.print_help()
    return 1
