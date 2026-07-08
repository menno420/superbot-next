#!/usr/bin/env python3
"""check_egress — the RC-21 send-egress AST fence (S11, frozen L0 spec 10
§2.A class 13 / §8.1), WIDENED per A-5 to raw Discord STATE MUTATIONS.

Structural assertion over the sb/ tree: the method names that send content
or mutate Discord state may be CALLED only under `sb/adapters/` (the only
layer that touches discord objects) — plus the sanctioned K8 error shims
(`sb/app/error_handlers.py`, the C-1 last-resort reply chokepoint).

Everything else must route through the kernel ports:
  - replies  → SurfaceResponder (spec 02)
  - sends    → ChannelEmitter (sb/kernel/interaction/egress.py — the only
               path that computes AllowedMentions; UNTRUSTED default-deny)
  - state    → K7 EFFECT legs inside audited CompoundOpSpecs (adapters own
               the concrete discord calls)

Exit 0 = clean; exit 1 = violations.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SB = REPO_ROOT / "sb"

ALLOWED_DIRS = ("sb/adapters",)
ALLOWED_FILES = ("sb/app/error_handlers.py",)   # the C-1 error shims (spec 02 §3.3)

# send/reply egress + the A-5 raw Discord state mutations.
BANNED_METHODS = frozenset({
    "send", "reply", "send_message", "send_modal",
    "edit", "delete", "purge",
    "add_roles", "remove_roles", "ban", "kick", "timeout",
    "create_text_channel", "create_voice_channel", "create_role",
    "create_category", "edit_role_positions", "set_permissions",
})

# kernel-port receivers whose same-named methods are the SANCTIONED path
# (the fence bans raw discord objects, not the ports themselves).
ALLOWED_RECEIVERS = frozenset({
    "emitter", "_emitter", "responder", "_presenter", "bus", "_bus",
    "self", "store", "hook", "supervisor", "reader",
})


def _under(path: Path, dirs: tuple[str, ...], files: tuple[str, ...]) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    return (any(rel == d or rel.startswith(d + "/") for d in dirs)
            or rel in files)


def _receiver_name(node: ast.Call) -> str | None:
    func = node.func
    if not isinstance(func, ast.Attribute):
        return None
    base = func.value
    while isinstance(base, ast.Attribute):
        base = base.value
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Await):
        return None
    return None


def check() -> list[str]:
    problems: list[str] = []
    for path in sorted(SB.rglob("*.py")):
        if _under(path, ALLOWED_DIRS, ALLOWED_FILES):
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in BANNED_METHODS:
                continue
            receiver = _receiver_name(node)
            if receiver in ALLOWED_RECEIVERS:
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            problems.append(
                f"{rel}:{node.lineno}: raw egress/state call .{func.attr}(...) "
                f"outside sb/adapters (route replies through SurfaceResponder, "
                f"sends through ChannelEmitter, state through K7 EFFECT legs)")
    return problems


def main() -> int:
    problems = check()
    if problems:
        print("check_egress: VIOLATIONS")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("check_egress: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
