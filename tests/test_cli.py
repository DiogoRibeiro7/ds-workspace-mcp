from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp import cli


def write_cli_dataset(root: Path, name: str = "sample.csv") -> Path:
    """Create a small dataset for CLI tests."""

    path = root / name
    pd.DataFrame(
        {
            "feature": [1, 2, 3],
            "target": [4, 5, 6],
        }
    ).to_csv(path, index=False)
    return path


def test_cli_serve_calls_server(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []

    def fake_serve() -> None:
        called.append("serve")

    monkeypatch.setattr(cli, "serve_main", fake_serve)

    exit_code = cli.main(["serve"])

    assert exit_code == 0
    assert called == ["serve"]


def test_cli_list_datasets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_cli_dataset(tmp_path, "b.csv")
    write_cli_dataset(tmp_path, "a.csv")

    exit_code = cli.main(["list-datasets"])
    output = capsys.readouterr().out.strip().splitlines()

    assert exit_code == 0
    assert output == ["a.csv", "b.csv"]


def test_cli_profile_dataset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_cli_dataset(tmp_path, "sample.csv")

    exit_code = cli.main(["profile-dataset", "sample.csv"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["file_name"] == "sample.csv"
    assert payload["row_count"] == 3


def test_cli_plan_modeling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_cli_dataset(tmp_path, "sample.csv")

    exit_code = cli.main(["plan-modeling", "sample.csv", "--target-column", "target"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["file_name"] == "sample.csv"
    assert payload["target_column"] == "target"
    assert "baseline_models" in payload
    assert "evaluation_metrics" in payload


def test_cli_report_modeling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_cli_dataset(tmp_path, "sample.csv")

    exit_code = cli.main(["report-modeling", "sample.csv", "--target-column", "target"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "## Summary" in output
    assert "`target`" in output


def test_cli_save_modeling_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_cli_dataset(tmp_path, "sample.csv")

    exit_code = cli.main(
        [
            "save-modeling-report",
            "sample.csv",
            "--target-column",
            "target",
            "--output-name",
            "sample-report.md",
        ]
    )
    saved_path = Path(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert saved_path.exists()
    assert saved_path.name == "sample-report.md"
    assert saved_path.parent.name == "reports"


def test_cli_list_modeling_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "b-report.md").write_text("b", encoding="utf-8")
    (reports_dir / "a-report.md").write_text("a", encoding="utf-8")

    exit_code = cli.main(["list-modeling-reports"])
    output = capsys.readouterr().out.strip().splitlines()

    assert exit_code == 0
    assert output == ["a-report.md", "b-report.md"]


def test_cli_search_modeling_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "clinic-usage-report.md").write_text("a", encoding="utf-8")
    (reports_dir / "finance-overview.md").write_text("b", encoding="utf-8")
    (reports_dir / "Clinic-wait-times.md").write_text("c", encoding="utf-8")

    exit_code = cli.main(["search-modeling-reports", "clinic"])
    output = capsys.readouterr().out.strip().splitlines()

    assert exit_code == 0
    assert output == ["clinic-usage-report.md", "Clinic-wait-times.md"]


def test_cli_search_modeling_report_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "clinic-usage-report.md").write_text(
        "# Clinic Usage\n\nStaffing risk is elevated on Mondays.",
        encoding="utf-8",
    )
    (reports_dir / "finance-overview.md").write_text(
        "# Finance\n\nBudget variance remains stable.",
        encoding="utf-8",
    )

    exit_code = cli.main(["search-modeling-report-content", "elevated"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert [match["output_name"] for match in payload] == ["clinic-usage-report.md"]
    assert payload[0]["headline"] == "Clinic Usage"
    assert "elevated" in payload[0]["snippet"].lower()


def test_cli_search_latest_modeling_report_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("# Older\n\nLegacy elevated issue", encoding="utf-8")
    newer.write_text("# Newer\n\nElevated queue pressure", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    exit_code = cli.main(["search-latest-modeling-report-content", "elevated"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert [match["output_name"] for match in payload] == ["newer.md"]
    assert payload[0]["headline"] == "Newer"
    assert "elevated" in payload[0]["snippet"].lower()


def test_cli_search_modeling_report_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "alpha.md").write_text(
        "# Alpha\n\n## Summary\nBody\n\n## Risks\n- Risk A",
        encoding="utf-8",
    )
    (reports_dir / "beta.md").write_text(
        "# Beta\n\n## Risk Review\n- Risk B",
        encoding="utf-8",
    )

    exit_code = cli.main(["search-modeling-report-sections", "risk"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert [(match["heading"], match["output_name"]) for match in payload] == [
        ("Risk Review", "beta.md"),
        ("Risks", "alpha.md"),
    ]
    assert "## Risk Review" in payload[0]["snippet"]


def test_cli_search_latest_modeling_report_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("# Older\n\n## Risk Log\nOld details", encoding="utf-8")
    newer.write_text(
        "# Newer\n\n## Summary\nBody\n\n## Risk Review\nNew details",
        encoding="utf-8",
    )
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    exit_code = cli.main(["search-latest-modeling-report-sections", "risk"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert [(match["heading"], match["output_name"]) for match in payload] == [
        ("Risk Review", "newer.md"),
    ]
    assert "## Risk Review" in payload[0]["snippet"]


def test_cli_summarize_modeling_report_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "alpha.md").write_text(
        "# Alpha\n\n## Summary\nBody\n\n## Risks\n- Risk A",
        encoding="utf-8",
    )
    (reports_dir / "beta.md").write_text(
        "# Beta\n\n## Summary\nBody\n\n## Next Steps\n- Step B",
        encoding="utf-8",
    )

    exit_code = cli.main(["summarize-modeling-report-sections"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert [(summary["heading"], summary["report_count"]) for summary in payload[:2]] == [
        ("Summary", 2),
        ("Alpha", 1),
    ]
    assert payload[0]["example_reports"] == ["alpha.md", "beta.md"]


def test_cli_list_recent_modeling_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("a", encoding="utf-8")
    newer.write_text("b", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    exit_code = cli.main(["list-recent-modeling-reports", "--limit", "2"])
    output = capsys.readouterr().out.strip().splitlines()

    assert exit_code == 0
    assert output == ["newer.md", "older.md"]


def test_cli_summarize_modeling_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("aa", encoding="utf-8")
    newer.write_text("bbbb", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    exit_code = cli.main(["summarize-modeling-reports", "--limit", "1"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["report_count"] == 2
    assert payload["total_size_bytes"] == 6
    assert [report["output_name"] for report in payload["most_recent_reports"]] == ["newer.md"]


def test_cli_read_modeling_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "sample-report.md").write_text("# Sample\n\nBody", encoding="utf-8")

    exit_code = cli.main(["read-modeling-report", "sample-report.md"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "# Sample" in output


def test_cli_list_modeling_report_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "sample-report.md").write_text(
        "# Sample\n\n## Summary\nBody\n\n## Risks\n- Risk",
        encoding="utf-8",
    )

    exit_code = cli.main(["list-modeling-report-sections", "sample-report.md"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert [(section["heading"], section["level"]) for section in payload] == [
        ("Sample", 1),
        ("Summary", 2),
        ("Risks", 2),
    ]


def test_cli_list_latest_modeling_report_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("# Older\n\n## Summary\nOld", encoding="utf-8")
    newer.write_text("# Newer\n\n## Summary\nNew\n\n## Risks\n- Risk", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    exit_code = cli.main(["list-latest-modeling-report-sections"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert [(section["heading"], section["level"]) for section in payload] == [
        ("Newer", 1),
        ("Summary", 2),
        ("Risks", 2),
    ]


def test_cli_read_modeling_report_section(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "sample-report.md").write_text(
        "# Sample\n\n## Summary\nBody\n\n## Risks\n- Risk",
        encoding="utf-8",
    )

    exit_code = cli.main(["read-modeling-report-section", "sample-report.md", "summary"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["heading"] == "Summary"
    assert payload["level"] == 2
    assert "## Summary" in payload["markdown"]
    assert "## Risks" not in payload["markdown"]


def test_cli_read_latest_modeling_report_section(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("# Older\n\n## Summary\nOld", encoding="utf-8")
    newer.write_text("# Newer\n\n## Summary\nNew\n\n## Risks\n- Risk", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    exit_code = cli.main(["read-latest-modeling-report-section", "summary"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["output_name"] == "newer.md"
    assert payload["heading"] == "Summary"
    assert "## Summary" in payload["markdown"]
    assert "## Risks" not in payload["markdown"]


def test_cli_save_modeling_report_section(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "sample-report.md").write_text(
        "# Sample\n\n## Summary\nBody\n\n## Risks\n- Risk",
        encoding="utf-8",
    )

    exit_code = cli.main(["save-modeling-report-section", "sample-report.md", "risks"])
    output = Path(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert output == (reports_dir / "sample-report--risks--section.md").resolve()
    assert output.read_text(encoding="utf-8") == "## Risks\n- Risk"


def test_cli_save_latest_modeling_report_section(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("# Older\n\n## Risks\n- Old", encoding="utf-8")
    newer.write_text("# Newer\n\n## Risks\n- New", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    exit_code = cli.main(["save-latest-modeling-report-section", "risks"])
    output = Path(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert output == (reports_dir / "newer--risks--section.md").resolve()
    assert output.read_text(encoding="utf-8") == "## Risks\n- New"


def test_cli_compare_modeling_report_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "before.md").write_text(
        "# Report\n\n## Risks\n- Risk A\n- Risk B",
        encoding="utf-8",
    )
    (reports_dir / "after.md").write_text(
        "# Report\n\n## Risks\n- Risk A\n- Risk C",
        encoding="utf-8",
    )

    exit_code = cli.main(["compare-modeling-report-sections", "before.md", "after.md", "risks"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["output_name"] == "before.md"
    assert payload["other_output_name"] == "after.md"
    assert payload["section_heading"] == "Risks"
    assert payload["changed"] is True
    assert payload["added_line_count"] == 1
    assert payload["removed_line_count"] == 1


def test_cli_compare_latest_modeling_report_sections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("# Report\n\n## Risks\n- Older", encoding="utf-8")
    newer.write_text("# Report\n\n## Risks\n- Newer", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    exit_code = cli.main(["compare-latest-modeling-report-sections", "risks"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["output_name"] == "older.md"
    assert payload["other_output_name"] == "newer.md"
    assert payload["section_heading"] == "Risks"
    assert payload["changed"] is True


def test_cli_read_latest_modeling_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("# Older\n\nBody", encoding="utf-8")
    newer.write_text("# Newer\n\nLatest body", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    exit_code = cli.main(["read-latest-modeling-report"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "# Newer" in output
    assert "Latest body" in output


def test_cli_delete_modeling_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    report_path = reports_dir / "sample-report.md"
    report_path.write_text("# Sample\n\nBody", encoding="utf-8")

    exit_code = cli.main(["delete-modeling-report", "sample-report.md"])
    output = Path(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert output == report_path.resolve()
    assert not report_path.exists()


def test_cli_rename_modeling_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    source = reports_dir / "old-name.md"
    source.write_text("# Sample\n\nBody", encoding="utf-8")

    exit_code = cli.main(["rename-modeling-report", "old-name.md", "new-name.md"])
    output = Path(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert output == (reports_dir / "new-name.md").resolve()
    assert not source.exists()
    assert (reports_dir / "new-name.md").exists()


def test_cli_copy_modeling_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    source = reports_dir / "source.md"
    source.write_text("# Sample\n\nBody", encoding="utf-8")

    exit_code = cli.main(["copy-modeling-report", "source.md", "copy.md"])
    output = Path(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert output == (reports_dir / "copy.md").resolve()
    assert source.exists()
    assert output.read_text(encoding="utf-8") == "# Sample\n\nBody"


def test_cli_copy_latest_modeling_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("# Older\n\nBody", encoding="utf-8")
    newer.write_text("# Newer\n\nLatest body", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    exit_code = cli.main(["copy-latest-modeling-report", "latest-copy.md"])
    output = Path(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert output == (reports_dir / "latest-copy.md").resolve()
    assert output.read_text(encoding="utf-8") == "# Newer\n\nLatest body"


def test_cli_inspect_modeling_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    report_path = reports_dir / "sample-report.md"
    report_path.write_text("# Sample\n\nBody", encoding="utf-8")

    exit_code = cli.main(["inspect-modeling-report", "sample-report.md"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["output_name"] == "sample-report.md"
    assert payload["output_path"] == str(report_path.resolve())
    assert payload["size_bytes"] > 0


def test_cli_inspect_latest_modeling_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("# Older\n\nBody", encoding="utf-8")
    newer.write_text("# Newer\n\nLatest body", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    exit_code = cli.main(["inspect-latest-modeling-report"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["output_name"] == "newer.md"
    assert payload["output_path"] == str(newer.resolve())
    assert payload["size_bytes"] > 0
    assert payload["modified_at"].endswith("+00:00")


def test_cli_preview_modeling_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    report_path = reports_dir / "sample-report.md"
    report_path.write_text("# Sample\n\n## Summary\nBody", encoding="utf-8")

    exit_code = cli.main(["preview-modeling-report", "sample-report.md"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["output_name"] == "sample-report.md"
    assert payload["headline"] == "Sample"
    assert payload["output_path"] == str(report_path.resolve())
    assert "## Summary" in payload["preview_markdown"]


def test_cli_compare_modeling_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "before.md").write_text("# Report\n\nLine A", encoding="utf-8")
    (reports_dir / "after.md").write_text("# Report\n\nLine B", encoding="utf-8")

    exit_code = cli.main(["compare-modeling-reports", "before.md", "after.md"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["output_name"] == "before.md"
    assert payload["other_output_name"] == "after.md"
    assert payload["changed"] is True
    assert payload["added_line_count"] == 1
    assert payload["removed_line_count"] == 1


def test_cli_compare_latest_modeling_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("# Report\n\nOlder", encoding="utf-8")
    newer.write_text("# Report\n\nNewer", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    exit_code = cli.main(["compare-latest-modeling-reports"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["output_name"] == "older.md"
    assert payload["other_output_name"] == "newer.md"
    assert payload["changed"] is True


def test_cli_preview_latest_modeling_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    older = reports_dir / "older.md"
    newer = reports_dir / "newer.md"
    older.write_text("# Older\n\nBody", encoding="utf-8")
    newer.write_text("# Newest\n\n## Summary\nBody", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    exit_code = cli.main(["preview-latest-modeling-report"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["output_name"] == "newer.md"
    assert payload["headline"] == "Newest"
    assert "## Summary" in payload["preview_markdown"]


def test_cli_generate_sample_healthcare_data(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / "generated.csv"

    exit_code = cli.main(
        [
            "generate-sample-healthcare-data",
            "--output",
            str(output_path),
            "--days",
            "5",
            "--clinics",
            "2",
            "--seed",
            "10",
        ]
    )

    printed_path = Path(capsys.readouterr().out.strip())
    assert exit_code == 0
    assert printed_path == output_path
    assert output_path.exists()


def test_cli_generate_sample_healthcare_data_rejects_invalid_options(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["generate-sample-healthcare-data", "--days", "0"])
    output = capsys.readouterr().out.strip()

    assert exit_code == 1
    assert "--days must be greater than 0." in output
