from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from ds_workspace_mcp.core import list_csv_files, profile_csv_dataset
from ds_workspace_mcp.experiment_plan import build_experiment_plan_dataset
from ds_workspace_mcp.modeling_report import build_modeling_report_dataset
from ds_workspace_mcp.report_export import (
    compare_latest_modeling_report_sections,
    compare_latest_modeling_reports,
    compare_saved_modeling_report_sections,
    compare_saved_modeling_reports,
    delete_saved_modeling_report,
    inspect_latest_modeling_report,
    inspect_saved_modeling_report,
    list_latest_modeling_report_sections,
    list_recent_modeling_reports,
    list_saved_modeling_report_sections,
    list_saved_modeling_reports,
    preview_latest_modeling_report,
    preview_saved_modeling_report,
    read_latest_modeling_report,
    read_latest_modeling_report_section,
    read_saved_modeling_report,
    read_saved_modeling_report_section,
    rename_saved_modeling_report,
    save_latest_modeling_report_section,
    save_modeling_report_dataset,
    save_modeling_report_section,
    search_latest_modeling_report_content,
    search_latest_modeling_report_sections,
    search_saved_modeling_report_content,
    search_saved_modeling_report_sections,
    search_saved_modeling_reports,
    summarize_modeling_report_catalog,
    summarize_saved_modeling_report_sections,
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

    search_report_content_parser = subparsers.add_parser(
        "search-modeling-report-content",
        help="Search saved markdown modeling reports by content and print bounded matches as JSON.",
    )
    search_report_content_parser.add_argument(
        "query",
        help="Case-insensitive text to match inside report content.",
    )

    search_latest_report_content_parser = subparsers.add_parser(
        "search-latest-modeling-report-content",
        help=(
            "Search the newest saved markdown modeling report by content and print "
            "bounded matches as JSON."
        ),
    )
    search_latest_report_content_parser.add_argument(
        "query",
        help="Case-insensitive text to match inside the newest report content.",
    )

    search_report_sections_parser = subparsers.add_parser(
        "search-modeling-report-sections",
        help="Search saved markdown report section headings and print bounded matches as JSON.",
    )
    search_report_sections_parser.add_argument(
        "query",
        help="Case-insensitive text to match inside section headings.",
    )

    search_latest_report_sections_parser = subparsers.add_parser(
        "search-latest-modeling-report-sections",
        help=(
            "Search section headings in the newest saved modeling report and print "
            "bounded matches as JSON."
        ),
    )
    search_latest_report_sections_parser.add_argument(
        "query",
        help="Case-insensitive text to match inside newest report section headings.",
    )

    subparsers.add_parser(
        "summarize-modeling-report-sections",
        help="Print a compact summary of recurring saved report section headings as JSON.",
    )

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

    list_report_sections_parser = subparsers.add_parser(
        "list-modeling-report-sections",
        help="List markdown section headings from one saved modeling report as JSON.",
    )
    list_report_sections_parser.add_argument(
        "output_name",
        help="Markdown report file name inside reports/.",
    )

    subparsers.add_parser(
        "list-latest-modeling-report-sections",
        help="List markdown section headings from the newest saved modeling report as JSON.",
    )

    read_report_section_parser = subparsers.add_parser(
        "read-modeling-report-section",
        help="Print one markdown section from a saved modeling report as JSON.",
    )
    read_report_section_parser.add_argument(
        "output_name",
        help="Markdown report file name inside reports/.",
    )
    read_report_section_parser.add_argument(
        "section_heading",
        help="Markdown heading to extract, case-insensitively.",
    )

    read_latest_report_section_parser = subparsers.add_parser(
        "read-latest-modeling-report-section",
        help="Print one markdown section from the newest saved modeling report as JSON.",
    )
    read_latest_report_section_parser.add_argument(
        "section_heading",
        help="Markdown heading to extract from the newest report.",
    )

    save_report_section_parser = subparsers.add_parser(
        "save-modeling-report-section",
        help="Save one markdown section from a report as a new markdown artifact.",
    )
    save_report_section_parser.add_argument(
        "output_name",
        help="Markdown report file name inside reports/.",
    )
    save_report_section_parser.add_argument(
        "section_heading",
        help="Markdown heading to extract and save, case-insensitively.",
    )
    save_report_section_parser.add_argument(
        "--output-name",
        dest="new_output_name",
        help="Optional markdown file name for the extracted section inside reports/.",
    )

    save_latest_report_section_parser = subparsers.add_parser(
        "save-latest-modeling-report-section",
        help="Save one markdown section from the newest report as a new markdown artifact.",
    )
    save_latest_report_section_parser.add_argument(
        "section_heading",
        help="Markdown heading to extract and save from the newest report.",
    )
    save_latest_report_section_parser.add_argument(
        "--output-name",
        dest="new_output_name",
        help="Optional markdown file name for the extracted section inside reports/.",
    )

    compare_report_sections_parser = subparsers.add_parser(
        "compare-modeling-report-sections",
        help="Print a bounded diff summary between matching sections in two reports as JSON.",
    )
    compare_report_sections_parser.add_argument(
        "output_name",
        help="Primary markdown report file name inside reports/.",
    )
    compare_report_sections_parser.add_argument(
        "other_output_name",
        help="Comparison markdown report file name inside reports/.",
    )
    compare_report_sections_parser.add_argument(
        "section_heading",
        help="Markdown heading to compare, case-insensitively.",
    )

    compare_latest_report_sections_parser = subparsers.add_parser(
        "compare-latest-modeling-report-sections",
        help="Print a bounded diff summary for one section across the two newest reports as JSON.",
    )
    compare_latest_report_sections_parser.add_argument(
        "section_heading",
        help="Markdown heading to compare across the two newest reports.",
    )

    subparsers.add_parser(
        "read-latest-modeling-report",
        help="Print the most recently modified saved markdown modeling report.",
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

    subparsers.add_parser(
        "inspect-latest-modeling-report",
        help="Print metadata for the most recently modified saved markdown modeling report.",
    )

    preview_report_parser = subparsers.add_parser(
        "preview-modeling-report",
        help="Print a bounded preview of one saved markdown modeling report.",
    )
    preview_report_parser.add_argument(
        "output_name",
        help="Markdown report file name inside reports/.",
    )

    compare_report_parser = subparsers.add_parser(
        "compare-modeling-reports",
        help="Print a bounded diff summary between two saved modeling reports as JSON.",
    )
    compare_report_parser.add_argument(
        "output_name",
        help="Primary markdown report file name inside reports/.",
    )
    compare_report_parser.add_argument(
        "other_output_name",
        help="Comparison markdown report file name inside reports/.",
    )

    subparsers.add_parser(
        "compare-latest-modeling-reports",
        help="Print a bounded diff summary between the two most recent reports as JSON.",
    )

    subparsers.add_parser(
        "preview-latest-modeling-report",
        help="Print a bounded preview of the most recently modified modeling report.",
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

    if command == "search-modeling-report-content":
        content_matches = search_saved_modeling_report_content(args.query)
        print(json.dumps([match.model_dump(mode="json") for match in content_matches], indent=2))
        return 0

    if command == "search-latest-modeling-report-content":
        latest_content_matches = search_latest_modeling_report_content(args.query)
        print(
            json.dumps(
                [match.model_dump(mode="json") for match in latest_content_matches],
                indent=2,
            )
        )
        return 0

    if command == "search-modeling-report-sections":
        section_matches = search_saved_modeling_report_sections(args.query)
        print(json.dumps([match.model_dump(mode="json") for match in section_matches], indent=2))
        return 0

    if command == "search-latest-modeling-report-sections":
        latest_section_matches = search_latest_modeling_report_sections(args.query)
        print(
            json.dumps(
                [match.model_dump(mode="json") for match in latest_section_matches],
                indent=2,
            )
        )
        return 0

    if command == "summarize-modeling-report-sections":
        section_summaries = summarize_saved_modeling_report_sections()
        print(
            json.dumps(
                [summary.model_dump(mode="json") for summary in section_summaries],
                indent=2,
            )
        )
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

    if command == "list-modeling-report-sections":
        sections = list_saved_modeling_report_sections(args.output_name)
        print(json.dumps([section.model_dump(mode="json") for section in sections], indent=2))
        return 0

    if command == "list-latest-modeling-report-sections":
        latest_sections = list_latest_modeling_report_sections()
        print(
            json.dumps(
                [section.model_dump(mode="json") for section in latest_sections],
                indent=2,
            )
        )
        return 0

    if command == "read-modeling-report-section":
        section = read_saved_modeling_report_section(
            output_name=args.output_name,
            section_heading=args.section_heading,
        )
        print(json.dumps(section.model_dump(mode="json"), indent=2))
        return 0

    if command == "read-latest-modeling-report-section":
        latest_section = read_latest_modeling_report_section(args.section_heading)
        print(json.dumps(latest_section.model_dump(mode="json"), indent=2))
        return 0

    if command == "save-modeling-report-section":
        saved_section = save_modeling_report_section(
            output_name=args.output_name,
            section_heading=args.section_heading,
            new_output_name=args.new_output_name,
        )
        print(saved_section.output_path)
        return 0

    if command == "save-latest-modeling-report-section":
        latest_saved_section = save_latest_modeling_report_section(
            section_heading=args.section_heading,
            new_output_name=args.new_output_name,
        )
        print(latest_saved_section.output_path)
        return 0

    if command == "compare-modeling-report-sections":
        section_comparison = compare_saved_modeling_report_sections(
            output_name=args.output_name,
            other_output_name=args.other_output_name,
            section_heading=args.section_heading,
        )
        print(json.dumps(section_comparison.model_dump(mode="json"), indent=2))
        return 0

    if command == "compare-latest-modeling-report-sections":
        latest_section_comparison = compare_latest_modeling_report_sections(args.section_heading)
        print(json.dumps(latest_section_comparison.model_dump(mode="json"), indent=2))
        return 0

    if command == "read-latest-modeling-report":
        read_report = read_latest_modeling_report()
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

    if command == "inspect-latest-modeling-report":
        metadata = inspect_latest_modeling_report()
        print(json.dumps(metadata.model_dump(mode="json"), indent=2))
        return 0

    if command == "preview-modeling-report":
        preview = preview_saved_modeling_report(args.output_name)
        print(json.dumps(preview.model_dump(mode="json"), indent=2))
        return 0

    if command == "compare-modeling-reports":
        report_comparison = compare_saved_modeling_reports(
            output_name=args.output_name,
            other_output_name=args.other_output_name,
        )
        print(json.dumps(report_comparison.model_dump(mode="json"), indent=2))
        return 0

    if command == "compare-latest-modeling-reports":
        latest_report_comparison = compare_latest_modeling_reports()
        print(json.dumps(latest_report_comparison.model_dump(mode="json"), indent=2))
        return 0

    if command == "preview-latest-modeling-report":
        preview = preview_latest_modeling_report()
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
