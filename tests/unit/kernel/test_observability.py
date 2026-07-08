"""Unit checks for the metric grammar + registry (K0/S1, spec 05 §3.3)."""

import pytest

from sb.kernel.observability.metrics import CONTENT_TYPE, build_registry, render
from sb.spec.observability import METRICS, LabelSpec, MetricKind, MetricSpec


def test_label_spec_requires_exactly_one_bound():
    with pytest.raises(ValueError):
        LabelSpec("unbounded")  # neither domain nor max_cardinality
    with pytest.raises(ValueError):
        LabelSpec("both", domain=("a",), max_cardinality=5)
    assert LabelSpec("dom", domain=("a", "b")).cardinality == 2
    assert LabelSpec("bound", max_cardinality=7).cardinality == 7


def test_histogram_requires_buckets():
    with pytest.raises(ValueError):
        MetricSpec(name="h", kind=MetricKind.HISTOGRAM, doc="d")


def test_metrics_registry_is_declared_clean():
    """The committed METRICS tuple passes its own CI gate."""
    from tools.check_metric_cardinality import check

    assert check(METRICS) == []


def test_metrics_family_count_and_uniqueness():
    names = [m.name for m in METRICS]
    assert len(names) == len(set(names))
    assert len(names) == 46  # verbatim from shipped disbot/services/metrics.py


def test_build_registry_and_render():
    registry = build_registry()
    counter = registry.counter("command_total")
    counter.labels(cog="economy", command="give", result="success").inc()
    gauge = registry.gauge("session_active_count")
    gauge.set(3)
    histogram = registry.histogram("db_query_seconds")
    histogram.labels(query_name="select:xp").observe(0.01)
    body, content_type = render()
    assert content_type == CONTENT_TYPE
    assert isinstance(body, bytes)


def test_registry_kind_mismatch_raises():
    registry = build_registry()
    with pytest.raises(KeyError):
        registry.counter("session_active_count")  # it is a gauge


def test_duplicate_family_raises():
    spec = METRICS[0]
    with pytest.raises(ValueError):
        build_registry((spec, spec))
