from __future__ import annotations

import logging

from ds_workspace_mcp.config import Settings

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(settings: Settings) -> None:
    """Configure process logging for local and container execution."""

    root_logger = logging.getLogger()
    level = getattr(logging, settings.mcp_log_level)

    if root_logger.handlers:
        root_logger.setLevel(level)
        for handler in root_logger.handlers:
            handler.setLevel(level)
            handler.setFormatter(logging.Formatter(LOG_FORMAT))
        return

    logging.basicConfig(level=level, format=LOG_FORMAT)
