"""The class-killer invariant (docs/ideas/effect-leg-compensation-gaps-
2026-07-10.md): a ``"reversible"`` EFFECT leg without a compensator behaves
identically to ``irreversible`` at runtime (engine fork E: failed effect
without compensator => operator finding only) — the label promises safety
that isn't wired. So: every NON-OPTIONAL EFFECT leg that FOLLOWS a DB leg
must be compensatable-with-compensator, irreversible (the §2.7 confirm
fence owns that posture), or optional. Scans EVERY declared CompoundOpSpec
in sb/domain so the class is unwritable at authoring time — both original
instances (moderation.timeout, proof_channel.end_access) failed this test
before their compensators landed; KICK (deliberately irreversible +
typed-phrase confirmation, docs/decisions.md) passes by design."""

from __future__ import annotations

import importlib
from pathlib import Path

from sb.kernel.workflow.spec import CompoundOpSpec, LegKind

# Ops that violate the invariant with an accepted, documented justification.
# Keep EMPTY unless a ruling says otherwise — an entry here is a standing
# defect the test would otherwise catch. Format: {op_key: "why"}.
_ALLOWLIST: dict[str, str] = {}


def _domain_spec_modules() -> list[str]:
    """Every sb.domain module that declares a CompoundOpSpec (source scan —
    a new domain's ops module joins the sweep automatically)."""
    root = Path(__file__).resolve().parents[3]
    domain = root / "sb" / "domain"
    modules = []
    for path in sorted(domain.rglob("*.py")):
        if "CompoundOpSpec(" in path.read_text():
            rel = path.relative_to(root).with_suffix("")
            modules.append(".".join(rel.parts))
    return modules


def _collect_specs() -> dict[str, CompoundOpSpec]:
    specs: dict[str, CompoundOpSpec] = {}
    for module_name in _domain_spec_modules():
        module = importlib.import_module(module_name)
        for obj in vars(module).values():
            candidates = obj if isinstance(obj, tuple) else (obj,)
            for item in candidates:
                if isinstance(item, CompoundOpSpec):
                    specs[item.op_key] = item
    return specs


def test_sweep_sees_the_full_roster():
    specs = _collect_specs()
    # the roster only grows; 97 ops at the time this invariant landed
    assert len(specs) >= 97
    for key in ("moderation.timeout", "proof_channel.end_access",
                "moderation.kick", "moderation.warn"):
        assert key in specs, key


def test_effect_leg_after_db_leg_declares_its_recovery_posture():
    """No dead-letter EFFECT legs: after a DB leg commits, a non-optional
    EFFECT leg labelled "reversible" with no compensator strands external
    state on refusal — durable history claims something happened that
    didn't."""
    violations: list[str] = []
    for op_key, spec in sorted(_collect_specs().items()):
        db_seen = False
        for leg in spec.legs:
            if leg.kind is LegKind.DB:
                db_seen = True
                continue
            if leg.kind is not LegKind.EFFECT or not db_seen or leg.optional:
                continue
            if leg.reversibility == "reversible" and leg.compensator is None:
                if op_key not in _ALLOWLIST:
                    violations.append(f"{op_key}/{leg.leg_id}")
            elif leg.reversibility == "irreversible" and spec.confirmation is None:
                # the §2.7 fence: irreversible must carry its confirm posture
                if op_key not in _ALLOWLIST:
                    violations.append(f"{op_key}/{leg.leg_id} (irreversible, no confirm)")
    assert violations == [], (
        "EFFECT leg(s) after a committed DB leg with no wired recovery — "
        "declare a compensator (compensatable), an explicit irreversible+"
        f"confirm posture, or optional: {violations}")


def test_allowlist_entries_are_still_real_ops():
    """A stale allowlist row outlives its defect — prune on fix."""
    specs = _collect_specs()
    for op_key in _ALLOWLIST:
        assert op_key in specs, f"allowlisted op {op_key!r} no longer exists"
