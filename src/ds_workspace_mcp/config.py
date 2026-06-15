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
DEFAULT_MAX_CATEGORICAL_VALUES = 5
DEFAULT_LOG_LEVEL: LogLevel = "INFO"


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
    mcp_max_categorical_values: int = DEFAULT_MAX_CATEGORICAL_VALUES
    mcp_log_level: LogLevel = DEFAULT_LOG_LEVEL

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

    @field_validator("mcp_max_categorical_values")
    @classmethod
    def validate_max_categorical_values(cls, value: int) -> int:
        """Constrain categorical summary sizes."""

        if value < 1 or value > 25:
            raise ValueError("MCP_MAX_CATEGORICAL_VALUES must be between 1 and 25.")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()


def reset_settings_cache() -> None:
    """Clear the cached settings instance for tests or reloads."""

    get_settings.cache_clear()
