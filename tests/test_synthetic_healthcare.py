from __future__ import annotations

from pathlib import Path

import pandas as pd

from ds_workspace_mcp.synthetic.healthcare import (
    GeneratorConfig,
    generate_healthcare_dataset,
    write_healthcare_dataset,
)


def test_generate_healthcare_dataset_has_expected_columns(tmp_path: Path) -> None:
    config = GeneratorConfig(output_path=tmp_path / "synthetic.csv", days=10, clinics=2, seed=7)

    df = generate_healthcare_dataset(config)

    assert list(df.columns) == [
        "clinic_id",
        "date",
        "appointments_scheduled",
        "appointments_completed",
        "cancellations",
        "no_shows",
        "marketing_campaign",
        "local_holiday",
        "staff_available",
        "average_wait_time",
        "patient_satisfaction_score",
    ]


def test_generate_healthcare_dataset_is_reproducible(tmp_path: Path) -> None:
    config = GeneratorConfig(output_path=tmp_path / "synthetic.csv", days=8, clinics=2, seed=99)

    first = generate_healthcare_dataset(config)
    second = generate_healthcare_dataset(config)

    pd.testing.assert_frame_equal(first, second)


def test_generate_healthcare_dataset_row_count(tmp_path: Path) -> None:
    config = GeneratorConfig(output_path=tmp_path / "synthetic.csv", days=12, clinics=3, seed=13)

    df = generate_healthcare_dataset(config)

    assert len(df) == 36


def test_generate_healthcare_dataset_date_range(tmp_path: Path) -> None:
    config = GeneratorConfig(
        output_path=tmp_path / "synthetic.csv",
        start_date="2025-02-01",
        days=5,
        clinics=1,
        seed=5,
    )

    df = generate_healthcare_dataset(config)

    assert df["date"].min() == "2025-02-01"
    assert df["date"].max() == "2025-02-05"


def test_write_healthcare_dataset_creates_file(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "synthetic.csv"
    config = GeneratorConfig(output_path=output_path, days=4, clinics=2, seed=11)

    written_path = write_healthcare_dataset(config)

    assert written_path == output_path
    assert written_path.exists()
