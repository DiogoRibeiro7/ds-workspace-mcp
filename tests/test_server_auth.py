from __future__ import annotations

import asyncio
from pathlib import Path

from starlette.testclient import TestClient

from ds_workspace_mcp.config import Settings
from ds_workspace_mcp.server import create_mcp, create_mcp_server


def build_settings(tmp_path: Path, api_key: str | None = None) -> Settings:
    """Create server settings for HTTP auth tests."""

    return Settings(
        mcp_data_root=tmp_path,
        mcp_reports_root=tmp_path / "reports",
        mcp_transport="streamable-http",
        mcp_host="127.0.0.1",
        mcp_port=8000,
        mcp_api_key=api_key,
    )


def test_streamable_http_auth_disabled_by_default(tmp_path: Path) -> None:
    app = create_mcp(build_settings(tmp_path)).streamable_http_app()

    with TestClient(app) as client:
        response = client.get("/mcp")

    assert response.status_code not in {401, 403}


def test_streamable_http_requires_api_key_when_enabled(tmp_path: Path) -> None:
    app = create_mcp(build_settings(tmp_path, api_key="secret-token")).streamable_http_app()

    with TestClient(app) as client:
        response = client.get("/mcp")

    assert response.status_code == 401
    assert response.json()["error"] == "invalid_token"


def test_streamable_http_rejects_invalid_api_key(tmp_path: Path) -> None:
    app = create_mcp(build_settings(tmp_path, api_key="secret-token")).streamable_http_app()

    with TestClient(app) as client:
        response = client.get("/mcp", headers={"Authorization": "Bearer wrong-token"})

    assert response.status_code == 401
    assert response.json()["error"] == "invalid_token"


def test_streamable_http_accepts_valid_api_key(tmp_path: Path) -> None:
    app = create_mcp(build_settings(tmp_path, api_key="secret-token")).streamable_http_app()

    with TestClient(app) as client:
        response = client.get("/mcp", headers={"Authorization": "Bearer secret-token"})

    assert response.status_code not in {401, 403}


def test_create_mcp_reconfigures_runtime_settings(tmp_path: Path) -> None:
    first = create_mcp(build_settings(tmp_path, api_key=None))
    second = create_mcp(build_settings(tmp_path, api_key="secret-token"))

    assert first is not second
    assert second.settings.host == "127.0.0.1"
    assert second.settings.port == 8000
    assert second.settings.auth is not None
    assert first.settings.auth is None


def test_create_mcp_server_constructs_stdio_server(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    settings.mcp_transport = "stdio"

    server = create_mcp_server(settings)

    assert server.settings.host == "127.0.0.1"
    assert server.settings.port == 8000
    assert server.settings.auth is None


def test_create_mcp_server_constructs_http_server(tmp_path: Path) -> None:
    server = create_mcp_server(build_settings(tmp_path, api_key=None))

    assert server.settings.host == "127.0.0.1"
    assert server.settings.port == 8000
    assert server.settings.auth is None


def test_repeated_server_factory_calls_do_not_share_registered_tools(tmp_path: Path) -> None:
    first = create_mcp_server(build_settings(tmp_path))
    second = create_mcp_server(build_settings(tmp_path))

    first.remove_tool("preview_csv")

    async def list_tool_names() -> tuple[list[str], list[str]]:
        first_tools = await first.list_tools()
        second_tools = await second.list_tools()
        return [tool.name for tool in first_tools], [tool.name for tool in second_tools]

    first_tool_names, second_tool_names = asyncio.run(list_tool_names())

    assert "preview_csv" not in first_tool_names
    assert "preview_csv" in second_tool_names
