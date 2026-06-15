from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ds_workspace_mcp.config import (
    DEFAULT_DATA_ROOT,
    DEFAULT_HOST,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_CATEGORICAL_VALUES,
    DEFAULT_MAX_PREVIEW_ROWS,
    DEFAULT_MAX_SQL_ROWS,
    DEFAULT_PORT,
    Settings,
    get_settings,
)


def test_settings_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    settings = get_settings()

    assert settings.mcp_data_root == (tmp_path / DEFAULT_DATA_ROOT).resolve()
    assert settings.mcp_transport == "streamable-http"
    assert settings.mcp_host == DEFAULT_HOST
    assert settings.mcp_port == DEFAULT_PORT
    assert settings.mcp_max_preview_rows == DEFAULT_MAX_PREVIEW_ROWS
    assert settings.mcp_max_sql_rows == DEFAULT_MAX_SQL_ROWS
    assert settings.mcp_max_categorical_values == DEFAULT_MAX_CATEGORICAL_VALUES
    assert settings.mcp_log_level == DEFAULT_LOG_LEVEL


def test_settings_reject_invalid_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_TRANSPORT", "sse")

    with pytest.raises(ValidationError, match="mcp_transport"):
        Settings()


def test_settings_reject_invalid_row_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_MAX_PREVIEW_ROWS", "0")
    monkeypatch.setenv("MCP_MAX_SQL_ROWS", "10001")
    monkeypatch.setenv("MCP_MAX_CATEGORICAL_VALUES", "30")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    message = str(exc_info.value)
    assert "MCP_MAX_PREVIEW_ROWS" in message
    assert "MCP_MAX_SQL_ROWS" in message
    assert "MCP_MAX_CATEGORICAL_VALUES" in message


def test_settings_accept_custom_data_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    custom_root = tmp_path / "custom-data"
    monkeypatch.setenv("MCP_DATA_ROOT", str(custom_root))

    settings = get_settings()

    assert settings.mcp_data_root == custom_root.resolve()
    assert settings.mcp_data_root.exists()
    assert settings.mcp_data_root.is_dir()
