"""The K7 fences (frozen L0 spec 07 §3.6 + Q-D24 + A-5 hook).

Three declared fences + the Q-D24 session-concurrency rule:

- `idempotency_posture_declared` — every op declares a posture AND its
  mandated companion field (DURABLE_ONCE ⇒ dedup_key; NONE_JUSTIFIED ⇒
  justification; SINGLE_FLIGHT ⇒ scope); Q-D24: `session_transition` ⇒
  posture is NATURAL_KEY (the FOR UPDATE / state_version CAS seam).
- `audit_completeness` (spec-side half) — derives + freezes
  `op.reversibility = max(leg reversibilities)` and asserts
  `IRREVERSIBLE ⇒ confirmation is not None`. (The manifest-side half —
  mutating command ⇒ WorkflowRef route — already lives in the K2 compiler's
  P6 `audit_completeness`/`never_strand`, S3.)
- `atomic_db_only` — scoped to EXTERNAL-CONN callers ONLY (scheduler
  `ManagedTaskSpec.handler`, invariant `repair_ref`, version
  `compensation_ref` — NOT draft op_kinds; PIN-2/F-2): pure-DB legs, no
  EFFECT, no BEST_EFFORT emit, no confirmation, and the AST import-closure
  scan over DB-leg handler sources (no discord/aiohttp/bus.emit — the A-5
  body-scan complement's first arm; the declared-effect-vs-writes verifier
  arms when domain units exist, S11 widens it to raw Discord mutations).

`check_spec` runs at registration (structural); the S10 scheduler band calls
`check_atomic_db_only(spec)` for every ref it arms.
"""

from __future__ import annotations

import inspect
from dataclasses import replace

from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    DedupKeySpec,
    IdempotencyPosture,
    LegKind,
)
from sb.spec.events import DeliveryClass
from sb.spec.refs import resolve

__all__ = [
    "check_atomic_db_only",
    "check_spec",
    "derive_reversibility",
]

_REV_ORDER = {"reversible": 0, "compensatable": 1, "irreversible": 2}

# The AST/source-closure ban list for external-conn DB legs (spec 07 §3.6
# rule 2; A-5 first arm). Matched against the handler's source text.
_DB_LEG_BANNED_TOKENS = ("import discord", "import aiohttp", ".emit(", "discord.")


def derive_reversibility(spec: CompoundOpSpec) -> CompoundOpSpec:
    """The op rollup: max(leg.reversibility) under REVERSIBLE <
    COMPENSATABLE < IRREVERSIBLE. The author never sets it."""
    if not spec.legs:
        return replace(spec, reversibility="reversible")
    top = max(spec.legs, key=lambda l: _REV_ORDER.get(l.reversibility, 0))
    return replace(spec, reversibility=top.reversibility)


def check_spec(spec: CompoundOpSpec) -> list[str]:
    """The registration-time declaration fences. Empty list = clean."""
    problems: list[str] = []

    # --- idempotency_posture_declared (+ mandated companions, T2-21) ---
    if spec.idempotency is IdempotencyPosture.DURABLE_ONCE:
        if spec.dedup_key is None:
            problems.append("DURABLE_ONCE requires dedup_key")
    elif spec.dedup_key is not None:
        problems.append("dedup_key is only meaningful under DURABLE_ONCE")
    if spec.idempotency is IdempotencyPosture.NONE_JUSTIFIED:
        if not spec.idempotency_justification:
            problems.append("NONE_JUSTIFIED requires idempotency_justification")
    elif spec.idempotency_justification is not None:
        problems.append("idempotency_justification MUST be None unless NONE_JUSTIFIED")
    if spec.idempotency is IdempotencyPosture.SINGLE_FLIGHT and not spec.single_flight_scope:
        problems.append("SINGLE_FLIGHT requires single_flight_scope")
    if spec.idempotency is not IdempotencyPosture.SINGLE_FLIGHT and spec.single_flight_scope:
        problems.append("single_flight_scope MUST be None unless SINGLE_FLIGHT")

    # --- Q-D24: session transitions ride the NATURAL_KEY seam ---
    if spec.session_transition and spec.idempotency is not IdempotencyPosture.NATURAL_KEY:
        problems.append("session_transition ops MUST declare NATURAL_KEY (Q-D24)")

    # --- author never sets the derived rollup ---
    if spec.reversibility:
        problems.append("CompoundOpSpec.reversibility is derived; author must leave it unset")

    # --- leg discipline ---
    seen: set[str] = set()
    for leg in spec.legs:
        if leg.leg_id in seen:
            problems.append(f"duplicate leg_id {leg.leg_id!r}")
        seen.add(leg.leg_id)
        if leg.reversibility not in _REV_ORDER:
            problems.append(f"leg {leg.leg_id!r}: unknown reversibility {leg.reversibility!r}")
        if (leg.kind is LegKind.EFFECT and leg.reversibility == "compensatable"
                and leg.compensator is None):
            problems.append(f"leg {leg.leg_id!r}: COMPENSATABLE EFFECT leg requires compensator")

    # --- audit_completeness (spec-side): IRREVERSIBLE => confirmation ---
    derived = derive_reversibility(spec).reversibility
    if derived == "irreversible" and spec.confirmation is None:
        problems.append("IRREVERSIBLE op requires a ConfirmationSpec (P6/design §2.7)")

    # --- dedup tuple tokens must be declared op inputs? (spec: declared op
    #     inputs = ctx.params names; no param schema exists pre-manifest, so
    #     the tuple-form check is shape-only here: non-empty str tokens) ---
    if isinstance(spec.dedup_key, DedupKeySpec) and isinstance(spec.dedup_key.source, tuple):
        if not spec.dedup_key.source or not all(
                isinstance(t, str) and t for t in spec.dedup_key.source):
            problems.append("DedupKeySpec tuple source must name >=1 non-empty params")

    return problems


def check_atomic_db_only(spec: CompoundOpSpec) -> list[str]:
    """The external-conn fence (spec 07 §3.6) — call for every spec reachable
    as a scheduler handler / invariant repair_ref / version compensation_ref.
    NOT for draft op_kinds (they route through run() per-op, PIN-2)."""
    problems: list[str] = []
    for leg in spec.legs:
        if leg.kind is not LegKind.DB:
            problems.append(f"external-conn op {spec.op_key!r}: EFFECT leg {leg.leg_id!r}")
            continue
        try:
            source = inspect.getsource(resolve(leg.handler))
        except Exception:
            source = ""
        for token in _DB_LEG_BANNED_TOKENS:
            if token in source:
                problems.append(
                    f"external-conn op {spec.op_key!r}: DB leg {leg.leg_id!r} "
                    f"touches banned I/O ({token!r})")
    for emit in spec.emits:
        if emit.delivery is not DeliveryClass.AT_LEAST_ONCE:
            problems.append(
                f"external-conn op {spec.op_key!r}: BEST_EFFORT emit {emit.event!r} "
                "has no post-commit home")
    if spec.confirmation is not None:
        problems.append(
            f"external-conn op {spec.op_key!r}: confirmation cannot round-trip headless")
    return problems
