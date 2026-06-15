from __future__ import annotations

import asyncio
import json
import os
import sys

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")
DEFAULT_DATASET_NAME = os.getenv("MCP_EXAMPLE_DATASET", "sample_clinic_usage.csv")


async def main() -> None:
    """Connect to the local server over Streamable HTTP and inspect one dataset."""

    client_kwargs: dict[str, object] = {}
    api_key = os.getenv("MCP_API_KEY")
    if api_key:
        client_kwargs["headers"] = {"Authorization": f"Bearer {api_key}"}
    client_kwargs["follow_redirects"] = True

    dataset_name = DEFAULT_DATASET_NAME

    try:
        async with (
            httpx.AsyncClient(**client_kwargs) as client,
            streamable_http_client(
                SERVER_URL,
                http_client=client,
            ) as (read_stream, write_stream, _),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()

            tools = await session.list_tools()
            print("Tools:")
            print(json.dumps(tools.model_dump(mode="json"), indent=2))

            issues = await session.call_tool(
                "detect_csv_issues",
                {"file_name": dataset_name},
            )
            print("\nIssues:")
            print(json.dumps(issues.model_dump(mode="json"), indent=2))

            correlations = await session.call_tool(
                "summarize_correlations",
                {"file_name": dataset_name, "method": "pearson"},
            )
            print("\nCorrelations:")
            print(json.dumps(correlations.model_dump(mode="json"), indent=2))
    except Exception as exc:
        print(f"http example failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    asyncio.run(main())
