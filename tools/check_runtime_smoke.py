#!/usr/bin/env python3
"""check_runtime_smoke — the ORDER 016 headless boot-and-wire merge gate.

Static checks pass while WIRING breaks slip through ("locally correct,
systemically wrong"): a manifest that declares a ref nobody registers, a
panel route that dispatches into an empty registry, a bus subscriber armed
on a typo'd event name, a durable event delivered to nobody. This gate
performs the cheap first tier of an actual boot — no token, no guild, no
DB, no network — and asserts the registry + EventBus subscription graph is
intact. It rides the SAME composition-root code paths as ``sb.app.main``
(and its side-effect-free twin ``sb.app.verify_boot``), never a parallel
re-implementation:

  1. boot-gate leg A (``gate_recompile`` against the committed snapshot) —
     the exact main.py step 3 / verify_boot stage 2 call; this is ALSO the
     path that imports every ``sb.manifest`` module and runs the
     ``ENSURE_REFS`` re-arm hooks, so the ref table is populated the same
     way a real boot populates it.
  2. ``load_live_manifests()`` — the composition root's own loader (step 7).
  3. ``build_runtime`` + ``install_live_target_index`` — the dispatch-index
     realization (step 7, D-0028(2)).
  4. ``register_manifest_panels`` + ``install_panel_runtime`` — the panel
     wiring (step 8; headless branch: the presenter is left uninstalled
     when discord is absent — panel_host's own contract).
  5. ``EventBus()`` + ``arm_subscribe_roster(bus)`` — the REAL subscription
     graph the live boot arms (step 16).

The wiring-graph assertions (each numbered W-rule prints as
``W<n> <locus>: <detail>`` on red):

  W1 ref-graph      — every ref reachable from every live manifest resolves
                      through ``sb.spec.refs.resolve`` to a real callable
                      (the RUNTIME twin of compile P2's ``is_registered``:
                      P2 proves table membership at compile; W1 proves the
                      live boot's own load order produces a resolvable
                      callable for each).
  W2 panel-graph    — every PanelRef names a panel_id REGISTERED in the
                      panel registry after ``register_manifest_panels`` (the
                      band-1 replay's exact LookupError class).
  W3 subscriber     — every ``bus.on()`` subscription the roster armed names
                      a KNOWN_EVENTS event (no orphan/typo'd listeners) and
                      binds a real callable.
  W4 durable        — every AT_LEAST_ONCE event has >=1 live subscriber
                      (a durable event delivered to nobody is broken wiring,
                      not observability).
  W5 declared subs  — every ``EventSpec.expected_subscribers`` ref resolves
                      AND its event has >=1 live subscriber.
  W6 emit-sites     — a static AST scan over ``sb/`` for ``*.emit(...)``
                      call sites whose event name is a string literal or a
                      same-module module-level string constant: every such
                      name must be in KNOWN_EVENTS (an emit nobody declared
                      is a dead wire or a typo).

HONEST COVERAGE BOUNDARY (no fake coverage claims):
  - Emit sites with DYNAMIC names (the outbox relay re-emitting stored
    rows, ``enqueue_all``'s spec-driven names, the parity taps) are not
    statically enumerable; they are runtime-guarded by the enqueue
    name-guard against KNOWN_EVENTS instead. W6 covers literal/constant
    call sites only.
  - "Every emit has its expected subscriber" is asserted through W4+W5:
    a BEST_EFFORT event with no declared ``expected_subscribers`` may
    legitimately have zero listeners (§2.8 — observability events are
    fire-and-forget by design), so zero-subscriber best-effort events are
    NOT red. As of this writing no manifest declares
    ``expected_subscribers``, so W5 binds future declarations.
  - Nothing is DISPATCHED end-to-end (no command exercised): this is the
    boot-and-wire tier; the dispatch-tier live-boot job is the order's
    named follow-up.

Runs green with only ``pyyaml`` installed (guarded-import discipline) —
the same environment as ci.yml's ``checkers`` job and named-gates.yml's
``manifest-validate`` gate, which both run it per PR.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_SNAPSHOT = "manifest.snapshot.json"
_REPO_ROOT = Path(__file__).resolve().parent.parent


class GraphBus:
    """An EventBus-compatible recorder: real ``on``/``subscribers`` shape,
    plus enumeration of the armed graph for the W-rules."""

    def __init__(self) -> None:
        self._handlers: dict[str, list] = {}

    def on(self, event_name: str, handler) -> None:
        self._handlers.setdefault(event_name, []).append(handler)

    def subscribers(self, event_name: str) -> tuple:
        return tuple(self._handlers.get(event_name, ()))

    def subscribed_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))


# --- the pure W-rules (unit-testable against synthetic wiring) ------------------


def unresolved_manifest_refs(manifests: list, *, resolver, walk_refs,
                             skip_predicate) -> list[str]:
    """W1: every reachable ref resolves to a callable."""
    problems: list[str] = []
    seen: set[tuple[str, str]] = set()
    for m in manifests:
        key = getattr(m, "key", "?")
        for ref, _owner in walk_refs(m):
            ident = (ref.kind, ref.name)
            if ident in seen:
                continue
            seen.add(ident)
            if skip_predicate(ref):
                continue
            try:
                fn = resolver(ref)
            except Exception as exc:  # noqa: BLE001 — the finding IS the report
                problems.append(f"W1 {key}: {ref.kind}:{ref.name} — {exc}")
                continue
            if not callable(fn):
                problems.append(
                    f"W1 {key}: {ref.kind}:{ref.name} resolved to a "
                    f"non-callable {type(fn).__name__}")
    return problems


def unregistered_panel_refs(manifests: list, *, get_panel, walk_refs) -> list[str]:
    """W2: every PanelRef names a registered panel_id."""
    problems: list[str] = []
    seen: set[str] = set()
    for m in manifests:
        key = getattr(m, "key", "?")
        for ref, _owner in walk_refs(m):
            if getattr(ref, "kind", None) != "panel" or ref.name in seen:
                continue
            seen.add(ref.name)
            try:
                get_panel(ref.name)
            except LookupError:
                problems.append(
                    f"W2 {key}: panel:{ref.name} routed but NOT in the panel "
                    "registry (the band-1 LookupError class)")
    return problems


def orphan_subscriptions(bus: GraphBus, known_events: dict) -> list[str]:
    """W3: every armed subscription names a KNOWN_EVENTS event + a callable."""
    problems: list[str] = []
    for name in bus.subscribed_names():
        if name not in known_events:
            problems.append(
                f"W3 bus: subscriber armed on {name!r} which is NOT in "
                "KNOWN_EVENTS (typo'd or undeclared event)")
        for handler in bus.subscribers(name):
            if not callable(handler):
                problems.append(
                    f"W3 bus: non-callable subscriber on {name!r}: "
                    f"{type(handler).__name__}")
    return problems


def undelivered_durable_events(bus: GraphBus, known_events: dict) -> list[str]:
    """W4: every AT_LEAST_ONCE event has >=1 live subscriber."""
    problems: list[str] = []
    for name, spec in sorted(known_events.items()):
        delivery = getattr(getattr(spec, "delivery", None), "value", None)
        if delivery == "at_least_once" and not bus.subscribers(name):
            problems.append(
                f"W4 {name}: AT_LEAST_ONCE event has ZERO live subscribers "
                "(durable delivery to nobody)")
    return problems


def unmet_expected_subscribers(bus: GraphBus, known_events: dict, *,
                               resolver) -> list[str]:
    """W5: every declared expected_subscribers ref resolves; its event has
    >=1 live subscriber."""
    problems: list[str] = []
    for name, spec in sorted(known_events.items()):
        expected = getattr(spec, "expected_subscribers", ()) or ()
        if not expected:
            continue
        for ref in expected:
            try:
                resolver(ref)
            except Exception as exc:  # noqa: BLE001
                problems.append(
                    f"W5 {name}: expected subscriber "
                    f"{getattr(ref, 'kind', '?')}:{getattr(ref, 'name', ref)} "
                    f"does not resolve — {exc}")
        if not bus.subscribers(name):
            problems.append(
                f"W5 {name}: declares expected_subscribers but has ZERO "
                "live subscribers on the armed bus")
    return problems


def unknown_emit_names(emit_sites: list[tuple[str, int, str]],
                       known_events: dict) -> list[str]:
    """W6: every statically-enumerable emitted name is a declared event."""
    return [
        f"W6 {path}:{line}: emits {name!r} which is NOT in KNOWN_EVENTS"
        for path, line, name in emit_sites
        if name not in known_events
    ]


# --- the static emit-site scan (W6 input) ---------------------------------------


def _module_str_constants(tree: ast.Module) -> dict[str, str]:
    consts: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    consts[target.id] = node.value.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None \
                and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str) \
                and isinstance(node.target, ast.Name):
            consts[node.target.id] = node.value.value
    return consts


def scan_emit_sites(root: Path) -> list[tuple[str, int, str]]:
    """Every ``<expr>.emit(<name>, ...)`` call under ``root`` whose first
    positional argument is a string literal or a module-level string
    constant of the SAME module. Dynamic names are skipped by construction
    (the documented boundary)."""
    sites: list[tuple[str, int, str]] = []
    for py in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue  # not this gate's finding — the import legs own it
        consts = _module_str_constants(tree)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "emit" and node.args):
                continue
            first = node.args[0]
            name: str | None = None
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                name = first.value
            elif isinstance(first, ast.Name):
                name = consts.get(first.id)
            if name is not None:
                try:
                    rel = py.relative_to(root.parent)
                except ValueError:
                    rel = py
                sites.append((str(rel), node.lineno, name))
    return sites


# --- the real-plugin boot proof (ORDER 002 game-plugin contract) ----------------


def plugin_boot_problems(host_manifests: list) -> list[str]:
    """Boot the IN-TREE exemplar (``examples/superbot-plugin-hello``) headless
    against the COMMITTED ``plugins.lock.json`` pin — the real ``load_plugins``
    call ``sb.app.main`` step 9b makes, minus a pip install.

    Static-green-but-boot-broken is exactly this gate's remit, and a plugin
    is the sharpest case: the in-tree corpus can be statically perfect while
    the committed pin has drifted from the real manifest (a spec facet grew
    without a re-pin), so the one external plugin the host ships cannot boot
    against its own lock. This proves entry-point discovery + the committed
    pin verify + the v1 facet fence + the joint host+plugin compile all admit
    the real manifest, and that its declared panel registers.

    The entry point is CONSTRUCTED (its ``.load()`` imports the real module —
    import == ref registration): the exemplar is in-tree, not a pip-installed
    dist, so this stays hermetic (no install, no network — the same
    pyyaml-only environment the rest of the gate runs in). Called AFTER the
    in-tree W-rules so the plugin's refs never leak into leg-A's corpus hash
    (the main.py step-9b ordering: plugins load after the host is armed)."""
    import importlib

    exemplar = _REPO_ROOT / "examples" / "superbot-plugin-hello"
    if not (exemplar / "superbot_plugin_hello" / "manifest.py").exists():
        return []  # exemplar absent from this checkout — nothing to prove
    if str(exemplar) not in sys.path:
        sys.path.insert(0, str(exemplar))

    from sb.app import plugin_host
    from sb.app.panel_host import register_manifest_panels
    from sb.kernel.panels.registry import get_panel

    module_name = "superbot_plugin_hello.manifest"
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 — the finding IS the report
        return [f"plugin-boot: exemplar import failed — {exc!r}"]
    ensure = getattr(module, "ENSURE_REFS", None)
    if callable(ensure):
        ensure()  # re-arm the plugin's own refs (the host re-arm skips plugins)

    class _Dist:
        name = "superbot-plugin-hello"
        version = "0.1.0"

    class _EntryPoint:
        name = "hello"
        value = module_name
        dist = _Dist()

        def load(self):
            return importlib.import_module(module_name)

    pins = plugin_host.read_pins(_REPO_ROOT / plugin_host.PINS_FILENAME)
    report = plugin_host.load_plugins(
        host_manifests, pins=pins, entry_points=(_EntryPoint(),))
    if report.violations:
        return [f"plugin-boot: {v}" for v in report.violations]
    if not any(getattr(m, "key", None) == "hello" for m in report.manifests):
        return ["plugin-boot: the exemplar admitted 0 manifests "
                "(expected the 'hello' subsystem)"]
    register_manifest_panels(list(report.manifests))
    try:
        get_panel("hello.home")
    except LookupError:
        return ["plugin-boot: hello.home is declared by the exemplar but NOT "
                "registered after register_manifest_panels (the band-1 "
                "LookupError class)"]
    return []


# --- the headless boot (the I/O shell) -------------------------------------------


def run_smoke(snapshot_path: Path) -> list[str]:
    """The headless boot-and-wire sequence + all W-rules. Returns problems."""
    import json

    problems: list[str] = []

    # 1. boot-gate leg A — imports every manifest + ENSURE_REFS (main step 3).
    from sb.app.boot_gate import gate_recompile

    committed = json.loads(snapshot_path.read_text(encoding="utf-8"))
    violations = gate_recompile(committed)
    if violations:
        return [f"boot-gate leg A: {v}" for v in violations]

    # 2..4. the composition root's own loaders/wiring (steps 7-8).
    from sb.app.build_runtime import build_runtime, install_live_target_index
    from sb.app.main import arm_subscribe_roster, load_live_manifests
    from sb.app.panel_host import install_panel_runtime, register_manifest_panels

    build_runtime(committed)
    manifests = load_live_manifests()
    index_size = install_live_target_index(manifests)
    panel_count = register_manifest_panels(manifests)
    install_panel_runtime()

    # 5. the subscription graph (step 16), on a recorder with the bus shape.
    bus = GraphBus()
    armed = arm_subscribe_roster(bus)

    from sb.kernel.panels.registry import get_panel
    from sb.spec.events import KNOWN_EVENTS
    from sb.spec.refs import PredicateRef, is_namespaced_predicate, resolve
    from tools.manifest_compile import _walk_refs

    def _skip(ref) -> bool:
        return isinstance(ref, PredicateRef) and (
            ref.name == "" or is_namespaced_predicate(ref))

    problems += unresolved_manifest_refs(
        manifests, resolver=resolve, walk_refs=_walk_refs, skip_predicate=_skip)
    problems += unregistered_panel_refs(
        manifests, get_panel=get_panel, walk_refs=_walk_refs)
    problems += orphan_subscriptions(bus, KNOWN_EVENTS)
    problems += undelivered_durable_events(bus, KNOWN_EVENTS)
    problems += unmet_expected_subscribers(bus, KNOWN_EVENTS, resolver=resolve)
    emit_sites = scan_emit_sites(_REPO_ROOT / "sb")
    problems += unknown_emit_names(emit_sites, KNOWN_EVENTS)

    # 6. the real-plugin boot (main.py step 9b) — AFTER the in-tree wiring so
    #    the plugin's refs never leak into leg-A's corpus hash.
    plugin_problems = plugin_boot_problems(manifests)
    problems += plugin_problems

    if not problems:
        print(f"check_runtime_smoke: clean — {len(manifests)} manifest(s), "
              f"{index_size} dispatch target(s), {panel_count} panel(s), "
              f"{len(armed)} roster module(s), "
              f"{len(bus.subscribed_names())} subscribed event name(s), "
              f"{len(emit_sites)} static emit site(s), "
              f"{len(KNOWN_EVENTS)} declared event(s), "
              "+1 real plugin exemplar (hello) booted against its pin")
    return problems


def main(argv: list[str]) -> int:
    snapshot_path = Path(argv[1]) if len(argv) > 1 else _REPO_ROOT / DEFAULT_SNAPSHOT
    if not snapshot_path.exists():
        print(f"check_runtime_smoke: {snapshot_path} absent — dormant until "
              "the compiler emits the committed snapshot.")
        return 0
    problems = run_smoke(snapshot_path)
    for p in problems:
        print(p)
    if problems:
        print(f"check_runtime_smoke: {len(problems)} wiring problem(s)",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
