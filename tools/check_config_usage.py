#!/usr/bin/env python3
"""check_config_usage — bans scattered env reads outside `sb/kernel/config/`.

Frozen L0 spec 05 §2/§7 (K0 CI gate): every consumer goes through the typed
`Config` accessor; `os.getenv` / `os.environ` are forbidden everywhere under
`sb/` except `sb/kernel/config/` (the one loader). AST-based, stdlib-only.

Exit 0 = clean; exit 1 = violations (one per line: path:line: message).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ALLOWED_PREFIXES = ("sb/kernel/config/",)


def _env_reads(tree: ast.AST) -> list[tuple[int, str]]:
    """Return (lineno, description) for every os.getenv / os.environ use."""
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            base = node.value
            if isinstance(base, ast.Name) and base.id == "os" and node.attr in ("getenv", "environ"):
                hits.append((node.lineno, f"os.{node.attr}"))
        elif isinstance(node, ast.Name) and node.id in ("getenv", "environ"):
            # `from os import getenv/environ` usage
            hits.append((node.lineno, node.id))
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            for alias in node.names:
                if alias.name in ("getenv", "environ"):
                    hits.append((node.lineno, f"from os import {alias.name}"))
    return hits


def check(root: Path) -> list[str]:
    violations: list[str] = []
    sb_root = root / "sb"
    if not sb_root.is_dir():
        return [f"{sb_root}: sb/ package not found"]
    for path in sorted(sb_root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(p) for p in ALLOWED_PREFIXES):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            violations.append(f"{rel}:{exc.lineno}: unparseable ({exc.msg})")
            continue
        for lineno, what in _env_reads(tree):
            violations.append(
                f"{rel}:{lineno}: {what} outside sb/kernel/config/ — read cfg.<ENV_VAR> instead"
            )
    return violations


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    violations = check(root)
    for line in violations:
        print(line)
    if violations:
        print(f"check_config_usage: {len(violations)} violation(s)", file=sys.stderr)
        return 1
    print("check_config_usage: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
