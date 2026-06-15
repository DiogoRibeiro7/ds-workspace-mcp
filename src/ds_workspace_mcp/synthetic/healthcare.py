from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_OUTPUT_NAME = "synthetic_clinic_usage.csv"
DEFAULT_START_DATE = "2025-01-01"
DEFAULT_DAYS = 90
DEFAULT_CLINICS = 4
DEFAULT_SEED = 42


@dataclass(frozen=True)
class GeneratorConfig:
    """Configuration for synthetic healthcare dataset generation."""

    output_path: Path
    start_date: str = DEFAULT_START_DATE
    days: int = DEFAULT_DAYS
    clinics: int = DEFAULT_CLINICS
    seed: int = DEFAULT_SEED


def generate_healthcare_dataset(config: GeneratorConfig) -> pd.DataFrame:
    """Generate a synthetic clinic operations dataset."""

    rng = np.random.default_rng(config.seed)
    dates = pd.date_range(config.start_date, periods=config.days, freq="D")
    clinic_ids = [f"CLN-{index + 1:03d}" for index in range(config.clinics)]

    rows: list[dict[str, object]] = []
    for clinic_index, clinic_id in enumerate(clinic_ids):
        clinic_scale = 1.0 + clinic_index * 0.25
        for date in dates:
            weekday = date.weekday()
            weekend_factor = 0.75 if weekday >= 5 else 1.0
            month_factor = 1.0 + 0.15 * np.sin((date.dayofyear / 365.0) * 2 * np.pi)
            campaign = int(rng.random() < 0.18)
            local_holiday = int(date.month == 12 and date.day in {24, 25, 31})

            base_demand = 65 * clinic_scale * weekend_factor * month_factor
            campaign_lift = 9 if campaign else 0
            holiday_drag = -6 if local_holiday else 0
            noise = rng.normal(0, 6)
            appointments_scheduled = max(
                15,
                int(round(base_demand + campaign_lift + holiday_drag + noise)),
            )

            no_show_rate = 0.08 + (0.03 if campaign else 0.0) + max(0, 0.02 * (weekday == 0))
            cancellation_rate = 0.06 + (0.01 if local_holiday else 0.0)
            no_shows = min(
                appointments_scheduled,
                int(round(appointments_scheduled * no_show_rate)),
            )
            cancellations = min(
                appointments_scheduled - no_shows,
                int(round(appointments_scheduled * cancellation_rate)),
            )
            appointments_completed = max(
                0,
                appointments_scheduled - cancellations - no_shows + int(rng.integers(-2, 3)),
            )

            staff_available = max(
                3,
                int(round((appointments_scheduled / 12) + rng.normal(0, 0.7))),
            )
            avg_wait_time = max(
                5.0,
                11.0
                + (appointments_scheduled / max(staff_available, 1)) * 1.9
                + rng.normal(0, 2.5)
                - (2.0 if local_holiday else 0.0),
            )
            patient_satisfaction = min(
                99.0,
                max(
                    55.0,
                    89.0
                    - avg_wait_time * 0.8
                    - no_shows * 0.15
                    + (3.0 if campaign else 0.0)
                    + rng.normal(0, 2.8),
                ),
            )

            row = {
                "clinic_id": clinic_id,
                "date": date.strftime("%Y-%m-%d"),
                "appointments_scheduled": appointments_scheduled,
                "appointments_completed": min(appointments_completed, appointments_scheduled),
                "cancellations": cancellations,
                "no_shows": no_shows,
                "marketing_campaign": campaign,
                "local_holiday": local_holiday,
                "staff_available": staff_available,
                "average_wait_time": round(avg_wait_time, 2),
                "patient_satisfaction_score": round(patient_satisfaction, 2),
            }
            rows.append(row)

    df = pd.DataFrame(rows)
    return _inject_missingness(df=df, rng=rng)


def write_healthcare_dataset(config: GeneratorConfig) -> Path:
    """Generate and write a synthetic healthcare dataset to disk."""

    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    df = generate_healthcare_dataset(config)
    df.to_csv(config.output_path, index=False)
    return config.output_path


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(description="Generate a synthetic clinic usage dataset.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data") / DEFAULT_OUTPUT_NAME,
        help="Output CSV path.",
    )
    parser.add_argument(
        "--start-date",
        default=DEFAULT_START_DATE,
        help="Start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help="Number of daily observations per clinic.",
    )
    parser.add_argument(
        "--clinics",
        type=int,
        default=DEFAULT_CLINICS,
        help="Number of clinics to simulate.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Random seed for reproducible generation.",
    )
    return parser


def main() -> None:
    """CLI entrypoint for dataset generation."""

    parser = build_parser()
    args = parser.parse_args()
    config = GeneratorConfig(
        output_path=args.output,
        start_date=args.start_date,
        days=args.days,
        clinics=args.clinics,
        seed=args.seed,
    )
    if config.days < 1:
        raise SystemExit("--days must be greater than 0.")
    if config.clinics < 1:
        raise SystemExit("--clinics must be greater than 0.")

    output_path = write_healthcare_dataset(config)
    print(output_path)


def _inject_missingness(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Inject small, reproducible missingness into selected columns."""

    result = df.copy()
    for column, rate in {
        "average_wait_time": 0.04,
        "patient_satisfaction_score": 0.05,
    }.items():
        mask = rng.random(len(result)) < rate
        result.loc[mask, column] = np.nan
    return result
