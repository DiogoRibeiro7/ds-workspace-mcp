from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.cache import ProfileCache, ProfileCacheConfig, ProfileCacheKey
from ds_workspace_mcp.core import profile_cache, profile_csv_dataset
from ds_workspace_mcp.profiling import DatasetProfile, ProfilingLimits


def write_cached_dataset(
    root: Path,
    name: str = "cache.csv",
    values: list[int] | None = None,
) -> Path:
    """Create a dataset that can be mutated across cache tests."""

    path = root / name
    data = values if values is not None else [1, 2, 3]
    pd.DataFrame({"value": data, "category": ["a", "b", "c"][: len(data)]}).to_csv(
        path,
        index=False,
    )
    return path


def make_cache_key(
    root: Path,
    name: str,
    size: int = 1,
    modified_time_ns: int = 1,
) -> ProfileCacheKey:
    return ProfileCacheKey(
        path=root / name,
        file_size=size,
        modified_time_ns=modified_time_ns,
        max_categorical_values=10,
    )


def make_profile(name: str) -> DatasetProfile:
    return DatasetProfile(
        file_name=name,
        row_count=1,
        column_count=1,
        columns=["value"],
        dtypes={"value": "int64"},
        missing_values={"value": 0},
        missing_percentage={"value": 0.0},
        profiling_limits=ProfilingLimits(max_categorical_values=10),
    )


def test_profile_cache_reuses_cached_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_cached_dataset(tmp_path)

    first_profile = profile_csv_dataset("cache.csv")
    second_profile = profile_csv_dataset("cache.csv")

    assert first_profile is second_profile
    assert len(profile_cache) == 1


def test_profile_cache_invalidates_on_modified_time_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    dataset_path = write_cached_dataset(tmp_path)

    first_profile = profile_csv_dataset("cache.csv")
    dataset_path.write_text("value,category\n1,a\n2,b\n3,c\n4,d\n", encoding="utf-8")
    second_profile = profile_csv_dataset("cache.csv")

    assert first_profile is not second_profile
    assert second_profile.row_count == 4


def test_profile_cache_invalidates_on_file_size_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    dataset_path = write_cached_dataset(tmp_path)

    first_profile = profile_csv_dataset("cache.csv")
    dataset_path.write_text("value,category\n10,a\n20,b\n30,c\n1000,z\n", encoding="utf-8")
    second_profile = profile_csv_dataset("cache.csv")

    assert first_profile is not second_profile
    assert second_profile.numeric_columns[0].max == 1000.0


def test_profile_cache_can_be_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_PROFILE_CACHE_ENABLED", "false")
    write_cached_dataset(tmp_path)

    first_profile = profile_csv_dataset("cache.csv")
    second_profile = profile_csv_dataset("cache.csv")

    assert first_profile is not second_profile
    assert len(profile_cache) == 0


def test_profile_cache_respects_max_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_PROFILE_CACHE_MAX_ENTRIES", "1")
    write_cached_dataset(tmp_path, name="a.csv", values=[1])
    write_cached_dataset(tmp_path, name="b.csv", values=[2])

    profile_csv_dataset("a.csv")
    assert len(profile_cache) == 1

    profile_csv_dataset("b.csv")
    assert len(profile_cache) == 1


def test_profile_cache_exposes_path_free_stats(tmp_path: Path) -> None:
    cache = ProfileCache(enabled=True, max_entries=2)
    key = make_cache_key(tmp_path, "private.csv")

    assert cache.get(key) is None
    cache.set(key, make_profile("private.csv"))
    assert cache.get(key) is not None

    stats = cache.stats()

    assert stats.hits == 1
    assert stats.misses == 1
    assert stats.evictions == 0
    assert stats.current_entries == 1
    assert str(tmp_path) not in repr(stats)


def test_profile_cache_lru_eviction_is_explicit(tmp_path: Path) -> None:
    cache = ProfileCache(enabled=True, max_entries=2)
    first_key = make_cache_key(tmp_path, "first.csv")
    second_key = make_cache_key(tmp_path, "second.csv")
    third_key = make_cache_key(tmp_path, "third.csv")

    cache.set(first_key, make_profile("first.csv"))
    cache.set(second_key, make_profile("second.csv"))
    assert cache.get(first_key) is not None
    cache.set(third_key, make_profile("third.csv"))

    assert cache.get(second_key) is None
    assert cache.get(first_key) is not None
    assert cache.get(third_key) is not None
    assert cache.stats().evictions == 1


def test_profile_cache_configuration_trims_entries_and_can_disable(tmp_path: Path) -> None:
    cache = ProfileCache(enabled=True, max_entries=3)
    first_key = make_cache_key(tmp_path, "first.csv")
    second_key = make_cache_key(tmp_path, "second.csv")
    third_key = make_cache_key(tmp_path, "third.csv")
    for key in (first_key, second_key, third_key):
        cache.set(key, make_profile(key.path.name))

    cache.configure(ProfileCacheConfig(enabled=True, max_entries=1))

    assert len(cache) == 1
    assert cache.stats().evictions == 2

    cache.configure(enabled=False)

    assert len(cache) == 0
    assert cache.stats().enabled is False


def test_profile_cache_invalidate_removes_one_entry(tmp_path: Path) -> None:
    cache = ProfileCache(enabled=True, max_entries=2)
    key = make_cache_key(tmp_path, "cache.csv")

    cache.set(key, make_profile("cache.csv"))

    assert cache.invalidate(key) is True
    assert cache.invalidate(key) is False
    assert len(cache) == 0


def test_profile_cache_concurrent_access_cannot_corrupt_state(tmp_path: Path) -> None:
    cache = ProfileCache(enabled=True, max_entries=8)
    keys = [make_cache_key(tmp_path, f"{index}.csv", size=index + 1) for index in range(24)]

    def touch_cache(index: int) -> None:
        key = keys[index % len(keys)]
        cache.configure(enabled=True, max_entries=8)
        cache.set(key, make_profile(key.path.name))
        cache.get(key)
        if index % 5 == 0:
            cache.invalidate(keys[(index + 1) % len(keys)])

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(touch_cache, range(200)))

    stats = cache.stats()
    assert stats.current_entries <= stats.max_entries
    assert stats.hits > 0
    assert stats.evictions > 0
