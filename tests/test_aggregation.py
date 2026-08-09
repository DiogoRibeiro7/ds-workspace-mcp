from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import duckdb
import pandas as pd
import pytest
from pydantic import ValidationError

from ds_workspace_mcp.aggregation import (
    AggregateOperation,
    AggregationFilter,
    AggregationMetric,
    AggregationOrder,
    AggregationRequest,
    FilterOperation,
    SortDirection,
    aggregate_dataset,
)
from ds_workspace_mcp.exceptions import InvalidAggregationError


def write_aggregation_csv(root: Path) -> None:
    pd.DataFrame(
        {
            "clinic": ["north", "north", "south", "south", "west"],
            "appointments": [10, 12, 6, 9, 4],
            "score": [1.0, 2.0, 3.5, None, 5.0],
            "status": ["open", "closed", "open", "open", "closed"],
        }
    ).to_csv(root / "aggregate.csv", index=False)


def write_aggregation_parquet(root: Path) -> None:
    with duckdb.connect(database=":memory:") as connection:
        connection.execute(
            """
            CREATE TABLE sample AS
            SELECT *
            FROM (
                VALUES
                    ('north', 10),
                    ('north', 12),
                    ('south', 6)
            ) AS rows(clinic, appointments)
            """
        )
        connection.execute("COPY sample TO ? (FORMAT PARQUET)", [str(root / "aggregate.parquet")])


def test_aggregate_dataset_groups_orders_and_limits_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_aggregation_csv(tmp_path)

    result = aggregate_dataset(
        AggregationRequest(
            file_name="aggregate.csv",
            group_by=["clinic"],
            filters=[
                AggregationFilter(
                    column="appointments",
                    operation=FilterOperation.GTE,
                    value=6,
                )
            ],
            metrics=[
                AggregationMetric(operation=AggregateOperation.COUNT, output_name="rows"),
                AggregationMetric(
                    operation=AggregateOperation.SUM,
                    column="appointments",
                    output_name="total_appointments",
                ),
            ],
            order_by=[AggregationOrder(column="total_appointments", direction=SortDirection.DESC)],
            limit=2,
        )
    )

    assert result.group_by == ["clinic"]
    assert result.metric_columns == ["rows", "total_appointments"]
    assert result.limit_applied == 2
    assert result.total_group_count == 2
    assert result.rows == [
        {"clinic": "north", "rows": 2, "total_appointments": 22},
        {"clinic": "south", "rows": 2, "total_appointments": 15},
    ]


def test_aggregate_dataset_supports_parquet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_aggregation_parquet(tmp_path)

    result = aggregate_dataset(
        AggregationRequest(
            file_name="aggregate.parquet",
            group_by=["clinic"],
            metrics=[
                AggregationMetric(
                    operation=AggregateOperation.MEAN,
                    column="appointments",
                    output_name="mean_appointments",
                )
            ],
            order_by=[AggregationOrder(column="clinic")],
            limit=10,
        )
    )

    assert result.rows == [
        {"clinic": "north", "mean_appointments": 11.0},
        {"clinic": "south", "mean_appointments": 6.0},
    ]


def test_aggregate_dataset_rejects_unsupported_metric_dtype(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_aggregation_csv(tmp_path)

    with pytest.raises(InvalidAggregationError, match="sum requires a numeric column"):
        aggregate_dataset(
            AggregationRequest(
                file_name="aggregate.csv",
                metrics=[AggregationMetric(operation=AggregateOperation.SUM, column="status")],
            )
        )


def test_aggregate_dataset_rejects_malicious_column_names(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_aggregation_csv(tmp_path)

    with pytest.raises(InvalidAggregationError, match="Unknown group_by column"):
        aggregate_dataset(
            AggregationRequest(
                file_name="aggregate.csv",
                group_by=["clinic; DROP TABLE dataset"],
                metrics=[AggregationMetric(operation=AggregateOperation.COUNT)],
            )
        )


def test_aggregate_dataset_rejects_malicious_filter_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_aggregation_csv(tmp_path)

    with pytest.raises(InvalidAggregationError, match="Filter values must be scalar"):
        aggregate_dataset(
            AggregationRequest(
                file_name="aggregate.csv",
                filters=[
                    AggregationFilter(
                        column="clinic",
                        operation=FilterOperation.EQ,
                        value={"$ne": "north"},
                    )
                ],
                metrics=[AggregationMetric(operation=AggregateOperation.COUNT)],
            )
        )


def test_aggregate_dataset_rejects_grouping_cardinality_over_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_MAX_SQL_ROWS", "2")
    pd.DataFrame({"id": [1, 2, 3], "value": [1, 1, 1]}).to_csv(
        tmp_path / "wide.csv",
        index=False,
    )

    with pytest.raises(InvalidAggregationError, match="grouping cardinality"):
        aggregate_dataset(
            AggregationRequest(
                file_name="wide.csv",
                group_by=["id"],
                metrics=[AggregationMetric(operation=AggregateOperation.COUNT)],
                limit=2,
            )
        )


def test_aggregate_request_rejects_unknown_operations() -> None:
    with pytest.raises(ValidationError):
        AggregationRequest(
            file_name="aggregate.csv",
            metrics=cast(Any, [{"operation": "eval", "column": "appointments"}]),
        )
