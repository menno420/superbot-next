#!/usr/bin/env python3
"""check_metric_cardinality — the label-cardinality budget gate (K0 CI gate).

Frozen L0 spec 05 §3.3: for every HISTOGRAM a non-empty `buckets`; for every
labelled family a `cardinality_budget > 0` and the product over labels of
L.cardinality <= cardinality_budget, where L.cardinality = len(L.domain) when
a domain is declared else L.max_cardinality. A label with neither is CI-red
(the unbounded-label class). Duplicate family names are CI-red too.

Exit 0 = clean; exit 1 = violations.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sb.spec.observability import METRICS, MetricKind, MetricSpec  # noqa: E402


def check(specs: tuple[MetricSpec, ...] = METRICS) -> list[str]:
    violations: list[str] = []
    seen: set[str] = set()
    for spec in specs:
        if spec.name in seen:
            violations.append(f"{spec.name}: duplicate metric family name")
        seen.add(spec.name)
        if spec.kind is MetricKind.HISTOGRAM and not spec.buckets:
            violations.append(f"{spec.name}: HISTOGRAM with empty buckets")
        if spec.labels:
            if spec.cardinality_budget <= 0:
                violations.append(f"{spec.name}: labelled family with no cardinality_budget")
                continue
            product = 1
            for label in spec.labels:
                if label.cardinality <= 0:
                    violations.append(
                        f"{spec.name}: label {label.name!r} has neither domain "
                        "nor max_cardinality (unbounded)"
                    )
                product *= max(label.cardinality, 1)
            if product > spec.cardinality_budget:
                violations.append(
                    f"{spec.name}: label-cardinality product {product} exceeds "
                    f"budget {spec.cardinality_budget}"
                )
    return violations


def main() -> int:
    violations = check()
    for line in violations:
        print(line)
    if violations:
        print(f"check_metric_cardinality: {len(violations)} violation(s)", file=sys.stderr)
        return 1
    print(f"check_metric_cardinality: clean ({len(METRICS)} families)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
