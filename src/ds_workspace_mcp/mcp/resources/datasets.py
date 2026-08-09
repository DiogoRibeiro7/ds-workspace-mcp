from __future__ import annotations

import logging

from ds_workspace_mcp.core import list_csv_files
from ds_workspace_mcp.mcp.app import _mcp_resource
from ds_workspace_mcp.tracing import traced_operation

logger = logging.getLogger(__name__)


@_mcp_resource("datasets://catalog")
def list_datasets() -> str:
    """
    List CSV datasets available to the assistant.

    Resources are useful for exposing data without side effects.
    """

    with traced_operation("resource.list_datasets"):
        files = list_csv_files()
        logger.info("Resource request datasets://catalog returned %s files", len(files))

        if not files:
            return "No CSV datasets found in the configured data directory."

        return "\n".join(files)
