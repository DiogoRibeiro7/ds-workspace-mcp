from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ds_workspace_mcp.config import (
    DEFAULT_DATA_ROOT,
    DEFAULT_HOST,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_CATEGORICAL_VALUES,
    DEFAULT_MAX_DATASET_BYTES,
    DEFAULT_MAX_PREVIEW_ROWS,
    DEFAULT_MAX_SQL_QUERY_LENGTH,
    DEFAULT_MAX_SQL_ROWS,
    DEFAULT_PORT,
    DEFAULT_PROFILE_CACHE_ENABLED,
    DEFAULT_PROFILE_CACHE_MAX_ENTRIES,
    DEFAULT_SQL_TIMEOUT_MS,
    DEFAULT_TRACING_CONSOLE_EXPORTER,
    DEFAULT_TRACING_ENABLED,
    DEFAULT_TRACING_SERVICE_NAME,
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
    assert settings.mcp_max_sql_query_length == DEFAULT_MAX_SQL_QUERY_LENGTH
    assert settings.mcp_sql_timeout_ms == DEFAULT_SQL_TIMEOUT_MS
    assert settings.mcp_max_categorical_values == DEFAULT_MAX_CATEGORICAL_VALUES
    assert settings.mcp_max_dataset_bytes == DEFAULT_MAX_DATASET_BYTES
    assert settings.mcp_profile_cache_enabled is DEFAULT_PROFILE_CACHE_ENABLED
    assert settings.mcp_profile_cache_max_entries == DEFAULT_PROFILE_CACHE_MAX_ENTRIES
    assert settings.mcp_log_level == DEFAULT_LOG_LEVEL
    assert settings.mcp_api_key is None
    assert settings.mcp_tracing_enabled is DEFAULT_TRACING_ENABLED
    assert settings.mcp_tracing_service_name == DEFAULT_TRACING_SERVICE_NAME
    assert settings.mcp_tracing_console_exporter is DEFAULT_TRACING_CONSOLE_EXPORTER


def test_settings_reject_invalid_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_TRANSPORT", "sse")

    with pytest.raises(ValidationError, match="mcp_transport"):
        Settings()


def test_settings_reject_invalid_row_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_MAX_PREVIEW_ROWS", "0")
    monkeypatch.setenv("MCP_MAX_SQL_ROWS", "10001")
    monkeypatch.setenv("MCP_MAX_SQL_QUERY_LENGTH", "99")
    monkeypatch.setenv("MCP_SQL_TIMEOUT_MS", "99")
    monkeypatch.setenv("MCP_MAX_CATEGORICAL_VALUES", "30")
    monkeypatch.setenv("MCP_MAX_DATASET_BYTES", "1000")
    monkeypatch.setenv("MCP_PROFILE_CACHE_MAX_ENTRIES", "0")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    message = str(exc_info.value)
    assert "MCP_MAX_PREVIEW_ROWS" in message
    assert "MCP_MAX_SQL_ROWS" in message
    assert "MCP_MAX_SQL_QUERY_LENGTH" in message
    assert "MCP_SQL_TIMEOUT_MS" in message
    assert "MCP_MAX_CATEGORICAL_VALUES" in message
    assert "MCP_MAX_DATASET_BYTES" in message
    assert "MCP_PROFILE_CACHE_MAX_ENTRIES" in message


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


def test_settings_treat_blank_api_key_as_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_API_KEY", "   ")

    settings = Settings()

    assert settings.mcp_api_key is None


def test_settings_reject_blank_tracing_service_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_TRACING_SERVICE_NAME", "   ")

    with pytest.raises(ValidationError, match="MCP_TRACING_SERVICE_NAME"):
        Settings()
