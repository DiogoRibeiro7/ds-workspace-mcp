from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.core import profile_cache, profile_csv_dataset


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
