from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.core import (
    detect_csv_dataset_issues,
    list_csv_files,
    preview_csv_dataset,
    profile_csv_dataset,
)
from ds_workspace_mcp.ml.baselines import evaluate_baseline_model_dataset
from ds_workspace_mcp.report_export import (
    list_saved_modeling_reports,
    save_modeling_report_dataset,
)
from ds_workspace_mcp.sql.duckdb_engine import query_csv_with_duckdb_dataset
from ds_workspace_mcp.sql.sqlite_engine import query_sqlite_database
from ds_workspace_mcp.timeseries import validate_time_series_dataset


@pytest.fixture
def regression_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    data_root = tmp_path / "data"
    reports_root = tmp_path / "reports"
    data_root.mkdir()
    reports_root.mkdir()
    monkeypatch.setenv("MCP_DATA_ROOT", str(data_root))
    monkeypatch.setenv("MCP_REPORTS_ROOT", str(reports_root))
    _write_csv_fixture(data_root / "baseline.csv")
    _write_sqlite_fixture(data_root / "baseline.sqlite")
    return tmp_path


def test_dataset_discovery_preview_profile_and_issue_baseline(
    regression_workspace: Path,
) -> None:
    data_root = regression_workspace / "data"
    (data_root / "notes.txt").write_text("ignore", encoding="utf-8")

    assert list_csv_files() == ["baseline.csv"]

    preview = preview_csv_dataset("baseline.csv", rows=3)
    assert preview.file_name == "baseline.csv"
    assert len(preview.rows) == 3
    assert preview.rows[0]["clinic_id"] == "clinic_00"

    profile = profile_csv_dataset("baseline.csv")
    assert profile.row_count == 12
    assert profile.column_count == 7
    assert profile.missing_values["mostly_missing"] == 10
    assert profile.missing_percentage["mostly_missing"] == pytest.approx(83.33, abs=0.01)

    issues = detect_csv_dataset_issues("baseline.csv")
    issue_types = {issue.issue_type for issue in issues}
    assert {"high_missingness", "possible_identifier"}.issubset(issue_types)


def test_sql_baseline_for_duckdb_and_sqlite(regression_workspace: Path) -> None:
    duckdb_result = query_csv_with_duckdb_dataset(
        file_name="baseline.csv",
        sql="""
            SELECT region, SUM(appointments) AS total_appointments
            FROM dataset
            GROUP BY region
            ORDER BY region
        """,
        limit=10,
    )

    assert duckdb_result.columns == ["region", "total_appointments"]
    assert duckdb_result.rows == [
        {"region": "north", "total_appointments": 300.0},
        {"region": "south", "total_appointments": 312.0},
    ]
    assert duckdb_result.limit_applied == 10

    sqlite_result = query_sqlite_database(
        file_name="baseline.sqlite",
        sql="""
            SELECT region, SUM(appointments) AS total_appointments
            FROM visits
            GROUP BY region
            ORDER BY region
        """,
        limit=10,
    )

    assert sqlite_result.columns == ["region", "total_appointments"]
    assert sqlite_result.rows == [
        {"region": "north", "total_appointments": 45},
        {"region": "south", "total_appointments": 48},
    ]


def test_modeling_and_time_series_baseline(regression_workspace: Path) -> None:
    baseline = evaluate_baseline_model_dataset(
        file_name="baseline.csv",
        target_column="appointments",
        task_type="regression",
        test_size=0.25,
        random_state=7,
    )
    assert baseline.train_rows == 9
    assert baseline.test_rows == 3
    assert baseline.regression_metrics is not None
    assert baseline.classification_metrics is None

    time_series = validate_time_series_dataset(
        file_name="baseline.csv",
        time_column="service_date",
        target_column="appointments",
    )
    assert time_series.row_count == 12
    assert time_series.parsed_timestamp_count == 12
    assert time_series.inferred_frequency == "1D"
    assert time_series.missing_intervals == 1
    assert time_series.missing_target_values == 0


def test_modeling_report_persistence_baseline(regression_workspace: Path) -> None:
    saved_report = save_modeling_report_dataset(
        file_name="baseline.csv",
        target_column="appointments",
        output_name="baseline-report.md",
    )

    output_path = Path(saved_report.output_path)
    assert output_path.exists()
    assert output_path.name == "baseline-report.md"
    assert "## Summary" in output_path.read_text(encoding="utf-8")

    reports = list_saved_modeling_reports()
    assert [report.output_name for report in reports] == ["baseline-report.md"]
    assert reports[0].size_bytes > 0


def _write_csv_fixture(path: Path) -> None:
    rows = []
    service_dates = pd.to_datetime(
        [
            "2026-01-01",
            "2026-01-02",
            "2026-01-03",
            "2026-01-04",
            "2026-01-05",
            "2026-01-06",
            "2026-01-08",
            "2026-01-09",
            "2026-01-10",
            "2026-01-11",
            "2026-01-12",
            "2026-01-13",
        ]
    )
    for index, service_date in enumerate(service_dates):
        rows.append(
            {
                "clinic_id": f"clinic_{index:02d}",
                "region": "north" if index % 2 == 0 else "south",
                "service_date": service_date.strftime("%Y-%m-%d"),
                "appointments": 40 + index * 2,
                "staff_hours": 20.0 + index,
                "is_holiday": index in {1, 8},
                "mostly_missing": "known" if index in {2, 9} else None,
            }
        )

    pd.DataFrame(rows).to_csv(path, index=False)


def _write_sqlite_fixture(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            CREATE TABLE visits (
                visit_id INTEGER PRIMARY KEY,
                region TEXT NOT NULL,
                appointments INTEGER NOT NULL
            )
            """
        )
        connection.executemany(
            "INSERT INTO visits (region, appointments) VALUES (?, ?)",
            [
                ("north", 10),
                ("north", 15),
                ("north", 20),
                ("south", 12),
                ("south", 16),
                ("south", 20),
            ],
        )
        connection.commit()
    finally:
        connection.close()
