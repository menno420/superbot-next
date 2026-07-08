#!/usr/bin/env python3
"""check_no_skip — the K8 AST no-skip fence (frozen L0 spec 02 §7, arms at
S9): there is NO path from a Discord surface to a handler except through
`sb.kernel.interaction.resolve.resolve()`.

Two structural assertions over the sb/ tree:

1. **Surface-registration containment** — the tokens that register a Discord
   entry point (`@bot.event`, `@bot.command`, `@commands.command`,
   `@tree.command`, `@app_commands.command`, `tree.interaction_check`,
   `bot.add_view`, `@bot.listen`) may appear ONLY under the sanctioned
   composition layers: `sb/kernel/interaction/adapters/`,
   `sb/adapters/discord/`, `sb/app/`. Anywhere else = a bypassing path.
2. **discord import containment** — `import discord` / `from discord`
   appears ONLY under `sb/adapters/` (guarded) — the kernel never sees a
   discord type (the layer rule the whole spine rides).

Exit 0 = clean; exit 1 = violations.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SB = REPO_ROOT / "sb"

ALLOWED_SURFACE_DIRS = (
    "sb/kernel/interaction/adapters",
    "sb/adapters/discord",
    "sb/app",
)
ALLOWED_DISCORD_IMPORT_DIRS = ("sb/adapters",)

SURFACE_TOKENS = (
    "bot.event", "bot.command", "bot.listen", "commands.command",
    "tree.command", "app_commands.command", "tree.interaction_check",
    "bot.add_view", "process_commands",
)


def _under(path: Path, dirs: tuple[str, ...]) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    return any(rel == d or rel.startswith(d + "/") for d in dirs)


def _decorator_tokens(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        decorators = getattr(node, "decorator_list", None) or []
        for dec in decorators:
            target = dec.func if isinstance(dec, ast.Call) else dec
            found.add(ast.unparse(target))
    return found


def check() -> list[str]:
    problems: list[str] = []
    for path in sorted(SB.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            problems.append(f"{rel}: unparseable ({exc})")
            continue

        # 2. discord import containment.
        if not _under(path, ALLOWED_DISCORD_IMPORT_DIRS):
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    if any(a.name.split(".")[0] == "discord" for a in node.names):
                        problems.append(f"{rel}:{node.lineno}: discord import "
                                        "outside sb/adapters (layer rule)")
                elif isinstance(node, ast.ImportFrom):
                    if (node.module or "").split(".")[0] == "discord":
                        problems.append(f"{rel}:{node.lineno}: discord import "
                                        "outside sb/adapters (layer rule)")

        # 1. surface-registration containment.
        if not _under(path, ALLOWED_SURFACE_DIRS):
            tokens = _decorator_tokens(tree)
            for token in SURFACE_TOKENS:
                if any(token in t for t in tokens) or f"{token}(" in source:
                    problems.append(
                        f"{rel}: surface-registration token {token!r} outside "
                        "the sanctioned adapter/composition layers — every "
                        "surface must funnel through resolve()")
    return problems


def main() -> int:
    problems = check()
    if problems:
        print("check_no_skip: VIOLATIONS")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("check_no_skip: clean (every surface funnels through resolve())")
    return 0


if __name__ == "__main__":
    sys.exit(main())
