from __future__ import annotations

import importlib
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from ds_workspace_mcp.config import Settings, get_settings

logger = logging.getLogger(__name__)

TraceAttribute = str | bool | int | float


@dataclass
class _TracingState:
    """Mutable runtime state for optional tracing."""

    configured: bool = False
    tracer: Any | None = None
    warning_emitted: bool = False


@dataclass
class TraceHandle:
    """Handle for setting optional span attributes inside an operation."""

    span: Any | None = None

    def set_attribute(self, key: str, value: object) -> None:
        """Set a span attribute when tracing is active."""

        if self.span is None:
            return
        normalized = _normalize_attribute(value)
        if normalized is not None:
            self.span.set_attribute(key, normalized)


_STATE = _TracingState()


def configure_tracing(settings: Settings | None = None) -> None:
    """Configure OpenTelemetry tracing if it is enabled and available."""

    if _STATE.configured:
        return

    runtime_settings = settings or get_settings()
    _STATE.configured = True

    if not runtime_settings.mcp_tracing_enabled:
        return

    modules = _load_opentelemetry()
    if modules is None:
        if not _STATE.warning_emitted:
            logger.warning(
                "Tracing is enabled but OpenTelemetry dependencies are not installed. "
                "Install the `opentelemetry` Poetry extra to enable spans."
            )
            _STATE.warning_emitted = True
        return

    (
        trace_module,
        resource_cls,
        tracer_provider_cls,
        span_processor_cls,
        console_exporter_cls,
    ) = modules
    provider = tracer_provider_cls(
        resource=resource_cls.create({"service.name": runtime_settings.mcp_tracing_service_name})
    )

    if runtime_settings.mcp_tracing_console_exporter:
        provider.add_span_processor(span_processor_cls(console_exporter_cls()))

    trace_module.set_tracer_provider(provider)
    _STATE.tracer = trace_module.get_tracer(runtime_settings.mcp_tracing_service_name)


@contextmanager
def traced_operation(
    name: str,
    attributes: dict[str, object] | None = None,
) -> Iterator[TraceHandle]:
    """Run a block inside an optional tracing span."""

    if not _STATE.configured:
        configure_tracing()

    tracer = _STATE.tracer
    if tracer is None:
        yield TraceHandle()
        return

    with tracer.start_as_current_span(name) as span:
        handle = TraceHandle(span=span)
        for key, value in (attributes or {}).items():
            handle.set_attribute(key, value)

        try:
            yield handle
        except Exception as exc:
            span.record_exception(exc)
            raise


def reset_tracing_state() -> None:
    """Reset tracing runtime state for tests."""

    _STATE.configured = False
    _STATE.tracer = None
    _STATE.warning_emitted = False


def _normalize_attribute(value: object) -> TraceAttribute | None:
    """Normalize span attributes to simple scalar values."""

    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float | str):
        return value
    return str(value)


def _load_opentelemetry() -> tuple[Any, Any, Any, Any, Any] | None:
    """Import OpenTelemetry modules lazily."""

    try:
        trace_module = importlib.import_module("opentelemetry.trace")
        resources_module = importlib.import_module("opentelemetry.sdk.resources")
        sdk_trace_module = importlib.import_module("opentelemetry.sdk.trace")
        export_module = importlib.import_module("opentelemetry.sdk.trace.export")
    except ImportError:
        return None

    return (
        trace_module,
        resources_module.Resource,
        sdk_trace_module.TracerProvider,
        export_module.BatchSpanProcessor,
        export_module.ConsoleSpanExporter,
    )
