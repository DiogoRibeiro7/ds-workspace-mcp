from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Transport = Literal["stdio", "streamable-http"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

DEFAULT_DATA_ROOT = Path("data")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_MAX_PREVIEW_ROWS = 50
DEFAULT_MAX_SQL_ROWS = 1000
DEFAULT_MAX_SQL_QUERY_LENGTH = 20_000
DEFAULT_SQL_TIMEOUT_MS = 5_000
DEFAULT_MAX_CATEGORICAL_VALUES = 5
DEFAULT_MAX_DATASET_BYTES = 25_000_000
DEFAULT_PROFILE_CACHE_ENABLED = True
DEFAULT_PROFILE_CACHE_MAX_ENTRIES = 128
DEFAULT_LOG_LEVEL: LogLevel = "INFO"
DEFAULT_TRACING_ENABLED = False
DEFAULT_TRACING_SERVICE_NAME = "ds-workspace-mcp"
DEFAULT_TRACING_CONSOLE_EXPORTER = False


class Settings(BaseSettings):
    """Validated runtime settings for the MCP server."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mcp_data_root: Path = DEFAULT_DATA_ROOT
    mcp_transport: Transport = "streamable-http"
    mcp_host: str = DEFAULT_HOST
    mcp_port: int = DEFAULT_PORT
    mcp_max_preview_rows: int = DEFAULT_MAX_PREVIEW_ROWS
    mcp_max_sql_rows: int = DEFAULT_MAX_SQL_ROWS
    mcp_max_sql_query_length: int = DEFAULT_MAX_SQL_QUERY_LENGTH
    mcp_sql_timeout_ms: int = DEFAULT_SQL_TIMEOUT_MS
    mcp_max_categorical_values: int = DEFAULT_MAX_CATEGORICAL_VALUES
    mcp_max_dataset_bytes: int = DEFAULT_MAX_DATASET_BYTES
    mcp_profile_cache_enabled: bool = DEFAULT_PROFILE_CACHE_ENABLED
    mcp_profile_cache_max_entries: int = DEFAULT_PROFILE_CACHE_MAX_ENTRIES
    mcp_log_level: LogLevel = DEFAULT_LOG_LEVEL
    mcp_api_key: str | None = None
    mcp_tracing_enabled: bool = DEFAULT_TRACING_ENABLED
    mcp_tracing_service_name: str = DEFAULT_TRACING_SERVICE_NAME
    mcp_tracing_console_exporter: bool = DEFAULT_TRACING_CONSOLE_EXPORTER

    @field_validator("mcp_data_root", mode="after")
    @classmethod
    def validate_data_root(cls, value: Path) -> Path:
        """Resolve the data root and ensure it is a directory."""

        resolved = value.expanduser().resolve()
        if resolved.exists() and not resolved.is_dir():
            raise ValueError("MCP_DATA_ROOT must point to a directory.")
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    @field_validator("mcp_host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        """Reject blank host values."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("MCP_HOST must be a non-empty string.")
        return stripped

    @field_validator("mcp_api_key")
    @classmethod
    def validate_api_key(cls, value: str | None) -> str | None:
        """Normalize blank API keys to disabled auth."""

        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("mcp_tracing_service_name")
    @classmethod
    def validate_tracing_service_name(cls, value: str) -> str:
        """Reject blank tracing service names."""

        stripped = value.strip()
        if not stripped:
            raise ValueError("MCP_TRACING_SERVICE_NAME must be a non-empty string.")
        return stripped

    @field_validator("mcp_port")
    @classmethod
    def validate_port(cls, value: int) -> int:
        """Restrict the listening port to a valid TCP port."""

        if value < 1 or value > 65535:
            raise ValueError("MCP_PORT must be between 1 and 65535.")
        return value

    @field_validator("mcp_max_preview_rows")
    @classmethod
    def validate_max_preview_rows(cls, value: int) -> int:
        """Constrain preview row limits to a safe range."""

        if value < 1 or value > 1000:
            raise ValueError("MCP_MAX_PREVIEW_ROWS must be between 1 and 1000.")
        return value

    @field_validator("mcp_max_sql_rows")
    @classmethod
    def validate_max_sql_rows(cls, value: int) -> int:
        """Constrain SQL row limits to a safe range."""

        if value < 1 or value > 10000:
            raise ValueError("MCP_MAX_SQL_ROWS must be between 1 and 10000.")
        return value

    @field_validator("mcp_max_sql_query_length")
    @classmethod
    def validate_max_sql_query_length(cls, value: int) -> int:
        """Constrain SQL query text length."""

        if value < 100 or value > 100000:
            raise ValueError("MCP_MAX_SQL_QUERY_LENGTH must be between 100 and 100000.")
        return value

    @field_validator("mcp_sql_timeout_ms")
    @classmethod
    def validate_sql_timeout_ms(cls, value: int) -> int:
        """Constrain the SQL execution timeout."""

        if value < 100 or value > 600000:
            raise ValueError("MCP_SQL_TIMEOUT_MS must be between 100 and 600000.")
        return value

    @field_validator("mcp_max_categorical_values")
    @classmethod
    def validate_max_categorical_values(cls, value: int) -> int:
        """Constrain categorical summary sizes."""

        if value < 1 or value > 25:
            raise ValueError("MCP_MAX_CATEGORICAL_VALUES must be between 1 and 25.")
        return value

    @field_validator("mcp_max_dataset_bytes")
    @classmethod
    def validate_max_dataset_bytes(cls, value: int) -> int:
        """Constrain the maximum readable dataset size."""

        if value < 1024 or value > 500_000_000:
            raise ValueError("MCP_MAX_DATASET_BYTES must be between 1024 and 500000000.")
        return value

    @field_validator("mcp_profile_cache_max_entries")
    @classmethod
    def validate_profile_cache_max_entries(cls, value: int) -> int:
        """Constrain profile cache size."""

        if value < 1 or value > 1024:
            raise ValueError("MCP_PROFILE_CACHE_MAX_ENTRIES must be between 1 and 1024.")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()


def reset_settings_cache() -> None:
    """Clear the cached settings instance for tests or reloads."""

    get_settings.cache_clear()
