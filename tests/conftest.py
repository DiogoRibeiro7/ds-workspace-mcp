from __future__ import annotations

from collections.abc import Generator

import pytest

from ds_workspace_mcp.config import reset_settings_cache


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None, None, None]:
    """Keep settings reads isolated across tests."""

    reset_settings_cache()
    yield
    reset_settings_cache()
