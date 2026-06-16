from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from ds_workspace_mcp.core import list_csv_files, profile_csv_dataset
from ds_workspace_mcp.experiment_plan import build_experiment_plan_dataset
from ds_workspace_mcp.modeling_report import build_modeling_report_dataset
from ds_workspace_mcp.report_export import save_modeling_report_dataset
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
        saved_report = save_modeling_report_dataset(
            file_name=args.file_name,
            target_column=args.target_column,
            output_name=args.output_name,
        )
        print(saved_report.output_path)
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
