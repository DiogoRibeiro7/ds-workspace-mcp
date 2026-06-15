from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

DEFAULT_COMMAND = os.getenv("MCP_STDIO_COMMAND", "poetry")
DEFAULT_ARGS = os.getenv("MCP_STDIO_ARGS", "run ds-workspace-mcp serve").split()
DEFAULT_CWD = Path(os.getenv("MCP_STDIO_CWD", "."))
DEFAULT_DATA_ROOT = os.getenv("MCP_DATA_ROOT", "data")
DEFAULT_DATASET_NAME = os.getenv("MCP_EXAMPLE_DATASET", "sample_clinic_usage.csv")


async def main() -> None:
    """Connect to the local server over stdio and inspect one dataset."""

    server = StdioServerParameters(
        command=DEFAULT_COMMAND,
        args=DEFAULT_ARGS,
        cwd=str(DEFAULT_CWD),
        env={
            **os.environ,
            "MCP_TRANSPORT": "stdio",
            "MCP_DATA_ROOT": DEFAULT_DATA_ROOT,
        },
    )

    try:
        async with (
            stdio_client(server) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()

            resources = await session.list_resources()
            print("Resources:")
            print(json.dumps(resources.model_dump(mode="json"), indent=2))

            preview = await session.call_tool(
                "preview_csv",
                {"file_name": DEFAULT_DATASET_NAME, "rows": 3},
            )
            print("\nPreview:")
            print(json.dumps(preview.model_dump(mode="json"), indent=2))

            profile = await session.call_tool(
                "profile_csv",
                {"file_name": DEFAULT_DATASET_NAME},
            )
            print("\nProfile:")
            print(json.dumps(profile.model_dump(mode="json"), indent=2))
    except Exception as exc:
        print(f"stdio example failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    asyncio.run(main())
