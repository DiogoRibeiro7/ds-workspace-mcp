from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from ds_workspace_mcp.config import Settings
from ds_workspace_mcp.server import create_mcp


def build_settings(tmp_path: Path, api_key: str | None = None) -> Settings:
    """Create server settings for HTTP auth tests."""

    return Settings(
        mcp_data_root=tmp_path,
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
