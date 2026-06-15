from __future__ import annotations

import logging
from pathlib import Path

import pytest

from ds_workspace_mcp.config import Settings
from ds_workspace_mcp.core import preview_csv_dataset
from ds_workspace_mcp.logging_config import LOG_FORMAT, configure_logging


def test_configure_logging_sets_expected_format(monkeypatch: pytest.MonkeyPatch) -> None:
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    try:
        configure_logging(Settings())
        handler = logging.getLogger().handlers[0]
        formatter = handler.formatter

        assert formatter is not None
        assert formatter._fmt == LOG_FORMAT
    finally:
        for handler in logging.getLogger().handlers[:]:
            logging.getLogger().removeHandler(handler)
        for handler in original_handlers:
            logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(original_level)


def test_preview_logging_does_not_log_row_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    dataset_path = tmp_path / "sample.csv"
    dataset_path.write_text("id,name\n1,Alice\n2,Bob\n", encoding="utf-8")

    with caplog.at_level(logging.INFO):
        preview = preview_csv_dataset("sample.csv", rows=1)

    assert preview.rows[0]["name"] == "Alice"
    assert "Alice" not in caplog.text
    assert "Built dataset preview for file_name=sample.csv rows=1" in caplog.text
