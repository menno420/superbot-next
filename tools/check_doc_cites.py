#!/usr/bin/env python3
"""check_doc_cites — file:line citation checker over tracked markdown.

VERDICT 012 consumption (sim-lab `sims/verdict-012-doc-cite-checker-spec/`
@ 055245e9, approve): ships the measured winning spec verbatim —
**grammar** g3-strict-guard (slash-required paths, every segment carries
a letter, no `...`, fenced code blocks skipped), **scope** every tracked
`*.md` minus the FOREIGN_ROOTS config, **resolution** exact repo path
else unique path-suffix (ambiguous passes as unverifiable), **gating**
rule (a) missing-file RED (exit 1; measured 0 FP on this repo at the
sweep pin 2c62a099) with the inline waiver token for intentional
absent-path mentions, rule (b) range>EOF WARN (advisory — 16/29 audited
superbot pairs were <=2-line EOF boundary noise), rule (c) NOT shipped
(sampled precision 1/15).

Prints per-class counts (missing / boundary / skipped-foreign /
ambiguous / waived) per run — the verdict's telemetry guardrail, so the
warn->red graduation for rule (b) has its own evidence trail.

Run: python3 tools/check_doc_cites.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --- the only config (VERDICT 012 "named changes" item 3) -------------------

#: cross-repo first segments that must never red-gate: the sweep-measured
#: superbot set {disbot/, views/, cogs/, utils/, scripts/, ext/} plus the
#: sim-lab evidence tree {sims/, harness/} cited by docs/review/ (the
#: config is lane-maintained by design — the verdict names it the one
#: knob; both additions are foreign-repo trees, the same class).
FOREIGN_ROOTS = ("disbot/", "views/", "cogs/", "utils/", "scripts/",
                 "ext/", "sims/", "harness/")

#: inline waiver token for intentional absent-path mentions (correction
#: notes citing a fabricated path on purpose — superbot has 7 such lines,
#: this repo 0 at the sweep pin).
WAIVER_TOKEN = "cite: absent-by-design"

# --- grammar g3-strict-guard -------------------------------------------------

#: the verdict's cite regex verbatim (slash-required enforced post-match).
CITE_RE = re.compile(
    r"(?<![\w/.-])((?:[\w.-]+/)*[\w.-]+\.(?:py|ts|tsx|yml|yaml))"
    r":(\d+)(?:-(\d+))?")

_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_SEGMENT_HAS_LETTER = re.compile(r"[A-Za-z]")


def _g3_ok(path: str) -> bool:
    """g3-strict-guard: path contains '/', every segment contains a
    letter, no '...' anywhere (kills the two live regex-glue artifact
    classes the sweep measured on superbot)."""
    if "/" not in path or "..." in path:
        return False
    return all(_SEGMENT_HAS_LETTER.search(seg) for seg in path.split("/"))


def _tracked_md() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=ROOT, check=True,
        capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line]


def _iter_cites(text: str):
    """(lineno, line, path, start, end) per cite outside fenced blocks."""
    fenced = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        for match in CITE_RE.finditer(line):
            path = match.group(1)
            if not _g3_ok(path):
                continue
            start = int(match.group(2))
            end = int(match.group(3)) if match.group(3) else start
            yield lineno, line, path, start, end


def _build_suffix_index() -> tuple[set[str], dict[str, list[str]]]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True,
        capture_output=True, text=True).stdout
    tracked = {line for line in out.splitlines() if line}
    by_basename: dict[str, list[str]] = {}
    for path in tracked:
        by_basename.setdefault(path.rsplit("/", 1)[-1], []).append(path)
    return tracked, by_basename


def _resolve(path: str, tracked: set[str],
             by_basename: dict[str, list[str]]) -> str | None:
    """exact repo path, else unique path-suffix; 'ambiguous' sentinel
    passes as unverifiable (never red — the verdict's guardrail)."""
    if path in tracked:
        return path
    candidates = [p for p in by_basename.get(path.rsplit("/", 1)[-1], ())
                  if p == path or p.endswith("/" + path)]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        return "<ambiguous>"
    return None


def main() -> int:
    tracked, by_basename = _build_suffix_index()
    counts = {"checked": 0, "missing": 0, "boundary": 0,
              "skipped_foreign": 0, "ambiguous": 0, "waived": 0}
    red: list[str] = []
    warn: list[str] = []
    for doc in _tracked_md():
        text = (ROOT / doc).read_text(encoding="utf-8")
        for lineno, line, path, start, end in _iter_cites(text):
            counts["checked"] += 1
            if any(path.startswith(root) for root in FOREIGN_ROOTS):
                counts["skipped_foreign"] += 1
                continue
            resolved = _resolve(path, tracked, by_basename)
            if resolved == "<ambiguous>":
                counts["ambiguous"] += 1
                continue
            if resolved is None:
                if WAIVER_TOKEN in line:
                    counts["waived"] += 1
                    continue
                counts["missing"] += 1
                red.append(f"{doc}:{lineno}: cited file not found: "
                           f"{path}:{start}")
                continue
            # rule (b): cited range <= EOF — WARN (advisory).
            n_lines = len((ROOT / resolved).read_text(
                encoding="utf-8", errors="replace").splitlines())
            if max(start, end) > n_lines:
                counts["boundary"] += 1
                warn.append(f"{doc}:{lineno}: range {start}-{end} > EOF "
                            f"({n_lines} lines): {path}")
    for item in warn:
        print(f"WARN (range>EOF): {item}")
    for item in red:
        print(f"RED (missing file): {item}")
    print("check_doc_cites: "
          + " ".join(f"{k}={v}" for k, v in counts.items()))
    if red:
        print(f"check_doc_cites: FAIL — {len(red)} missing-file cite(s) "
              f"(waive intentional mentions with `{WAIVER_TOKEN}`)")
        return 1
    print("check_doc_cites: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
