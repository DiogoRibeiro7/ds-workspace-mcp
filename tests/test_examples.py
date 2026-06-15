from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import pytest


def write_example_dataset(root: Path, name: str = "example.csv") -> Path:
    """Create a small dataset for example smoke tests."""

    path = root / name
    pd.DataFrame(
        {
            "clinic": ["north", "south", "east"],
            "appointments": [10, 8, 12],
            "completed": [9, 7, 11],
        }
    ).to_csv(path, index=False)
    return path


def build_pythonpath(project_root: Path) -> str:
    """Build a PYTHONPATH that exposes the local src/ tree."""

    parts = [str(project_root / "src")]
    existing = os.environ.get("PYTHONPATH")
    if existing:
        parts.append(existing)
    return os.pathsep.join(parts)


def find_free_port() -> int:
    """Reserve an ephemeral port for a subprocess server."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


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


@pytest.mark.integration
def test_stdio_example_runs(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    write_example_dataset(tmp_path)

    result = subprocess.run(
        [sys.executable, "examples/stdio_client.py"],
        cwd=project_root,
        env={
            **os.environ,
            "PYTHONPATH": build_pythonpath(project_root),
            "MCP_STDIO_COMMAND": sys.executable,
            "MCP_STDIO_ARGS": "-m ds_workspace_mcp.server",
            "MCP_STDIO_CWD": str(project_root),
            "MCP_DATA_ROOT": str(tmp_path),
            "MCP_EXAMPLE_DATASET": "example.csv",
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Resources:" in result.stdout
    assert '"file_name": "example.csv"' in result.stdout


@pytest.fixture
def example_http_server(tmp_path: Path) -> Iterator[str]:
    """Start the Streamable HTTP server for the example client smoke test."""

    project_root = Path(__file__).resolve().parents[1]
    write_example_dataset(tmp_path)
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
        wait_for_tcp_server("127.0.0.1", port)
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive cleanup
            process.kill()
            process.wait(timeout=5)


@pytest.mark.integration
def test_http_example_runs(example_http_server: str) -> None:
    project_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [sys.executable, "examples/http_client.py"],
        cwd=project_root,
        env={
            **os.environ,
            "PYTHONPATH": build_pythonpath(project_root),
            "MCP_SERVER_URL": example_http_server,
            "MCP_EXAMPLE_DATASET": "example.csv",
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Tools:" in result.stdout
    assert '"warning_type"' in result.stdout
