"""Metric registry + Prometheus exposition (K0, frozen L0 spec 05 §3.3).

`build_registry(specs)` instantiates every declared `MetricSpec` family once.
When prometheus_client is absent every handle is the silent `_NoOp` (the
shipped fallback, preserved verbatim from `disbot/services/metrics.py`), so
callers never guard metric calls individually. `render()` produces the
Prometheus text exposition for the `/metrics` route (mounted at K5).
"""

from __future__ import annotations

from collections.abc import Iterable

from sb.spec.observability import METRICS, MetricKind, MetricSpec

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

try:
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised via the _NoOp path in CI
    PROMETHEUS_AVAILABLE = False


class _NoOp:
    """Silent no-op that accepts any label access or observation call."""

    def labels(self, **_: object) -> "_NoOp":
        return self

    def inc(self, *_: object, **__: object) -> None:
        pass

    def observe(self, *_: object, **__: object) -> None:
        pass

    def set(self, *_: object, **__: object) -> None:
        pass


class MetricRegistry:
    """Typed handle lookup over the instantiated families (spec 05 §3.3)."""

    def __init__(self) -> None:
        self._handles: dict[str, tuple[MetricKind, object]] = {}
        self._collector = CollectorRegistry() if PROMETHEUS_AVAILABLE else None

    def _add(self, spec: MetricSpec, handle: object) -> None:
        if spec.name in self._handles:
            raise ValueError(f"duplicate metric family: {spec.name}")
        self._handles[spec.name] = (spec.kind, handle)

    def _get(self, name: str, kind: MetricKind) -> object:
        actual_kind, handle = self._handles[name]
        if actual_kind is not kind:
            raise KeyError(f"{name} is a {actual_kind.value}, not a {kind.value}")
        return handle

    def counter(self, name: str) -> object:
        return self._get(name, MetricKind.COUNTER)

    def gauge(self, name: str) -> object:
        return self._get(name, MetricKind.GAUGE)

    def histogram(self, name: str) -> object:
        return self._get(name, MetricKind.HISTOGRAM)


_ACTIVE: MetricRegistry | None = None


def build_registry(specs: Iterable[MetricSpec] = METRICS) -> MetricRegistry:
    """Instantiate every declared family once.

    When prometheus_client is absent, every handle is the silent _NoOp.
    Duplicate name => ValueError at build.
    """
    global _ACTIVE
    registry = MetricRegistry()
    for spec in specs:
        if not PROMETHEUS_AVAILABLE:
            registry._add(spec, _NoOp())
            continue
        labelnames = [label.name for label in spec.labels]
        kwargs: dict[str, object] = {"registry": registry._collector}
        if spec.kind is MetricKind.COUNTER:
            handle = Counter(spec.name, spec.doc, labelnames, **kwargs)
        elif spec.kind is MetricKind.GAUGE:
            handle = Gauge(spec.name, spec.doc, labelnames, **kwargs)
        else:
            handle = Histogram(spec.name, spec.doc, labelnames,
                               buckets=spec.buckets, **kwargs)
        registry._add(spec, handle)
    _ACTIVE = registry
    return registry


def active_registry() -> MetricRegistry | None:
    """The registry the last build_registry() produced, or None before boot.

    Emitters below the composition root (e.g. the K3 DB seam's
    db_query_seconds observation) read handles through this instead of
    holding a registry reference; observability never blocks the seam.
    """
    return _ACTIVE


def render() -> tuple[bytes, str]:
    """(body, content_type) for the /metrics adapter (spec 05 §3.8).

    When prometheus_client is absent (or no registry was built), returns an
    empty body with the same content type — the _NoOp registry has nothing
    to emit.
    """
    if not PROMETHEUS_AVAILABLE or _ACTIVE is None or _ACTIVE._collector is None:
        return b"", CONTENT_TYPE
    return generate_latest(_ACTIVE._collector), CONTENT_TYPE
