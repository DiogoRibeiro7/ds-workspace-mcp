from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import Any, TypeVar, cast

from mcp.server.fastmcp import FastMCP

from ds_workspace_mcp.auth import build_http_auth
from ds_workspace_mcp.config import Settings

_Handler = TypeVar("_Handler", bound=Callable[..., Any])

mcp = FastMCP("Data Science Workspace MCP", json_response=True)
_MCP_REGISTRARS: list[Callable[[FastMCP], None]] = []
_REGISTRATIONS_LOADED = False


def create_mcp_server(settings: Settings) -> FastMCP:
    """Create a configured MCP server instance with registered handlers."""

    _ensure_registrations_loaded()
    server = _new_mcp_server(settings)
    for register in _MCP_REGISTRARS:
        register(server)
    return server


def create_mcp(settings: Settings) -> FastMCP:
    """Create a configured MCP server instance.

    This compatibility alias preserves the previous public import while no longer
    mutating the module-global server.
    """

    return create_mcp_server(settings)


def _new_mcp_server(settings: Settings) -> FastMCP:
    auth_settings, token_verifier = build_http_auth(settings)
    return FastMCP(
        "Data Science Workspace MCP",
        json_response=True,
        log_level=settings.mcp_log_level,
        host=settings.mcp_host,
        port=settings.mcp_port,
        auth=auth_settings,
        token_verifier=token_verifier,
    )


def _record_mcp_decorator(kind: str, *args: Any, **kwargs: Any) -> Callable[[_Handler], _Handler]:
    def decorate(handler: _Handler) -> _Handler:
        def register(server: FastMCP) -> None:
            getattr(server, kind)(*args, **kwargs)(handler)

        _MCP_REGISTRARS.append(register)
        return cast(_Handler, getattr(mcp, kind)(*args, **kwargs)(handler))

    return decorate


def _mcp_resource(*args: Any, **kwargs: Any) -> Callable[[_Handler], _Handler]:
    return _record_mcp_decorator("resource", *args, **kwargs)


def _mcp_tool(*args: Any, **kwargs: Any) -> Callable[[_Handler], _Handler]:
    return _record_mcp_decorator("tool", *args, **kwargs)


def _mcp_prompt(*args: Any, **kwargs: Any) -> Callable[[_Handler], _Handler]:
    return _record_mcp_decorator("prompt", *args, **kwargs)


def _ensure_registrations_loaded() -> None:
    global _REGISTRATIONS_LOADED
    if _REGISTRATIONS_LOADED:
        return

    for module_name in (
        "ds_workspace_mcp.mcp.prompts.analysis",
        "ds_workspace_mcp.mcp.resources.databases",
        "ds_workspace_mcp.mcp.resources.datasets",
        "ds_workspace_mcp.mcp.resources.reports",
        "ds_workspace_mcp.mcp.tools.datasets",
        "ds_workspace_mcp.mcp.tools.modeling",
        "ds_workspace_mcp.mcp.tools.profiling",
        "ds_workspace_mcp.mcp.tools.reports",
        "ds_workspace_mcp.mcp.tools.sql",
        "ds_workspace_mcp.mcp.tools.timeseries",
    ):
        import_module(module_name)

    _REGISTRATIONS_LOADED = True
