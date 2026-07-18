"""Unit coverage for tools/check_config_usage.py — the K0 CI gate that bans
scattered env reads (`os.getenv` / `os.environ`) anywhere under `sb/` except
the one typed loader `sb/kernel/config/` (and the ledgered
`sb/adapters/parity/boot.py` widening, D-0028).

The checker is a NAMED CI gate yet had zero unit tests. These drive its real
public seam — `check(root: Path) -> list[str]` (empty list = clean) and the
AST helper `_env_reads` — against `tmp_path` fake trees, plus a real-tree
green pin. Stdlib-`ast` only; no DB, no bot boot.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tools.check_config_usage import ALLOWED_PREFIXES, _env_reads, check

REPO_ROOT = Path(__file__).resolve().parents[3]


def _plant(root: Path, rel: str, body: str) -> None:
    """Write `body` to `root/rel`, creating parent dirs."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


# --------------------------------------------------------------- _env_reads
class TestEnvReads:
    def test_flags_os_getenv_attribute(self):
        tree = ast.parse("import os\nTOKEN = os.getenv('TOKEN')\n")
        hits = _env_reads(tree)
        assert hits == [(2, "os.getenv")]

    def test_flags_os_environ_attribute(self):
        tree = ast.parse("import os\nX = os.environ['K']\n")
        hits = _env_reads(tree)
        assert ("os.environ") in {what for _, what in hits}

    def test_flags_from_os_import_and_bare_use(self):
        tree = ast.parse("from os import getenv\nX = getenv('K')\n")
        whats = {what for _, what in _env_reads(tree)}
        # both the ImportFrom row and the bare-Name usage are reported
        assert "from os import getenv" in whats
        assert "getenv" in whats

    def test_clean_module_has_no_hits(self):
        tree = ast.parse("import os\nP = os.path.join('a', 'b')\n")
        assert _env_reads(tree) == []


# ----------------------------------------------------------- fake-tree check
class TestCheckFakeTree:
    def test_getenv_outside_config_is_reported(self, tmp_path):
        _plant(tmp_path, "sb/foo.py", "import os\nT = os.getenv('DISCORD_TOKEN')\n")
        violations = check(tmp_path)
        assert len(violations) == 1
        assert violations[0].startswith("sb/foo.py:2:")
        assert "os.getenv" in violations[0]

    def test_environ_outside_config_is_reported(self, tmp_path):
        _plant(tmp_path, "sb/domain/x.py", "import os\nY = os.environ['K']\n")
        violations = check(tmp_path)
        assert any("os.environ" in v and "sb/domain/x.py" in v for v in violations)

    def test_clean_tree_passes(self, tmp_path):
        _plant(tmp_path, "sb/foo.py", "from sb.kernel.config import Config\n")
        _plant(tmp_path, "sb/domain/x.py", "VALUE = 1\n")
        assert check(tmp_path) == []

    def test_config_package_is_allowed(self, tmp_path):
        # the one loader home may read the raw env
        _plant(
            tmp_path,
            "sb/kernel/config/loader.py",
            "import os\nT = os.getenv('DISCORD_TOKEN')\n",
        )
        assert check(tmp_path) == []

    def test_parity_boot_widening_is_allowed(self, tmp_path):
        # the ledgered D-0028 exception (seeds placeholder env before preflight)
        assert "sb/adapters/parity/boot.py" in ALLOWED_PREFIXES
        _plant(
            tmp_path,
            "sb/adapters/parity/boot.py",
            "import os\nT = os.getenv('TOKEN')\n",
        )
        assert check(tmp_path) == []

    def test_missing_sb_package_is_reported(self, tmp_path):
        violations = check(tmp_path)
        assert len(violations) == 1
        assert "sb/ package not found" in violations[0]

    def test_unparseable_module_is_reported_not_raised(self, tmp_path):
        _plant(tmp_path, "sb/broken.py", "def f(:\n")
        violations = check(tmp_path)
        assert any("unparseable" in v and "sb/broken.py" in v for v in violations)


# ----------------------------------------------------------- real-tree green
class TestRealTreeIsGreen:
    def test_committed_tree_has_no_env_read_violations(self):
        assert check(REPO_ROOT) == []
