"""Unit coverage for tools/check_symbol_shadowing.py — the K1 SYMBOL-identity
CI gate (the AST companion to the sb/namespace string registry).

Rules it enforces: (1) no in-module duplicate top-level def/class; (2) no
cross-module public-name collision within one package (unless one side is the
package `__init__.py` re-export, or a per-module `ENSURE_REFS` hook); (3)
grammar type names (`*Spec`/`*Result`/lexicon) are globally unique; (4) a bare
`class ActionSpec` is banned.

The checker is a NAMED CI gate yet had zero unit tests. These drive its real
public seam — `check(root: Path) -> list[str]` (empty list = clean) and the
AST helpers `_top_defs` / `_is_grammar_name` — against `tmp_path` fake trees,
plus a real-tree green pin. Stdlib-`ast` only; no DB, no bot boot.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tools.check_symbol_shadowing import _is_grammar_name, _top_defs, check

REPO_ROOT = Path(__file__).resolve().parents[3]


def _plant(root: Path, rel: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


# ---------------------------------------------------------------- _top_defs
class TestTopDefs:
    def test_collects_functions_and_classes_with_lineno_and_is_class(self):
        tree = ast.parse("def a():\n    pass\n\nclass B:\n    pass\n")
        assert _top_defs(tree) == [("a", 1, False), ("B", 4, True)]

    def test_async_def_is_collected(self):
        tree = ast.parse("async def h():\n    pass\n")
        assert _top_defs(tree) == [("h", 1, False)]

    def test_nested_defs_are_not_top_level(self):
        tree = ast.parse("def outer():\n    def inner():\n        pass\n")
        assert _top_defs(tree) == [("outer", 1, False)]


# ----------------------------------------------------------- _is_grammar_name
class TestIsGrammarName:
    def test_spec_and_result_suffixes_are_grammar(self):
        assert _is_grammar_name("PanelActionSpec")
        assert _is_grammar_name("WorkflowResult")

    def test_lexicon_member_is_grammar(self):
        assert _is_grammar_name("AIGateway")  # a lexicon entry with no suffix

    def test_ordinary_name_is_not_grammar(self):
        assert not _is_grammar_name("Helper")


# ----------------------------------------------------------- fake-tree check
class TestCheckFakeTree:
    def test_in_module_duplicate_top_level_def_is_reported(self, tmp_path):
        _plant(tmp_path, "sb/foo.py", "def go():\n    pass\n\ndef go():\n    pass\n")
        violations = check(tmp_path)
        assert any("in-module shadowing" in v and "`go`" in v for v in violations)

    def test_cross_module_public_collision_within_package_is_reported(self, tmp_path):
        _plant(tmp_path, "sb/pkg/a.py", "def widget():\n    pass\n")
        _plant(tmp_path, "sb/pkg/b.py", "def widget():\n    pass\n")
        violations = check(tmp_path)
        assert any(
            "public `widget`" in v and "package sb/pkg" in v for v in violations
        )

    def test_duplicate_grammar_name_across_modules_is_reported(self, tmp_path):
        _plant(tmp_path, "sb/one.py", "class FooSpec:\n    pass\n")
        _plant(tmp_path, "sb/two.py", "class FooSpec:\n    pass\n")
        violations = check(tmp_path)
        assert any(
            "grammar type `FooSpec`" in v and "globally unique" in v
            for v in violations
        )

    def test_banned_actionspec_class_is_reported(self, tmp_path):
        _plant(tmp_path, "sb/foo.py", "class ActionSpec:\n    pass\n")
        violations = check(tmp_path)
        assert any("`class ActionSpec` is banned" in v for v in violations)

    def test_clean_tree_passes(self, tmp_path):
        _plant(tmp_path, "sb/a.py", "def alpha():\n    pass\n")
        _plant(tmp_path, "sb/b.py", "def beta():\n    pass\n")
        assert check(tmp_path) == []

    def test_init_reexport_is_not_a_collision(self, tmp_path):
        # a package __init__.py deliberately re-exports a module's public name
        _plant(tmp_path, "sb/pkg/impl.py", "def widget():\n    pass\n")
        _plant(tmp_path, "sb/pkg/__init__.py", "def widget():\n    pass\n")
        assert check(tmp_path) == []

    def test_ensure_refs_module_hook_is_exempt(self, tmp_path):
        # the manifest-module ENSURE_REFS hook may repeat across modules (D-0025)
        _plant(tmp_path, "sb/pkg/a.py", "def ENSURE_REFS():\n    pass\n")
        _plant(tmp_path, "sb/pkg/b.py", "def ENSURE_REFS():\n    pass\n")
        assert check(tmp_path) == []

    def test_private_names_do_not_collide_across_modules(self, tmp_path):
        _plant(tmp_path, "sb/pkg/a.py", "def _helper():\n    pass\n")
        _plant(tmp_path, "sb/pkg/b.py", "def _helper():\n    pass\n")
        assert check(tmp_path) == []

    def test_missing_sb_package_is_reported(self, tmp_path):
        violations = check(tmp_path)
        assert len(violations) == 1
        assert "sb/ package not found" in violations[0]

    def test_unparseable_module_is_reported_not_raised(self, tmp_path):
        _plant(tmp_path, "sb/broken.py", "class :\n")
        violations = check(tmp_path)
        assert any("unparseable" in v and "sb/broken.py" in v for v in violations)


# ----------------------------------------------------------- real-tree green
class TestRealTreeIsGreen:
    def test_committed_tree_has_no_shadowing_violations(self):
        assert check(REPO_ROOT) == []
