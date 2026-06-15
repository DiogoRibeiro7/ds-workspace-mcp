from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ds_workspace_mcp.core import profile_csv_dataset
from ds_workspace_mcp.tracing import configure_tracing


def write_dataset(root: Path, name: str = "sample.csv") -> Path:
    """Create a small CSV dataset for tracing tests."""

    path = root / name
    pd.DataFrame({"feature": [1, 2, 3], "target": [4, 5, 6]}).to_csv(path, index=False)
    return path


def test_profile_csv_dataset_works_with_tracing_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    write_dataset(tmp_path)

    profile = profile_csv_dataset("sample.csv")

    assert profile.row_count == 3


def test_profile_csv_dataset_works_with_tracing_enabled_without_optional_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_TRACING_ENABLED", "true")
    write_dataset(tmp_path)
    monkeypatch.setattr("ds_workspace_mcp.tracing._load_opentelemetry", lambda: None)

    configure_tracing()
    profile = profile_csv_dataset("sample.csv")

    assert profile.row_count == 3


def test_profile_csv_dataset_uses_fake_tracer_when_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("MCP_TRACING_ENABLED", "true")
    monkeypatch.setenv("MCP_TRACING_CONSOLE_EXPORTER", "true")
    write_dataset(tmp_path)

    started_spans: list[str] = []

    class FakeSpan:
        def __enter__(self) -> FakeSpan:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        def set_attribute(self, key: str, value: object) -> None:
            return None

        def record_exception(self, exc: Exception) -> None:
            return None

    class FakeTracer:
        def start_as_current_span(self, name: str) -> FakeSpan:
            started_spans.append(name)
            return FakeSpan()

    class FakeTraceModule:
        def __init__(self) -> None:
            self.provider: object | None = None

        def set_tracer_provider(self, provider: object) -> None:
            self.provider = provider

        def get_tracer(self, name: str) -> FakeTracer:
            return FakeTracer()

    class FakeResource:
        @staticmethod
        def create(attributes: dict[str, object]) -> dict[str, object]:
            return attributes

    class FakeTracerProvider:
        def __init__(self, resource: object) -> None:
            self.resource = resource
            self.processors: list[object] = []

        def add_span_processor(self, processor: object) -> None:
            self.processors.append(processor)

    class FakeBatchSpanProcessor:
        def __init__(self, exporter: object) -> None:
            self.exporter = exporter

    class FakeConsoleSpanExporter:
        pass

    fake_trace_module = FakeTraceModule()
    monkeypatch.setattr(
        "ds_workspace_mcp.tracing._load_opentelemetry",
        lambda: (
            fake_trace_module,
            FakeResource,
            FakeTracerProvider,
            FakeBatchSpanProcessor,
            FakeConsoleSpanExporter,
        ),
    )

    configure_tracing()
    profile = profile_csv_dataset("sample.csv")

    assert profile.row_count == 3
    assert "dataset.profile" in started_spans
    assert "dataset.resolve" in started_spans
    assert fake_trace_module.provider is not None
