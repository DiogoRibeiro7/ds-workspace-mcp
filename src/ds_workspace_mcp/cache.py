from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from ds_workspace_mcp.profiling import DatasetProfile


@dataclass(frozen=True)
class ProfileCacheKey:
    """Stable cache key for a profiled dataset."""

    path: Path
    file_size: int
    modified_time_ns: int
    max_categorical_values: int


class ProfileCache:
    """A small in-memory LRU cache for dataset profiles."""

    def __init__(self, enabled: bool, max_entries: int) -> None:
        self._enabled = enabled
        self._max_entries = max_entries
        self._entries: OrderedDict[ProfileCacheKey, DatasetProfile] = OrderedDict()

    def get(self, key: ProfileCacheKey) -> DatasetProfile | None:
        """Return a cached profile when available."""

        if not self._enabled:
            return None

        cached = self._entries.get(key)
        if cached is None:
            return None

        self._entries.move_to_end(key)
        return cached

    def set(self, key: ProfileCacheKey, value: DatasetProfile) -> None:
        """Insert or update a cached profile."""

        if not self._enabled:
            return

        self._entries[key] = value
        self._entries.move_to_end(key)

        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        """Remove all cached entries."""

        self._entries.clear()

    def __len__(self) -> int:
        """Return the current number of cached entries."""

        return len(self._entries)
