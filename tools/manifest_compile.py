#!/usr/bin/env python3
"""The manifest compiler (K2 — THE LINCHPIN; frozen L0 spec 01 §3.2-§3.5, §5).

`compile_manifests()` runs 9 dependency-ordered passes over the declared
manifests and emits `manifest.snapshot.json` — the committed interchange
artifact the entire kernel and port order sit behind. Order is load-bearing;
within a pass, collect ALL violations; at a pass boundary, fail fast.

  P1 load                — import sb.manifest.*, collect manifests, populate the ref table
  P2 ref_resolution      — every {"$ref"} registered; namespaced predicates well-formed
  --  _project           — the violation-free snapshot-body build (pure data for P3/P4/P6/P7)
  P3 namespace           — K1's ONE oracle `validate(snapshot)` (RC-7: P3 IS spec 03's validate)
  P3b app_tree           — slash root command name must not equal a subcommand-group name
                           (discord.py CommandAlreadyRegistered, Finding #3 / PR #370; joint set)
  P4 authority           — validate_authority_ref over authority_ref fields (ARMS AT K6/S7)
  P5 role_tag            — every spec field tagged exactly one of [S]/[A]/[O]
  P6 semantic            — the six predicates (never_strand, destructive_confirmation,
                           external_cost, leaderboard_writer, audit_completeness,
                           action_cooldown_parity)
  P7 store_completeness  — dropped StoreSpec needs an owner-signed retirement (ARMS AT K3;
                           baseline None => every store `added`, no drop possible)
  P8 serialize           — canonical JSON + layout-lock overlays ([A]-only) + stable_hash
  P9 recompile_parity    — recompiled stable_hash == committed BODY's recomputed hash
                           (leg A / DRIFT)

Hash membership (spec 01 §5, fork 9): the hashed body EXCLUDES `stable_hash`,
`compiler_version`, `manifest_count`; INCLUDES `schema_version`, `field_roles`,
`subsystems`, `projections`.

The committed file does NOT carry a `stable_hash` field: because hash
membership excludes it, the value is purely derivable from the rest of the
file, and the cached line re-conflicted any two concurrent PRs that both
recompiled the snapshot (PRs #333/#352 class — runbook:
docs/operations/manifest-snapshot-conflicts.md). P9 recomputes the committed
body's hash on the fly via `compute_stable_hash`, which ignores the field if
a legacy snapshot still carries it — drift detection is unchanged.

Never imported at runtime (tools/ layer); `sb/app/boot_gate.py` wraps it for
boot leg-A.
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib
import json
import pkgutil
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sb.namespace import validate as namespace_validate  # noqa: E402
from sb.spec.refs import (  # noqa: E402
    AnyRef,
    EngineRef,
    HandlerRef,
    PanelRef,
    PredicateRef,
    ProviderRef,
    ViewRef,
    WorkflowRef,
    is_namespaced_predicate,
    is_registered,
    parse_namespaced_predicate,
    ref_inventory,
)
from sb.spec.roles import field_role, snapshot_field_roles  # noqa: E402

COMPILER_VERSION = "1.0.0"
SCHEMA_VERSION = 1
SNAPSHOT_FILENAME = "manifest.snapshot.json"
LAYOUT_LOCK_DIR = "sb/manifest/layout"
STORE_RETIREMENTS_PATH = "sb/namespace/store_retirements.yml"

# --- the failure taxonomy (spec 01 §3.5) -------------------------------------
COMPILE_ERROR = "COMPILE_ERROR"
COLLISION = "COLLISION"
CAP_VIOLATION = "CAP_VIOLATION"
FORMAT_ERROR = "FORMAT_ERROR"
SEMANTIC_VIOLATION = "SEMANTIC_VIOLATION"
STORE_DROP = "STORE_DROP"
DRIFT = "DRIFT"
BUILD_MISMATCH = "BUILD_MISMATCH"   # leg B (boot only; arms at K8)
REMOTE_LAG = "REMOTE_LAG"           # leg C (boot only, non-fatal; arms at K8)

FAILURE_CLASSES = (
    COMPILE_ERROR, COLLISION, CAP_VIOLATION, FORMAT_ERROR, SEMANTIC_VIOLATION,
    STORE_DROP, DRIFT, BUILD_MISMATCH, REMOTE_LAG,
)

_REF_TYPES = (HandlerRef, PanelRef, ViewRef, PredicateRef, EngineRef, WorkflowRef, ProviderRef)


@dataclass(frozen=True)
class Violation:
    pass_name: str
    failure_class: str                 # a taxonomy constant above
    subsystem: str | None
    locus: str                         # id / "Type.field" / "file:line"
    detail: str
    scope: str | None = None           # COLLISION on a command: "surface/parent_group"
    claimant_a: str | None = None
    claimant_b: str | None = None


@dataclass(frozen=True)
class CompileResult:
    ok: bool
    snapshot: dict | None              # None if a pre-serialize pass failed
    stable_hash: str | None
    violations: tuple[Violation, ...]


# --- serialization helpers -----------------------------------------------------

def canonical_json(body: object) -> str:
    """Determinism contract (spec 01 §5): sorted keys, tight separators, UTF-8."""
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_stable_hash(snapshot: dict) -> str:
    """sha256 over the canonical JSON of the snapshot minus the excluded keys."""
    hashed_body = {
        k: v for k, v in snapshot.items()
        if k not in ("stable_hash", "compiler_version", "manifest_count")
    }
    digest = hashlib.sha256(canonical_json(hashed_body).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _serialize(value: object) -> object:
    """Spec-object -> pure data. *Ref -> {"$ref": "kind:name"}; the namespaced
    PredicateRef form -> the plain string (spec 01 §3.1)."""
    if isinstance(value, PredicateRef) and is_namespaced_predicate(value):
        return value.name
    if isinstance(value, _REF_TYPES):
        return {"$ref": f"{value.kind}:{value.name}"}
    if isinstance(value, Enum):
        return value.value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            f.name: _serialize(getattr(value, f.name))
            for f in dataclasses.fields(value)
        }
    if isinstance(value, dict):
        return {str(k): _serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_serialize(v) for v in value)
    if callable(value):
        # callables are forbidden in specs (§2.0: callable -> registered-ref);
        # surfaced as a marker the P2 walk turns into a COMPILE_ERROR.
        return {"$callable": getattr(value, "__qualname__", repr(value))}
    return value


def _walk_spec_objects(value: object):
    """Yield every dataclass spec object reachable from a manifest facet.

    *Ref value objects are NOT spec types (they serialize to {"$ref": ...},
    P2 owns their validity) — excluded from the P4/P5/P6 spec walk."""
    if isinstance(value, _REF_TYPES):
        return
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        yield value
        for f in dataclasses.fields(value):
            yield from _walk_spec_objects(getattr(value, f.name))
    elif isinstance(value, (list, tuple, set, frozenset)):
        for v in value:
            yield from _walk_spec_objects(v)
    elif isinstance(value, dict):
        for v in value.values():
            yield from _walk_spec_objects(v)


def _walk_refs(value: object):
    """Yield (ref, owner_spec) for every *Ref reachable from `value`."""
    if isinstance(value, _REF_TYPES):
        yield value, None
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        for f in dataclasses.fields(value):
            child = getattr(value, f.name)
            if isinstance(child, _REF_TYPES):
                yield child, value
            else:
                yield from _walk_refs(child)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for v in value:
            yield from _walk_refs(v)
    elif isinstance(value, dict):
        for v in value.values():
            yield from _walk_refs(v)


def _spec_name(obj: object) -> str:
    return type(obj).__name__


def _get(obj: object, field: str, default: object = None) -> object:
    return getattr(obj, field, default)


def _handler_accepts_reserved_keys(sub_ref: object) -> bool:
    """delivery_declared rule 3 (spec 08 §3.1/§6.3): an AT_LEAST_ONCE event's
    expected subscriber must be able to receive the reserved `_outbox_*`
    delivery kwargs — `**kwargs` or an explicit `_outbox_dedup_key` param.
    An unregistered/unresolvable ref is skipped here (P2 owns unresolved-ref
    verdicts); only a RESOLVABLE handler with a closed signature reds."""
    import inspect

    from sb.spec.refs import is_registered, resolve
    try:
        if not is_registered(sub_ref):
            return True
        fn = resolve(sub_ref)
        sig = inspect.signature(fn)
    except Exception:  # noqa: BLE001 — best-effort arm
        return True
    for param in sig.parameters.values():
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            return True
        if param.name == "_outbox_dedup_key":
            return True
    return False


# --- P0: grammar import ------------------------------------------------------------

def _import_spec_grammar(violations: list[Violation]) -> None:
    """Import every sb.spec module BEFORE projecting, so each grammar type's
    `register_field_roles` side effects are visible to the snapshot's
    `field_roles` section regardless of which facets the loaded manifests
    happen to touch (P5 registration is at type-definition site; the snapshot
    must be import-order independent). Mirrors check_schema_growth."""
    import sb.spec as spec_pkg

    for info in sorted(pkgutil.iter_modules(spec_pkg.__path__), key=lambda i: i.name):
        module_name = f"sb.spec.{info.name}"
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # noqa: BLE001 — a broken grammar leaf is a compile verdict
            violations.append(Violation("load", COMPILE_ERROR, None, module_name,
                                        f"spec grammar import raised: {exc!r}"))


# --- P1: load --------------------------------------------------------------------

def _p1_load(manifest_pkg: str, injected: list | None,
             violations: list[Violation]) -> list:
    manifests: list = []
    if injected is not None:
        manifests = list(injected)
    else:
        try:
            pkg = importlib.import_module(manifest_pkg)
        except Exception as exc:  # noqa: BLE001 — every import failure is a P1 verdict
            violations.append(Violation("load", COMPILE_ERROR, None, manifest_pkg,
                                        f"manifest package import raised: {exc!r}"))
            return manifests
        search_paths = getattr(pkg, "__path__", [])
        for info in sorted(pkgutil.iter_modules(search_paths), key=lambda i: i.name):
            module_name = f"{manifest_pkg}.{info.name}"
            try:
                module = importlib.import_module(module_name)
            except Exception as exc:  # noqa: BLE001 — incl. RefRedefined dup binding
                violations.append(Violation("load", COMPILE_ERROR, info.name, module_name,
                                            f"manifest import raised: {exc!r}"))
                continue
            declared = getattr(module, "MANIFEST", None)
            if declared is not None:
                manifests.append(declared)
            for extra in getattr(module, "MANIFESTS", ()):
                manifests.append(extra)
            # Band-1 (D-0025): optional re-arm hook. Ref/handler decorators
            # run at first import only; the test seam clear_ref_table()
            # empties the table without evicting module caches, so a module
            # may expose ENSURE_REFS() to idempotently re-register its refs
            # before P2 resolves them.
            hook = getattr(module, "ENSURE_REFS", None)
            if callable(hook):
                try:
                    hook()
                except Exception as exc:  # noqa: BLE001 - a P1 verdict, not a crash
                    violations.append(Violation(
                        "load", COMPILE_ERROR, info.name, module_name,
                        f"ENSURE_REFS raised: {exc!r}"))
    seen: dict[str, str] = {}
    for m in manifests:
        key = _get(m, "key")
        if not isinstance(key, str) or not key:
            violations.append(Violation("load", COMPILE_ERROR, None, repr(m),
                                        "manifest has no subsystem key"))
            continue
        if key in seen:
            violations.append(Violation("load", COMPILE_ERROR, key, key,
                                        "duplicate subsystem key declared twice"))
        seen[key] = key
    return manifests


# --- P2: ref resolution ------------------------------------------------------------

def _p2_ref_resolution(manifests: list, violations: list[Violation]) -> None:
    for m in manifests:
        key = _get(m, "key", "?")
        for ref, owner in _walk_refs(m):
            locus = f"{_spec_name(owner) if owner else 'manifest'} in {key}"
            if isinstance(ref, PredicateRef):
                if ref.name == "":
                    continue  # constant-true namespaced form
                if is_namespaced_predicate(ref):
                    try:
                        parse_namespaced_predicate(ref.name)
                    except ValueError as exc:
                        violations.append(Violation("ref_resolution", COMPILE_ERROR, key,
                                                    locus, f"bad_predicate: {exc}"))
                    continue
                if ":" in ref.name:
                    violations.append(Violation(
                        "ref_resolution", COMPILE_ERROR, key, locus,
                        f"bad_predicate: head not in namespaced-kind set: {ref.name!r}"))
                    continue
            if not is_registered(ref):
                violations.append(Violation("ref_resolution", COMPILE_ERROR, key, locus,
                                            f"unresolved_ref: {ref.kind}:{ref.name}"))


# --- _project: the violation-free snapshot-body build --------------------------------

def _project(manifests: list) -> dict:
    subsystems: dict[str, object] = {}
    ns_command: list[dict] = []
    ns_by_kind: dict[str, list[dict]] = {}
    stores_proj: dict[str, dict] = {}
    events_proj: dict[str, dict] = {}

    def _ns(kind: str, value: str, subsystem: str, source: str) -> None:
        ns_by_kind.setdefault(kind, []).append(
            {"value": value, "subsystem": subsystem, "source": source})

    for m in sorted(manifests, key=lambda m: _get(m, "key", "")):
        key = str(_get(m, "key"))
        subsystems[key] = _serialize(m)
        source = f"sb/manifest/{key}.py"
        _ns("subsystem_key", key, key, source)

        for cmd in _get(m, "commands", ()) or ():
            name = _get(cmd, "name")
            if not name:
                continue
            kind_field = _get(cmd, "surface", None) or _get(cmd, "kind", "both")
            surfaces = ["prefix", "slash"] if kind_field == "both" else [str(kind_field)]
            parent = _get(cmd, "group", None) or _get(cmd, "parent_group", None)
            for surface in surfaces:
                ns_command.append({
                    "value": str(name), "kind": "command", "surface": surface,
                    "parent_group": parent, "subsystem": key, "source": source,
                })

        for panel_spec in _get(m, "panels", ()) or ():
            panel_id = _get(panel_spec, "panel_id", None) or _get(panel_spec, "id", None)
            if panel_id:
                _ns("panel", str(panel_id), key, source)
            for action in _get(panel_spec, "actions", ()) or ():
                action_id = _get(action, "action_id", None)
                if action_id:
                    _ns("custom_id", str(action_id), key, source)

        for setting in _get(m, "settings", ()) or ():
            setting_key = _get(setting, "key", None)
            if setting_key:
                _ns("setting_key", str(setting_key), key, source)

        for store in _get(m, "stores", ()) or ():
            table = _get(store, "table", None)
            if not table:
                continue
            _ns("table", str(table), key, source)
            sole_writer = _get(store, "sole_writer", None)
            stores_proj[str(table)] = {
                "sole_writer": _serialize(sole_writer),
                "checkpoint_class": _serialize(_get(store, "checkpoint_class", None)),
                "invariant_tag": _serialize(_get(store, "invariant_tag", None)),
                "subsystem": key,
            }

        for event in _get(m, "events", ()) or ():
            name = _get(event, "name", None) or (event if isinstance(event, str) else None)
            if not name:
                continue
            _ns("event", str(name), key, source)
            delivery = _get(event, "delivery", None)
            events_proj[str(name)] = {
                "owner_subsystem": key,
                "observability_only": bool(_get(event, "observability_only", False)),
                "delivery": getattr(delivery, "value", delivery) or "best_effort",
            }

        for cap in _get(m, "capabilities", ()) or ():
            cap_value = _get(cap, "name", None) or (cap if isinstance(cap, str) else None)
            if cap_value:
                _ns("capability", str(cap_value), key, source)

    namespace_proj: dict[str, list] = {"command": ns_command}
    namespace_proj.update(ns_by_kind)
    return {
        "schema_version": SCHEMA_VERSION,
        "field_roles": snapshot_field_roles(),
        "subsystems": subsystems,
        "projections": {
            "namespace": namespace_proj,
            "stores": stores_proj,
            "events": events_proj,
            "refs": ref_inventory(),
        },
    }


# --- P3: namespace (K1's one oracle — RC-7) ------------------------------------------

def _p3_namespace(snapshot: dict, violations: list[Violation]) -> None:
    report = namespace_validate(snapshot)
    for c in report.collisions:
        scope = None
        if c.scope is not None:
            scope = f"{c.scope.surface.value}/{c.scope.parent_group or ''}"
        violations.append(Violation(
            "namespace", COLLISION, None, f"{c.kind.value}:{c.value}",
            c.detail or "two claimants of one (kind, value, scope)",
            scope=scope, claimant_a=c.claimant_a, claimant_b=c.claimant_b))
    for v in report.cap_violations:
        violations.append(Violation(
            "namespace", CAP_VIOLATION, None, v.locus or "<global>",
            f"{v.cap}: {v.count} > {v.limit} ({', '.join(v.members[:8])}...)"))
    for f in report.format_errors:
        violations.append(Violation(
            "namespace", FORMAT_ERROR, None, f"{f.kind.value}:{f.value}", f.detail))


# --- P3b: app-command tree shape (root/group name collision) --------------------------

def _p3b_app_tree(snapshot: dict, violations: list[Violation]) -> None:
    """Reject the ONE app-command-tree shape discord.py rejects at live boot
    but every static gate missed until now (Finding #3, PR #370): a
    slash-capable ROOT command whose name equals a subcommand-GROUP name in
    the SAME registered manifest set.

    ``sb/adapters/discord/command_tree.py::register_app_commands`` (verified
    at :107-:120) adds, for every LIVE ``CommandSpec`` with
    ``kind in ("slash","both")``, either a root ``app_commands.Command(name)``
    when ``group==""`` (``tree.add_command`` at :120) or — via ``_group_for``
    (:89-:102) — a top-level ``app_commands.Group(name=parts[0])`` for a
    grouped one (``tree.add_command`` at :101). discord.py's ``tree`` keeps ONE
    top-level namespace, so a Command and a Group claiming the same name raise
    ``CommandAlreadyRegistered`` the moment the second is added — a crash only
    a live boot surfaced.

    This models that condition EXACTLY, off the joint projection (so a plugin
    command colliding with a host name is caught in the ``load_plugins`` joint
    compile too):
      * a leaf registers ONLY when slash-capable — projected ``surface ==
        "slash"`` (``kind`` "slash" or the slash half of "both"); a PREFIX-only
        node is filtered out, so a ``kind=PREFIX`` root named X + group X is
        NOT flagged (the shape the #86 idle fix relies on, and the G-6
        ``!karma``/``/karma`` coexistence in-tree);
      * a ROOT is ``parent_group`` None/"" (``group==""``);
      * a top-level GROUP is ``parent_group.split(".")[0]`` of a slash leaf —
        groups are born ONLY from slash-capable commands, mirroring
        ``_group_for`` (a group holding only prefix leaves never registers a
        ``Group`` node, so it never collides).
    """
    command_nodes = (
        (snapshot.get("projections") or {}).get("namespace") or {}
    ).get("command") or []
    roots: dict[str, str] = {}         # slash root name -> first-claiming subsystem
    top_groups: dict[str, str] = {}    # top-level slash group name -> first-claiming subsystem
    for node in command_nodes:
        if node.get("surface") != "slash":
            continue
        subsystem = str(node.get("subsystem", "?"))
        parent = node.get("parent_group")
        if parent in (None, ""):
            roots.setdefault(str(node.get("value", "")), subsystem)
        else:
            top_groups.setdefault(str(parent).split(".")[0], subsystem)
    for name in sorted(set(roots) & set(top_groups)):
        violations.append(Violation(
            "app_tree", COLLISION, None, f"command:{name}",
            f"slash_root_group_collision: slash-capable root command {name!r} "
            f"shares its name with subcommand group {name!r} — discord.py's "
            "tree.add_command raises CommandAlreadyRegistered at live startup "
            "(register_app_commands adds both a root Command and a top-level "
            "Group under this name). Make the root command kind=prefix "
            "(PREFIX-only never registers as an app command) or rename one.",
            scope="slash/",
            claimant_a=roots[name], claimant_b=top_groups[name]))


# --- P4: authority (arms at K6/S7) ----------------------------------------------------

def _p4_authority(manifests: list, violations: list[Violation]) -> None:
    try:
        from sb.spec.authority import validate_authority_ref  # noqa: PLC0415 — armed-later seam
    except ImportError:
        return  # dormant until K6/S7 lands sb/spec/authority.py (spec 01 §11)
    for m in manifests:
        key = _get(m, "key", "?")
        for spec in _walk_spec_objects(m):
            ref = _get(spec, "authority_ref", None)
            if ref is None:
                continue
            try:
                validate_authority_ref(ref)  # "" is ALWAYS valid (ADMIN-floor carve-out)
            except Exception as exc:  # noqa: BLE001 — BadAuthorityError by contract
                violations.append(Violation(
                    "authority", COMPILE_ERROR, str(key),
                    f"{_spec_name(spec)}.authority_ref", f"bad_authority: {exc}"))


# --- P5: role_tag -----------------------------------------------------------------------

def _p5_role_tag(manifests: list, violations: list[Violation]) -> None:
    reported: set[str] = set()
    for m in manifests:
        key = _get(m, "key", "?")
        for spec in _walk_spec_objects(m):
            type_name = _spec_name(spec)
            for f in dataclasses.fields(spec):
                locus = f"{type_name}.{f.name}"
                if locus in reported:
                    continue
                if field_role(type_name, f.name) is None:
                    reported.add(locus)
                    violations.append(Violation(
                        "role_tag", COMPILE_ERROR, str(key), locus,
                        "untagged_field: not registered as exactly one of [S]/[A]/[O]"))


# --- P6: the six semantic predicates ------------------------------------------------------

def _p6_semantic(manifests: list, violations: list[Violation]) -> None:
    def flag(subsystem: str, locus: str, detail: str) -> None:
        violations.append(Violation("semantic", SEMANTIC_VIOLATION, subsystem, locus, detail))

    for m in manifests:
        key = str(_get(m, "key", "?"))
        commands = list(_get(m, "commands", ()) or ())
        panels = list(_get(m, "panels", ()) or ())

        # -- never_strand --------------------------------------------------------
        for cmd in commands:
            route = _get(cmd, "route", None)
            # WorkflowRef is admitted: it is the audited routable kind
            # audit_completeness REQUIRES for effect="mutating" commands.
            if route is not None and not isinstance(route, (PanelRef, HandlerRef, WorkflowRef)):
                flag(key, f"CommandSpec:{_get(cmd, 'name')}",
                     "never_strand: route must resolve to a PanelRef/justified "
                     "HandlerRef/WorkflowRef")

        # -- modal_ingress (G-10 on the command facet — CommandSpec.modal) --------
        # The panel-side G-10 fences (sb/kernel/panels/compile.py _check_modal +
        # the defer_mode pairing) re-proved for the COMMAND declaring surface,
        # plus the two command-only rules: SLASH-only (a prefix message carries
        # no interaction response slot — the shipped ingress class was
        # app-command-only, ORACLE cogs/btd6/_unified.py strat_submit_slash)
        # and a dispatchable SUBMIT route (the modal re-entry dispatches the
        # command's own route on surface=MODAL; a PanelRef there is a stranded
        # form, and None dead-ends in the no-routable-ref envelope).
        for cmd in commands:
            name = _get(cmd, "name", "?")
            locus = f"CommandSpec:{name}"
            modal = _get(cmd, "modal", None)
            defer = _get(cmd, "defer_mode", None)
            defer_token = getattr(defer, "value", defer)
            if modal is None:
                if defer_token == "modal":
                    flag(key, locus,
                         "modal_ingress: defer_mode=modal requires a ModalSpec (G-10)")
                continue
            kind_field = _get(cmd, "surface", None) or _get(cmd, "kind", "both")
            if str(kind_field) != "slash":
                flag(key, locus,
                     "modal_ingress: a modal-opening command must be kind=slash "
                     "(a prefix message has no interaction response slot)")
            if defer_token != "modal":
                flag(key, locus,
                     "modal_ingress: a declared modal requires defer_mode=modal "
                     "(the open is the ACK — G-10)")
            route = _get(cmd, "route", None)
            if not isinstance(route, (HandlerRef, WorkflowRef)):
                flag(key, locus,
                     "modal_ingress: the submit re-entry dispatches the command's "
                     "route — declare a HandlerRef/WorkflowRef (never a PanelRef)")
            fields = list(_get(modal, "fields", ()) or ())
            if not 1 <= len(fields) <= 5:
                flag(key, locus,
                     f"modal_ingress: ModalSpec {_get(modal, 'modal_id', '?')!r} has "
                     f"{len(fields)} fields (Discord allows 1..5)")
            field_ids = [str(_get(f, "field_id", "")) for f in fields]
            if len(set(field_ids)) != len(field_ids):
                flag(key, locus,
                     f"modal_ingress: ModalSpec {_get(modal, 'modal_id', '?')!r} "
                     "has duplicate field_ids")
            if not _get(modal, "modal_id", None):
                flag(key, locus, "modal_ingress: ModalSpec.modal_id is required "
                     "(the custom-id root routes the submit)")
        declared_actions: dict[str, object] = {}
        declared_selectors: set[str] = set()
        for panel_spec in panels:
            pid = _get(panel_spec, "panel_id", None) or _get(panel_spec, "id", "?")
            if _get(panel_spec, "navigation", None) is None:
                flag(key, f"PanelSpec:{pid}", "never_strand: panel has no NavigationSpec")
            for action in _get(panel_spec, "actions", ()) or ():
                action_id = _get(action, "action_id", None)
                if action_id:
                    declared_actions[str(action_id)] = action
            for selector in _get(panel_spec, "selectors", ()) or ():
                selector_id = _get(selector, "selector_id", None)
                if selector_id:
                    declared_selectors.add(str(selector_id))
        bound_counts: dict[str, int] = {}
        for panel_spec in panels:
            pid = _get(panel_spec, "panel_id", None) or _get(panel_spec, "id", "?")
            comps = _get(panel_spec, "components", None)
            if comps is not None:
                # duck-typed component tables (pre-layout fixture shape).
                for comp in comps or ():
                    target = _get(comp, "action_id", None) or _get(comp, "selector_id", None)
                    if target is None:
                        continue
                    if str(target) not in declared_actions:
                        flag(key, f"PanelSpec:{pid}",
                             f"never_strand: component targets undeclared action {target!r}")
                    else:
                        bound_counts[str(target)] = bound_counts.get(str(target), 0) + 1
                continue
            # the real grammar (panel-action slice, D-0034): placement IS
            # PanelSpec.layout — the ONE arrangement structure. A placed id
            # binds its action; selector ids are their own declared
            # population (registration's layout-coverage fence already
            # guarantees exhaustive+exclusive placement; this predicate
            # re-proves it manifest-side, arrangement-independent).
            layout = _get(panel_spec, "layout", None)
            for page in (_get(layout, "pages", ()) or ()):
                for row in (_get(page, "rows", ()) or ()):
                    for target in row or ():
                        target = str(target)
                        if target in declared_actions:
                            bound_counts[target] = bound_counts.get(target, 0) + 1
                        elif target not in declared_selectors:
                            flag(key, f"PanelSpec:{pid}",
                                 f"never_strand: component targets undeclared "
                                 f"action {target!r}")
        for action_id in declared_actions:
            n = bound_counts.get(action_id, 0)
            if n != 1:
                flag(key, f"PanelActionSpec:{action_id}",
                     f"never_strand: action bound by {n} components (must be exactly 1)")

        # -- the four field-driven predicates over every reachable spec -----------
        stat_writers: set[str] = set()
        for store in _get(m, "stores", ()) or ():
            stat_key = _get(store, "stat_key", None)
            if stat_key:
                stat_writers.add(str(stat_key))
        for spec in _walk_spec_objects(m):
            name = _spec_name(spec)
            locus = f"{name}:{_get(spec, 'name', None) or _get(spec, 'action_id', None) or '?'}"

            if _get(spec, "destructive", False):
                confirm = _get(spec, "confirm", None)
                if confirm is None:
                    flag(key, locus, "destructive_confirmation: destructive without ConfirmationSpec")
                reversibility = str(_get(spec, "reversibility", "") or "").upper()
                if reversibility == "IRREVERSIBLE" and (
                    confirm is None or not _get(confirm, "typed_challenge", None)
                ):
                    flag(key, locus,
                         "destructive_confirmation: irreversible requires a typed challenge")

            if _get(spec, "external_side_effects", False):
                if not _get(spec, "off_until_opt_in", False):
                    flag(key, locus, "external_cost: external_side_effects requires off_until_opt_in")
                if _get(spec, "spend_counter", None) is None and hasattr(spec, "spend_counter"):
                    flag(key, locus, "external_cost: media/external spec declares no spend_counter")

            if name == "LeaderboardSpec":
                stat_key = _get(spec, "stat_key", None)
                if stat_key and str(stat_key) not in stat_writers:
                    flag(key, locus,
                         f"leaderboard_writer: stat_key {stat_key!r} has no declared writer")

            effect = _get(spec, "effect", None)
            if effect == "mutating":
                ref_kinds = {r.kind for r, _o in _walk_refs(spec)}
                if "workflow" not in ref_kinds:
                    flag(key, locus,
                         "audit_completeness: mutating spec must route through a WorkflowRef")

            # -- delivery_declared (spec 08 §3.1 — additive fence, K4) -----------
            # Duck-typed on the `delivery` field (the compiler reads NAMED
            # declared fields, never class names — spec 01 facet-growth rule).
            delivery = _get(spec, "delivery", None)
            if delivery is not None:
                delivery_token = getattr(delivery, "value", delivery)
                if _get(spec, "observability_only", False) and \
                        delivery_token == "at_least_once":
                    flag(key, locus,
                         "delivery_declared: observability_only event cannot be "
                         "AT_LEAST_ONCE (telemetry is never guaranteed-delivered)")
                if delivery_token == "at_least_once":
                    if not (_get(m, "stores", ()) or ()):
                        flag(key, locus,
                             "delivery_declared: AT_LEAST_ONCE event whose "
                             "owner_subsystem writes no store the relay can reach")
                    for sub_ref in _get(spec, "expected_subscribers", ()) or ():
                        if not _handler_accepts_reserved_keys(sub_ref):
                            flag(key, locus,
                                 "delivery_declared: effectful subscriber "
                                 f"{getattr(sub_ref, 'name', sub_ref)!r} cannot receive "
                                 "the reserved _outbox_* delivery keys "
                                 "(declare **kwargs or an explicit _outbox_dedup_key)")

            if name == "PanelActionSpec" and effect == "mutating":
                mirrors = _get(spec, "mirrors", None)
                if _get(spec, "cooldown", None) is None:
                    flag(key, locus, "action_cooldown_parity: mutating panel action has no cooldown")
                if mirrors is not None:
                    mirrored = next((c for c in commands if _get(c, "name") == mirrors), None)
                    if mirrored is None:
                        flag(key, locus,
                             f"action_cooldown_parity: mirrors unknown command {mirrors!r}")
                    elif _get(mirrored, "cooldown", None) != _get(spec, "cooldown", None):
                        flag(key, locus,
                             "action_cooldown_parity: cooldown differs from mirrored command")


# --- P7: store completeness (arms at K3) ---------------------------------------------------

def _load_retirements(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        import yaml  # noqa: PLC0415 — optional dependency, tools-only
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except ImportError:
        return {}
    return {row["table"]: row for row in doc.get("retirements", []) if "table" in row}


def _p7_store_completeness(snapshot: dict, baseline_snapshot: dict | None,
                           violations: list[Violation],
                           retirements_path: str = STORE_RETIREMENTS_PATH) -> None:
    if baseline_snapshot is None:
        return  # first compile / arming: every store is `added`, no drop possible
    baseline_stores = set((baseline_snapshot.get("projections") or {}).get("stores") or {})
    current_stores = set(snapshot["projections"]["stores"])
    dropped = baseline_stores - current_stores
    if not dropped:
        return
    retirements = _load_retirements(_REPO_ROOT / retirements_path)
    for table in sorted(dropped):
        row = retirements.get(table)
        if row is None:
            violations.append(Violation(
                "store_completeness", STORE_DROP, None, table,
                "store present in baseline, absent now, with NO signed retirement "
                "(needs owner sign-off in sb/namespace/store_retirements.yml)"))
        elif row.get("disposition") not in ("export", "reverse-migrate", "declared-loss"):
            violations.append(Violation(
                "store_completeness", STORE_DROP, None, table,
                "signed retirement lacks a REQUIRED disposition "
                "(export | reverse-migrate | declared-loss — no default, spec 01 fork 8)"))


# --- P8: serialize (+ layout locks) ----------------------------------------------------------

def _find_overlay_node(snapshot: dict, instance_id: str) -> dict | None:
    """Locate the serialized node whose id field equals `instance_id`."""
    def search(node: object) -> dict | None:
        if isinstance(node, dict):
            for id_field in ("panel_id", "action_id", "id", "key"):
                if node.get(id_field) == instance_id:
                    return node
            for v in node.values():
                found = search(v)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for v in node:
                found = search(v)
                if found is not None:
                    return found
        return None
    return search(snapshot["subsystems"])


def _p8_serialize(snapshot: dict, violations: list[Violation],
                  layout_dir: str = LAYOUT_LOCK_DIR) -> None:
    lock_dir = _REPO_ROOT / layout_dir
    if not lock_dir.is_dir():
        return
    for lock_path in sorted(lock_dir.glob("*.lock.json")):
        entries = json.loads(lock_path.read_text(encoding="utf-8"))
        if isinstance(entries, dict):
            entries = entries.get("overlays", [])
        for entry in entries:
            target = entry.get("target", "")
            field = entry.get("field", "")
            type_name, _sep, instance_id = target.partition(":")
            role = field_role(type_name, field)
            if role is None or role.value != "A":
                violations.append(Violation(
                    "serialize", COMPILE_ERROR, None, f"{type_name}.{field}",
                    f"illegal_overlay_key: role is {role.value if role else 'untagged'}, "
                    "overlays may touch [A]-tagged fields only"))
                continue
            node = _find_overlay_node(snapshot, instance_id)
            if node is None:
                violations.append(Violation(
                    "serialize", COMPILE_ERROR, None, target,
                    "illegal_overlay_key: overlay target not found in snapshot"))
                continue
            node[field] = entry.get("arrangement")


# --- the pipeline ------------------------------------------------------------------------------

def compile_manifests(
    manifest_pkg: str = "sb.manifest",
    *,
    baseline_snapshot: dict | None = None,     # previous committed snapshot, for P7
    committed_snapshot: dict | None = None,    # committed file, for P9 / leg A
    manifests: list | None = None,             # library/test injection (bypasses package walk)
) -> CompileResult:
    violations: list[Violation] = []

    _import_spec_grammar(violations)                          # P0: role registration side effects
    if violations:
        return CompileResult(False, None, None, tuple(violations))

    loaded = _p1_load(manifest_pkg, manifests, violations)   # P1
    if violations:
        return CompileResult(False, None, None, tuple(violations))

    _p2_ref_resolution(loaded, violations)                    # P2
    if violations:
        return CompileResult(False, None, None, tuple(violations))

    snapshot = _project(loaded)                               # (internal, violation-free)

    _p3_namespace(snapshot, violations)                       # P3
    _p3b_app_tree(snapshot, violations)                       # P3b (app-command tree shape)
    if violations:
        return CompileResult(False, None, None, tuple(violations))

    _p4_authority(loaded, violations)                         # P4 (arms at K6)
    if violations:
        return CompileResult(False, None, None, tuple(violations))

    _p5_role_tag(loaded, violations)                          # P5
    if violations:
        return CompileResult(False, None, None, tuple(violations))

    _p6_semantic(loaded, violations)                          # P6
    if violations:
        return CompileResult(False, None, None, tuple(violations))

    _p7_store_completeness(snapshot, baseline_snapshot, violations)   # P7 (arms at K3)
    if violations:
        return CompileResult(False, None, None, tuple(violations))

    _p8_serialize(snapshot, violations)                       # P8
    if violations:
        return CompileResult(False, None, None, tuple(violations))

    stable_hash = compute_stable_hash(snapshot)
    full_snapshot = {
        "schema_version": snapshot["schema_version"],
        "compiler_version": COMPILER_VERSION,
        "manifest_count": len(snapshot["subsystems"]),
        "field_roles": snapshot["field_roles"],
        "subsystems": snapshot["subsystems"],
        "projections": snapshot["projections"],
    }

    if committed_snapshot is not None:                        # P9 (leg A)
        # Recompute from the committed BODY (the file carries no stable_hash
        # field; compute_stable_hash ignores one on legacy snapshots).
        committed_hash = compute_stable_hash(committed_snapshot)
        if committed_hash != stable_hash:
            violations.append(Violation(
                "recompile_parity", DRIFT, None, SNAPSHOT_FILENAME,
                f"recompiled {stable_hash} != committed {committed_hash} — recompile & commit"))

    ok = not violations
    return CompileResult(ok, full_snapshot, stable_hash, tuple(violations))


def serialize_manifest(manifest: object) -> object:
    """Public: one manifest → pure data (the P8 ``_serialize`` mechanics),
    for out-of-tree manifest pinning (``sb/app/plugin_host.py``)."""
    return _serialize(manifest)


def render_snapshot(snapshot: dict) -> str:
    """The committed-file rendering: canonical body, human-diffable indentation."""
    return json.dumps(snapshot, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="SuperBot manifest compiler (K2).")
    parser.add_argument("--write", action="store_true",
                        help="write manifest.snapshot.json (else verify against it, P9)")
    parser.add_argument("--snapshot", default=str(_REPO_ROOT / SNAPSHOT_FILENAME))
    args = parser.parse_args(argv)

    snapshot_path = Path(args.snapshot)
    committed = None
    if snapshot_path.exists() and not args.write:
        committed = json.loads(snapshot_path.read_text(encoding="utf-8"))
    baseline = committed  # CI: the previous committed snapshot is the P7 baseline

    result = compile_manifests(baseline_snapshot=baseline, committed_snapshot=committed)
    for v in result.violations:
        claimants = f" [{v.claimant_a} vs {v.claimant_b}]" if v.claimant_a else ""
        scope = f" scope={v.scope}" if v.scope else ""
        print(f"{v.failure_class} ({v.pass_name}) {v.locus}{scope}: {v.detail}{claimants}")
    if not result.ok:
        print(f"manifest_compile: {len(result.violations)} violation(s)", file=sys.stderr)
        return 1
    if args.write:
        snapshot_path.write_text(render_snapshot(result.snapshot), encoding="utf-8")
        print(f"manifest_compile: wrote {snapshot_path} ({result.stable_hash})")
    else:
        print(f"manifest_compile: green ({result.stable_hash}, "
              f"{result.snapshot['manifest_count']} manifest(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
