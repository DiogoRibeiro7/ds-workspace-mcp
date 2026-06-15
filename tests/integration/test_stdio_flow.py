from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def write_dataset(root: Path, name: str = "sample.csv") -> Path:
    """Create a small dataset for stdio integration tests."""

    path = root / name
    pd.DataFrame(
        {
            "clinic": ["north", "south", "east"],
            "appointments": [10, 8, 12],
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


@pytest.mark.integration
@pytest.mark.anyio
async def test_stdio_flow(tmp_path: Path) -> None:
    write_dataset(tmp_path)
    project_root = Path(__file__).resolve().parents[2]
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "ds_workspace_mcp.server"],
        cwd=str(project_root),
        env={
            **os.environ,
            "PYTHONPATH": build_pythonpath(project_root),
            "MCP_TRANSPORT": "stdio",
            "MCP_DATA_ROOT": str(tmp_path),
        },
    )

    async with (
        stdio_client(server) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()

        resources = await session.list_resources()
        resource_uris = {str(resource.uri) for resource in resources.resources}
        assert "datasets://catalog" in resource_uris

        result = await session.call_tool("preview_csv", {"file_name": "sample.csv", "rows": 2})
        assert result.isError is False
        assert result.structuredContent is not None
        assert result.structuredContent["file_name"] == "sample.csv"
        assert len(result.structuredContent["rows"]) == 2
