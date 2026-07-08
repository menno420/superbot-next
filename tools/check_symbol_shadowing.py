#!/usr/bin/env python3
"""check_symbol_shadowing — the AST companion to the K1 string registry.

The two-mechanism split (design-spec §3.5, ~L1159): the runtime-STRING
registry is `sb/namespace/`; this pass guards SYMBOL identities. Rules:

1. no module defines the same top-level `def`/`class` name twice;
2. no two modules define the same public name within one package unless one
   of the two is the package's `__init__.py` (deliberate re-export);
3. grammar type names (`*Spec`, `*Result`, and the lexicon of load-bearing
   types) are globally unique across the repo;
4. any new `class ActionSpec` anywhere is red (the bare-symbol ban, decision
   1 — its STRING twin lives in sb/namespace/tombstones.json; neither
   subsumes the other).

Stdlib ast only. Exit 0 = clean; exit 1 = violations.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BANNED_SYMBOLS = {"ActionSpec"}
LEXICON = {
    "PanelActionSpec", "AutomationActionSpec", "SettingSpec", "BindingSpec",
    "SubsystemManifest", "WorkflowResult", "CapabilityDecision", "AIGateway",
}


def _top_defs(tree: ast.Module) -> list[tuple[str, int, bool]]:
    """(name, lineno, is_class) for every top-level def/class."""
    return [
        (node.name, node.lineno, isinstance(node, ast.ClassDef))
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]


def _is_grammar_name(name: str) -> bool:
    return name in LEXICON or name.endswith("Spec") or name.endswith("Result")


def check(root: Path) -> list[str]:
    violations: list[str] = []
    grammar_seen: dict[str, str] = {}          # grammar name -> first locus
    package_names: dict[tuple[str, str], str] = {}  # (package, name) -> first locus

    sb_root = root / "sb"
    if not sb_root.is_dir():
        return [f"{sb_root}: sb/ package not found"]

    for path in sorted(sb_root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            violations.append(f"{rel}:{exc.lineno}: unparseable ({exc.msg})")
            continue
        defs = _top_defs(tree)
        # Rule 1: in-module duplicate top-level binding.
        seen_in_module: dict[str, int] = {}
        for name, lineno, is_class in defs:
            if name in seen_in_module:
                violations.append(
                    f"{rel}:{lineno}: `{name}` re-binds the top-level definition "
                    f"at line {seen_in_module[name]} (in-module shadowing)"
                )
            seen_in_module[name] = lineno
            locus = f"{rel}:{lineno}"
            # Rule 4: the banned bare symbol.
            if is_class and name in BANNED_SYMBOLS:
                violations.append(f"{locus}: `class {name}` is banned (decision 1)")
            # Rule 3: grammar names globally unique.
            if is_class and _is_grammar_name(name):
                if name in grammar_seen:
                    violations.append(
                        f"{locus}: grammar type `{name}` already defined at "
                        f"{grammar_seen[name]} (grammar names are globally unique)"
                    )
                else:
                    grammar_seen[name] = locus
            # Rule 2: cross-module public-name collision within one package.
            if not name.startswith("_") and path.name != "__init__.py":
                package = path.parent.relative_to(root).as_posix()
                key = (package, name)
                if key in package_names:
                    violations.append(
                        f"{locus}: public `{name}` also defined at {package_names[key]} "
                        f"in package {package} (rename or move to a shared home)"
                    )
                else:
                    package_names[key] = locus
    return violations


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    violations = check(root)
    for line in violations:
        print(line)
    if violations:
        print(f"check_symbol_shadowing: {len(violations)} violation(s)", file=sys.stderr)
        return 1
    print("check_symbol_shadowing: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
