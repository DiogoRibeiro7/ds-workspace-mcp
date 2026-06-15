from __future__ import annotations

import asyncio
import json
import os

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

SERVER_URL = "http://127.0.0.1:8000/mcp"


async def main() -> None:
    """Connect to the local server over Streamable HTTP and inspect one dataset."""

    headers = None
    api_key = os.getenv("MCP_API_KEY")
    if api_key:
        headers = {"Authorization": f"Bearer {api_key}"}

    async with (
        streamablehttp_client(SERVER_URL, headers=headers) as (read_stream, write_stream, _),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()

        tools = await session.list_tools()
        print("Tools:")
        print(json.dumps(tools.model_dump(mode="json"), indent=2))

        issues = await session.call_tool(
            "detect_csv_issues",
            {"file_name": "sample_clinic_usage.csv"},
        )
        print("\nIssues:")
        print(json.dumps(issues.model_dump(mode="json"), indent=2))

        correlations = await session.call_tool(
            "summarize_correlations",
            {"file_name": "sample_clinic_usage.csv", "method": "pearson"},
        )
        print("\nCorrelations:")
        print(json.dumps(correlations.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
