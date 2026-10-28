from __future__ import annotations

import csv
import io
import logging
import os
import re
import tempfile
from pathlib import Path

from pydantic import BaseModel, Field

from ds_workspace_mcp.config import get_settings
from ds_workspace_mcp.exceptions import DatasetExportError
from ds_workspace_mcp.sql.duckdb_engine import query_dataset_with_duckdb
from ds_workspace_mcp.tracing import traced_operation

logger = logging.getLogger(__name__)

# Output files are direct children of MCP_DATA_ROOT; no selectors or nested paths.
_SAFE_CSV_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,122}\.csv\Z", re.IGNORECASE)


class CSVQueryExportResult(BaseModel):
    """Path-free metadata for a successfully exported query result."""

    source_file_name: str
    output_file_name: str
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=1)
    bytes_written: int = Field(ge=1)
    limit_applied: int = Field(ge=1)


def export_query_result_to_csv_dataset(
    file_name: str,
    sql: str,
    output_name: str,
    limit: int | None = None,
) -> CSVQueryExportResult:
    """Write a bounded, read-only SQL result as a new CSV in the data root.

    Export is disabled by default. The output uses an exclusive atomic link from
    a fully written temporary file; it cannot replace an existing CSV, including
    one created by another concurrent export.
    """

    settings = get_settings()
    if not settings.mcp_query_export_enabled:
        raise DatasetExportError("CSV query export is disabled (MCP_QUERY_EXPORT_ENABLED=false).")

    _validate_output_name(output_name)
    max_rows = min(settings.mcp_max_sql_rows, settings.mcp_max_export_rows)
    if limit is None:
        safe_limit = max_rows
    elif type(limit) is not int or not 1 <= limit <= max_rows:
        raise DatasetExportError(
            f"limit must be between 1 and {max_rows} (MCP_MAX_EXPORT_ROWS and MCP_MAX_SQL_ROWS)."
        )
    else:
        safe_limit = limit

    output_path = settings.mcp_data_root / output_name
    if output_path.exists() or output_path.is_symlink():
        raise DatasetExportError(f"Output dataset already exists: {output_name}")

    with traced_operation(
        "dataset.query_export",
        {
            "dataset.file_name": file_name,
            "dataset.output_name": output_name,
            "sql.limit": safe_limit,
        },
    ):
        # Reuse the validated, externally isolated DuckDB query path (and cache).
        result = query_dataset_with_duckdb(file_name=file_name, sql=sql, limit=safe_limit)
        if not result.columns or len(result.columns) > settings.mcp_max_export_columns:
            raise DatasetExportError(
                f"Export must contain between 1 and {settings.mcp_max_export_columns} "
                "columns (MCP_MAX_EXPORT_COLUMNS)."
            )
        if len(set(result.columns)) != len(result.columns):
            raise DatasetExportError("Export requires unique result column names.")

        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(result.columns)
        writer.writerows([row.get(column) for column in result.columns] for row in result.rows)
        payload = buffer.getvalue().encode("utf-8")
        max_bytes = min(settings.mcp_max_export_bytes, settings.mcp_max_dataset_bytes)
        if len(payload) > max_bytes:
            raise DatasetExportError(
                f"Export exceeds the maximum allowed size of {max_bytes} bytes "
                "(MCP_MAX_EXPORT_BYTES and MCP_MAX_DATASET_BYTES)."
            )

        _create_csv_atomically(output_path, payload)
        logger.info(
            "Exported DuckDB result source=%s output=%s rows=%s bytes=%s",
            file_name,
            output_name,
            result.row_count,
            len(payload),
        )
        return CSVQueryExportResult(
            source_file_name=file_name,
            output_file_name=output_name,
            row_count=result.row_count,
            column_count=len(result.columns),
            bytes_written=len(payload),
            limit_applied=safe_limit,
        )


def _validate_output_name(output_name: str) -> None:
    """Require a single safe .csv basename; reject traversal and selectors."""

    if not isinstance(output_name, str) or _SAFE_CSV_NAME.fullmatch(output_name) is None:
        raise DatasetExportError(
            "output_name must be a single .csv file name (letters, digits, dots, - or _)."
        )


def _create_csv_atomically(output_path: Path, payload: bytes) -> None:
    """Publish complete bytes without overwriting an existing filesystem entry."""

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=output_path.parent,
            prefix=".ds-workspace-export-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())

        # Hard-link creation is atomic and fails if any file or symlink exists.
        os.link(temporary_path, output_path)
    except FileExistsError as exc:
        raise DatasetExportError(f"Output dataset already exists: {output_path.name}") from exc
    except OSError as exc:
        raise DatasetExportError(f"Could not write output dataset: {output_path.name}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
