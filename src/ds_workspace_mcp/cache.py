from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from threading import RLock

from ds_workspace_mcp.profiling import DatasetProfile


@dataclass(frozen=True)
class ProfileCacheConfig:
    """Public configuration for profile cache behavior."""

    enabled: bool
    max_entries: int

    def __post_init__(self) -> None:
        if self.max_entries < 1:
            raise ValueError("max_entries must be greater than 0.")


@dataclass(frozen=True)
class ProfileCacheStats:
    """Path-free profile cache metrics suitable for external reporting."""

    enabled: bool
    max_entries: int
    hits: int
    misses: int
    evictions: int
    current_entries: int


@dataclass(frozen=True)
class ProfileCacheKey:
    """Stable cache key for a profiled dataset."""

    path: Path
    file_size: int
    modified_time_ns: int
    max_categorical_values: int


class ProfileCache:
    """A small in-memory LRU cache for dataset profiles."""

    def __init__(self, enabled: bool = True, max_entries: int = 128) -> None:
        self._lock = RLock()
        self._config = ProfileCacheConfig(enabled=enabled, max_entries=max_entries)
        self._entries: OrderedDict[ProfileCacheKey, DatasetProfile] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def configure(
        self,
        config: ProfileCacheConfig | None = None,
        *,
        enabled: bool | None = None,
        max_entries: int | None = None,
    ) -> None:
        """Apply cache configuration through the typed public API."""

        with self._lock:
            next_config = config or ProfileCacheConfig(
                enabled=self._config.enabled if enabled is None else enabled,
                max_entries=self._config.max_entries if max_entries is None else max_entries,
            )
            self._config = next_config
            if not next_config.enabled:
                self._entries.clear()
                return
            self._evict_to_limit()

    def get(self, key: ProfileCacheKey) -> DatasetProfile | None:
        """Return a cached profile when available."""

        with self._lock:
            if not self._config.enabled:
                self._misses += 1
                return None

            cached = self._entries.get(key)
            if cached is None:
                self._misses += 1
                return None

            self._hits += 1
            self._entries.move_to_end(key)
            return cached

    def set(self, key: ProfileCacheKey, value: DatasetProfile) -> None:
        """Insert or update a cached profile."""

        with self._lock:
            if not self._config.enabled:
                return

            self._entries[key] = value
            self._entries.move_to_end(key)
            self._evict_to_limit()

    def invalidate(self, key: ProfileCacheKey) -> bool:
        """Remove one cache entry by key and return whether it existed."""

        with self._lock:
            return self._entries.pop(key, None) is not None

    def clear(self, *, reset_metrics: bool = False) -> None:
        """Remove all cached entries."""

        with self._lock:
            self._entries.clear()
            if reset_metrics:
                self._hits = 0
                self._misses = 0
                self._evictions = 0

    def stats(self) -> ProfileCacheStats:
        """Return path-free metrics for the current cache state."""

        with self._lock:
            return ProfileCacheStats(
                enabled=self._config.enabled,
                max_entries=self._config.max_entries,
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
                current_entries=len(self._entries),
            )

    def __len__(self) -> int:
        """Return the current number of cached entries."""

        with self._lock:
            return len(self._entries)

    def _evict_to_limit(self) -> None:
        while len(self._entries) > self._config.max_entries:
            self._entries.popitem(last=False)
            self._evictions += 1
