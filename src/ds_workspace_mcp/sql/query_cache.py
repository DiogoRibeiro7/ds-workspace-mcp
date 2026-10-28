from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Generic, TypeVar

from pydantic import BaseModel

_Result = TypeVar("_Result", bound=BaseModel)


@dataclass(frozen=True)
class QueryCacheKey:
    """Identify a query result by dataset version, SQL and output row bound."""

    path: Path
    file_name: str
    file_size: int
    modified_time_ns: int
    normalized_sql: str
    row_limit: int


@dataclass(frozen=True)
class QueryCacheStats:
    """Report cache activity without leaking paths or SQL query contents."""

    enabled: bool
    max_entries: int
    hits: int
    misses: int
    evictions: int
    current_entries: int


class QueryCache(Generic[_Result]):
    """Thread-safe, bounded in-memory LRU for successful query results.

    Results are deep-copied on insert and lookup so callers cannot mutate
    entries that are subsequently served to another request.
    """

    def __init__(self, *, enabled: bool = True, max_entries: int = 32) -> None:
        if not isinstance(enabled, bool):
            raise TypeError("enabled must be a boolean.")
        self._validate_max_entries(max_entries)
        self._lock = RLock()
        self._enabled = enabled
        self._max_entries = max_entries
        self._entries: OrderedDict[QueryCacheKey, _Result] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def configure(self, *, enabled: bool, max_entries: int) -> None:
        """Apply validated runtime settings without replacing cache metrics."""

        if not isinstance(enabled, bool):
            raise TypeError("enabled must be a boolean.")
        self._validate_max_entries(max_entries)
        with self._lock:
            self._enabled = enabled
            self._max_entries = max_entries
            if not enabled:
                self._entries.clear()
            self._evict_to_limit()

    def get(self, key: QueryCacheKey) -> _Result | None:
        """Return a defensive copy of one cached result, if present."""

        with self._lock:
            result = self._entries.get(key) if self._enabled else None
            if result is None:
                self._misses += 1
                return None
            self._hits += 1
            self._entries.move_to_end(key)
            return result.model_copy(deep=True)

    def set(self, key: QueryCacheKey, result: _Result) -> None:
        """Store a defensive copy of a successful query result."""

        with self._lock:
            if not self._enabled:
                return
            self._entries[key] = result.model_copy(deep=True)
            self._entries.move_to_end(key)
            self._evict_to_limit()

    def clear(self, *, reset_metrics: bool = False) -> None:
        """Clear cached data, optionally resetting counters for isolated tests."""

        with self._lock:
            self._entries.clear()
            if reset_metrics:
                self._hits = self._misses = self._evictions = 0

    def stats(self) -> QueryCacheStats:
        """Return path-free cache counters and configuration."""

        with self._lock:
            return QueryCacheStats(
                enabled=self._enabled,
                max_entries=self._max_entries,
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
                current_entries=len(self._entries),
            )

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    @staticmethod
    def _validate_max_entries(max_entries: int) -> None:
        if type(max_entries) is not int or max_entries < 1:
            raise ValueError("max_entries must be a positive integer.")

    def _evict_to_limit(self) -> None:
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)
            self._evictions += 1
