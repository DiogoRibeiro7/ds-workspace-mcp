from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pandas as pd
import pytest
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


def write_dataset(root: Path, name: str = "sample.csv") -> Path:
    """Create a small dataset for transport integration tests."""

    path = root / name
    pd.DataFrame(
        {
            "clinic": ["north", "south", "east"],
            "appointments": [10, 8, 12],
        }
    ).to_csv(path, index=False)
    return path


def find_free_port() -> int:
    """Reserve an ephemeral port for a subprocess server."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def build_pythonpath(project_root: Path) -> str:
    """Build a PYTHONPATH that exposes the local src/ tree."""

    parts = [str(project_root / "src")]
    existing = os.environ.get("PYTHONPATH")
    if existing:
        parts.append(existing)
    return os.pathsep.join(parts)


def wait_for_tcp_server(host: str, port: int, timeout_seconds: float = 15.0) -> None:
    """Poll until the subprocess opens the requested TCP port."""

    deadline = time.time() + timeout_seconds
    last_error: OSError | None = None
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except OSError as exc:  # pragma: no cover - timing dependent
            last_error = exc
        time.sleep(0.2)

    raise RuntimeError(f"HTTP server did not become ready at {host}:{port}") from last_error


@pytest.fixture
def http_server(tmp_path: Path) -> Iterator[tuple[str, dict[str, str]]]:
    """Start the Streamable HTTP server in a subprocess for integration tests."""

    write_dataset(tmp_path)
    project_root = Path(__file__).resolve().parents[2]
    port = find_free_port()
    env = {
        **os.environ,
        "PYTHONPATH": build_pythonpath(project_root),
        "MCP_TRANSPORT": "streamable-http",
        "MCP_DATA_ROOT": str(tmp_path),
        "MCP_HOST": "127.0.0.1",
        "MCP_PORT": str(port),
    }

    process = subprocess.Popen(
        [sys.executable, "-m", "ds_workspace_mcp.server"],
        cwd=project_root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        base_url = f"http://127.0.0.1:{port}/mcp"
        wait_for_tcp_server("127.0.0.1", port)
        yield base_url, env
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive cleanup
            process.kill()
            process.wait(timeout=5)


@pytest.mark.integration
@pytest.mark.anyio
async def test_streamable_http_flow(http_server: tuple[str, dict[str, str]]) -> None:
    base_url, _ = http_server

    async with (
        streamable_http_client(base_url) as (read_stream, write_stream, _),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()

        tools = await session.list_tools()
        tool_names = {tool.name for tool in tools.tools}
        assert "profile_csv" in tool_names

        result = await session.call_tool("profile_csv", {"file_name": "sample.csv"})
        assert result.isError is False
        assert result.structuredContent is not None
        assert result.structuredContent["file_name"] == "sample.csv"
        assert result.structuredContent["row_count"] == 3


@pytest.mark.integration
@pytest.mark.anyio
async def test_streamable_http_flow_with_api_key(tmp_path: Path) -> None:
    write_dataset(tmp_path)
    project_root = Path(__file__).resolve().parents[2]
    port = find_free_port()
    api_key = "integration-secret"
    env = {
        **os.environ,
        "PYTHONPATH": build_pythonpath(project_root),
        "MCP_TRANSPORT": "streamable-http",
        "MCP_DATA_ROOT": str(tmp_path),
        "MCP_HOST": "127.0.0.1",
        "MCP_PORT": str(port),
        "MCP_API_KEY": api_key,
    }

    process = subprocess.Popen(
        [sys.executable, "-m", "ds_workspace_mcp.server"],
        cwd=project_root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        base_url = f"http://127.0.0.1:{port}/mcp"
        wait_for_tcp_server("127.0.0.1", port)

        async with (
            httpx.AsyncClient(
                headers={"Authorization": f"Bearer {api_key}"},
                follow_redirects=True,
            ) as client,
            streamable_http_client(
                base_url,
                http_client=client,
            ) as (read_stream, write_stream, _),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()

            result = await session.call_tool(
                "preview_csv",
                {"file_name": "sample.csv", "rows": 2},
            )
            assert result.isError is False
            assert result.structuredContent is not None
            assert len(result.structuredContent["rows"]) == 2
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive cleanup
            process.kill()
            process.wait(timeout=5)
