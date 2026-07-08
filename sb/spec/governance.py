"""The slash-first survivability grammar (S15 — frozen L0 spec 14 §2.A).

The D-5 `slash_common` tag MATERIALIZES the frozen Q-0237(e) slash-common
decision as a manifest-readable field — a RECORD of an existing decision,
never a new per-capability judgment. It rides each capability's ENTRY-POINT
spec (the `authority_ref` placement pattern): `CommandSpec` for
command-rooted capabilities (role-registered here against the duck-typed
Gate-0 facet, the sb/spec/cost.py discipline), `PanelActionSpec` /
`SelectorSpec` for panel-rooted ones (fields live in sb/spec/panels.py —
inherently interaction-delivered, so their PRESENCE is the survivable
signal).

The survivability invariant: every `slash_common` (essential) capability
has >=1 entry point delivered via INTERACTION_CREATE — a slash registration
or a panel/component/selector — which needs NEITHER privileged intent, so
intent denial can never dark an essential capability (the load-bearing
platform fact: the interaction payload carries the invoking member + roles;
RC-12 `member_tier` resolves under denial too).

Enforced by tools/check_intent_survival.py + its companion
tools/check_slash_cap.py (the Q-0237(e) 100/25/1-nest budget).

Stdlib-only leaf.
"""

from __future__ import annotations

from sb.spec.roles import register_field_roles

__all__ = [
    "SLASH_CAP_TOP_LEVEL",
    "SLASH_CAP_PER_GROUP",
    "SLASH_CAP_MAX_DEPTH",
    "check_manifest_survival",
    "slash_cap_violations",
]

# CommandSpec facet field (duck-typed Gate-0 facet; the roles registration
# makes it real grammar NOW — the cost.py pattern):
#   slash_common: bool = False   # [S] D-5: the frozen Q-0237(e) essential tag
register_field_roles("CommandSpec", slash_common="S")

# The Q-0237(e) budget (already baked into K1's validate; asserted here as
# the composed CI gate — spec 14 §2.A "bound to the 100-cap").
SLASH_CAP_TOP_LEVEL = 100
SLASH_CAP_PER_GROUP = 25
SLASH_CAP_MAX_DEPTH = 3   # "1 nest": command -> group -> subcommand


def _surface_of(cmd: object) -> str:
    # band 1: the minted CommandSpec facet carries `kind` (§2.2 vocabulary
    # prefix|slash|both) — read it when the older duck field is absent.
    raw = getattr(cmd, "surface", None)
    if raw is None:
        raw = getattr(cmd, "kind", None)
    value = getattr(raw, "value", raw)
    return str(value).lower() if value is not None else ""


def _capability_of(spec: object) -> str:
    cap = getattr(spec, "capability", "") or ""
    return str(cap) or str(getattr(spec, "name", "") or
                           getattr(spec, "action_id", "") or
                           getattr(spec, "selector_id", ""))


def check_manifest_survival(manifest: object) -> list[str]:
    """The `check_intent_survival` core over ONE duck-typed manifest: every
    capability with the slash_common tag set must have >=1
    interaction-delivered entry point — a SLASH-surface CommandSpec, or any
    PanelActionSpec/SelectorSpec (presence = survivable). A slash-common
    capability whose only registrations are PREFIX CommandSpecs is red.
    No AST needed — every input is already in the manifest."""
    commands = tuple(getattr(manifest, "commands", ()) or ())
    panels = tuple(getattr(manifest, "panels", ()) or ())

    # capability -> has any interaction-delivered entry point
    survivable: set[str] = set()
    essential: dict[str, str] = {}   # capability -> the tagging spec's name
    for cmd in commands:
        cap = _capability_of(cmd)
        if _surface_of(cmd) in ("slash", "both"):
            # `both` registers a slash surface too (G-6 kind partition), so
            # it is interaction-delivered and survives an intent denial.
            survivable.add(cap)
        if getattr(cmd, "slash_common", False):
            essential.setdefault(cap, str(getattr(cmd, "name", cap)))
    for panel in panels:
        for entry in tuple(getattr(panel, "actions", ()) or ()) + tuple(
                getattr(panel, "selectors", ()) or ()):
            cap = _capability_of(entry)
            survivable.add(cap)   # inherently interaction-delivered
            if getattr(entry, "slash_common", False):
                essential.setdefault(cap, cap)

    key = getattr(manifest, "key", "<manifest>")
    return [
        f"{key}/{name}: slash_common (essential) capability {cap!r} has NO "
        f"interaction-delivered entry point (SLASH CommandSpec or panel/"
        f"selector) — it goes dark on message_content denial (spec 14 §2.A)"
        for cap, name in sorted(essential.items()) if cap not in survivable
    ]


def slash_cap_violations(commands) -> list[str]:
    """The Q-0237(e) 100/25/1-nest budget over the registered GLOBAL slash
    tree (command paths are space-separated tokens)."""
    problems: list[str] = []
    top_level: set[str] = set()
    children: dict[str, set[str]] = {}
    for cmd in commands:
        if _surface_of(cmd) != "slash":
            continue
        path = str(getattr(cmd, "name", "")).split()
        if not path:
            continue
        top_level.add(path[0])
        if len(path) > SLASH_CAP_MAX_DEPTH:
            problems.append(f"{' '.join(path)}: nests deeper than 1 group "
                            f"(max {SLASH_CAP_MAX_DEPTH} tokens)")
        for depth in range(1, min(len(path), SLASH_CAP_MAX_DEPTH)):
            group = " ".join(path[:depth])
            children.setdefault(group, set()).add(path[depth])
    if len(top_level) > SLASH_CAP_TOP_LEVEL:
        problems.append(f"global slash tree has {len(top_level)} top-level "
                        f"commands (Discord cap {SLASH_CAP_TOP_LEVEL})")
    for group, kids in sorted(children.items()):
        if len(kids) > SLASH_CAP_PER_GROUP:
            problems.append(f"group {group!r} has {len(kids)} children "
                            f"(Discord cap {SLASH_CAP_PER_GROUP})")
    return problems
