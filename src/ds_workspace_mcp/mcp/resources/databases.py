from __future__ import annotations

import logging

from ds_workspace_mcp.mcp.app import _mcp_resource
from ds_workspace_mcp.sql.sqlite_engine import list_sqlite_files
from ds_workspace_mcp.tracing import traced_operation

logger = logging.getLogger(__name__)


@_mcp_resource("databases://sqlite")
def list_sqlite_databases() -> str:
    """List SQLite databases available to the assistant."""

    with traced_operation("resource.list_sqlite_databases"):
        files = list_sqlite_files()
        logger.info("Resource request databases://sqlite returned %s files", len(files))

        if not files:
            return "No SQLite databases found in the configured data directory."

        return "\n".join(files)
