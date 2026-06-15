from __future__ import annotations

from hmac import compare_digest

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl, TypeAdapter

from ds_workspace_mcp.config import Settings

DEFAULT_AUTH_CLIENT_ID = "ds-workspace-mcp-api-key"
SERVICE_DOCUMENTATION_URL = "https://github.com/DiogoRibeiro7/ds-workspace-mcp#readme"
HTTP_URL_ADAPTER = TypeAdapter(AnyHttpUrl)


class ApiKeyTokenVerifier(TokenVerifier):
    """Validate a shared bearer token for simple HTTP deployments."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return access metadata when the provided bearer token matches."""

        if not compare_digest(token, self._api_key):
            return None

        return AccessToken(
            token="<redacted>",
            client_id=DEFAULT_AUTH_CLIENT_ID,
            scopes=[],
        )


def build_http_auth(settings: Settings) -> tuple[AuthSettings | None, TokenVerifier | None]:
    """Build optional HTTP auth components from runtime settings."""

    if settings.mcp_transport != "streamable-http" or settings.mcp_api_key is None:
        return None, None

    resource_url = HTTP_URL_ADAPTER.validate_python(_build_resource_server_url(settings))
    auth_settings = AuthSettings(
        issuer_url=resource_url,
        resource_server_url=resource_url,
        service_documentation_url=HTTP_URL_ADAPTER.validate_python(SERVICE_DOCUMENTATION_URL),
        required_scopes=[],
    )
    return auth_settings, ApiKeyTokenVerifier(settings.mcp_api_key)


def _build_resource_server_url(settings: Settings) -> str:
    """Build the public resource URL used by FastMCP auth settings."""

    host = "127.0.0.1" if settings.mcp_host == "0.0.0.0" else settings.mcp_host
    return f"http://{host}:{settings.mcp_port}/mcp"
