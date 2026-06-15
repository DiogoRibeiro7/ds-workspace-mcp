from __future__ import annotations

from collections.abc import Generator

import pytest

from ds_workspace_mcp.config import reset_settings_cache
from ds_workspace_mcp.core import reset_profile_cache
from ds_workspace_mcp.tracing import reset_tracing_state


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None, None, None]:
    """Keep settings reads isolated across tests."""

    reset_settings_cache()
    reset_profile_cache()
    reset_tracing_state()
    yield
    reset_settings_cache()
    reset_profile_cache()
    reset_tracing_state()
