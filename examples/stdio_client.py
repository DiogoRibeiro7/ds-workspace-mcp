from __future__ import annotations

import asyncio
import json
import os

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main() -> None:
    """Connect to the local server over stdio and inspect one dataset."""

    server = StdioServerParameters(
        command="poetry",
        args=["run", "ds-workspace-mcp", "serve"],
        cwd=".",
        env={
            **os.environ,
            "MCP_TRANSPORT": "stdio",
            "MCP_DATA_ROOT": "data",
        },
    )

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
            {"file_name": "sample_clinic_usage.csv", "rows": 3},
        )
        print("\nPreview:")
        print(json.dumps(preview.model_dump(mode="json"), indent=2))

        profile = await session.call_tool(
            "profile_csv",
            {"file_name": "sample_clinic_usage.csv"},
        )
        print("\nProfile:")
        print(json.dumps(profile.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
