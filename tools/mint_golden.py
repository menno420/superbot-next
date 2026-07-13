#!/usr/bin/env python3
"""mint_golden — the D-0073 golden-minting procedure as a tool.

The procedure was re-derived by hand four times (the D-0073 btd6 modal
mints, the D-0075 kernel band, the D-0079 creature battle, the 2026-07-13
fishing/cleanup mints); this CLI codifies it end to end:

  (a) CAPTURE — resolve the case (typed ``parity.cases.CURATED_CASES``
      first — curated cases live in parity/cases/curated.py — then
      golden-document reconstruction for a ``--force`` re-mint), run it
      through ``sb.adapters.parity.runner.capture_case`` on a fresh
      harness boot (Postgres required — the db_delta is part of the pin),
      and apply the ruled dispositions via
      ``sb.adapters.parity.dispositions.apply_dispositions`` — imported,
      never reimplemented. Its built-in kernel-band skip IS the D-0075
      inversion: a ``subsystem: kernel`` doc KEEPS the kernel spine
      (audit_log / event_outbox / command.dispatched — the band's whole
      point is to pin those bytes), every other subsystem has it
      stripped per the kernel-surface-drift disposition lists.
      KERNEL cases are double-captured across two INDEPENDENT harness
      boots and the prepared docs must be byte-identical before anything
      is written (D-0075).

  (b) ORACLE VERIFICATION — manual, deliberately: parity pins ORACLE
      semantics, and only a human/agent reading the oracle
      (menno420/superbot @ the parity.yml source sha) can vouch for the
      user-facing bytes. The tool PRINTS the checklist; it never fakes
      the step.

  (c) RE-PIN — write ``parity/goldens/<subsystem>/<case>.json`` (corpus
      byte-form: ``indent=1, sort_keys=True, ensure_ascii=False`` + a
      trailing newline), recompute the corpus FROM DISK, and rewrite the
      mutable count pins: ``minted_goldens:`` + the ``imported + minted
      − retired = N`` arithmetic comment in parity/parity.yml, ``assert
      golden_count == N`` + the ``(N/N)`` docstring in
      tests/unit/parity_adapter/test_replay_adapter.py, and ``assert
      len(goldens) == N`` / ``assert "N goldens" in out`` / ``assert
      source["minted_goldens"] == N`` in
      tests/unit/parity_gate/test_check_parity_depth.py. The IMPORT pin
      (``source.goldens: 465``; ``assert source["goldens"] == 465``) is
      GUARDED — asserted present and unchanged, never rewritten; so is
      ``retired_goldens`` (retirement is a reviewed corpus ruling, not a
      mint).

Integrity rule (#193 / parity/README.md): goldens are NEVER hand-edited.
This tool writes exactly what capture_case + apply_dispositions produce;
if the bytes are wrong, fix the bot or re-rule the corpus — do not touch
the JSON.

Write is OPT-IN: the default run captures and prints the planned golden
path, the disposition-dropped surfaces, and every planned pin edit
(old → new per site) without touching a file. ``--write`` performs the
writes; ``--force`` is required to overwrite an existing golden
(a re-mint — counts do not move). Exit 0 green / 1 red.

DB note: capture needs a live Postgres (tools/setup_local_env.py locally,
the CI service container). Pin-rewrite unit coverage is DB-free —
tests/unit/parity_gate/test_mint_golden.py pins the pure text functions
on copies of the real files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

GOLDENS_ROOT = REPO_ROOT / "parity" / "goldens"
PARITY_YML = REPO_ROOT / "parity" / "parity.yml"
REPLAY_ADAPTER_TEST = (REPO_ROOT / "tests" / "unit" / "parity_adapter"
                       / "test_replay_adapter.py")
DEPTH_TEST = (REPO_ROOT / "tests" / "unit" / "parity_gate"
              / "test_check_parity_depth.py")

#: the kernel coverage home (D-0075) — double-capture + spine kept.
KERNEL_SUBSYSTEM = "kernel"


class MintError(Exception):
    """A red — anchor missing/ambiguous, unknown case, refused overwrite."""


# --------------------------------------------------------------- the corpus
@dataclass(frozen=True)
class CorpusCounts:
    """The count identity: on-disk corpus = imported + minted − retired."""

    imported: int
    retired: int
    total: int

    @property
    def minted(self) -> int:
        return self.total - self.imported + self.retired


def count_goldens_on_disk(goldens_root: Path) -> int:
    """The corpus denominator, exactly as every pin site computes it:
    ``<subsystem>/<case>.json`` one level down (root files like
    ``_sweep_skips.json`` are not goldens)."""
    return sum(1 for _ in goldens_root.glob("*/*.json"))


def read_source_pins(parity_yml_text: str) -> tuple[int, int]:
    """(imported, retired) from the parity.yml ``source`` section — the
    two pins a mint NEVER moves."""
    import yaml

    source = (yaml.safe_load(parity_yml_text) or {}).get("source") or {}
    imported = source.get("goldens")
    retired = source.get("retired_goldens")
    if not isinstance(imported, int) or not isinstance(retired, int):
        raise MintError(
            "parity.yml source section is missing integer goldens/"
            "retired_goldens pins")
    return imported, retired


def compute_counts(goldens_root: Path, parity_yml_text: str) -> CorpusCounts:
    imported, retired = read_source_pins(parity_yml_text)
    return CorpusCounts(imported=imported, retired=retired,
                        total=count_goldens_on_disk(goldens_root))


# ---------------------------------------------------------- pin rewriting
# Pure text → text, each anchored EXACTLY ONCE so a drifted file is a red,
# never a silent partial rewrite. The import pin is guarded, not rewritten.

def _sub_once(pattern: re.Pattern[str], replacement: str, text: str,
              site: str) -> str:
    matches = pattern.findall(text)
    if len(matches) != 1:
        raise MintError(
            f"pin anchor {site!r} matched {len(matches)} time(s), expected "
            f"exactly 1 — the file drifted; re-derive the anchor before "
            f"minting")
    return pattern.sub(replacement, text, count=1)


def _guard_unchanged(pattern: re.Pattern[str], before: str, after: str,
                     site: str) -> None:
    b, a = pattern.findall(before), pattern.findall(after)
    if len(b) != 1:
        raise MintError(
            f"guarded pin {site!r} matched {len(b)} time(s), expected "
            f"exactly 1")
    if b != a:
        raise MintError(f"guarded pin {site!r} would change — refusing "
                        f"(the import pin never moves on a mint)")


_YML_MINTED = re.compile(r"(?m)^(?P<pre>\s*minted_goldens:\s*)\d+\b")
_YML_ARITH = re.compile(
    r"(?P<pre>imported \+ minted [−-] retired = )\d+\b")
_YML_IMPORT_PIN = re.compile(r"(?m)^\s*goldens:\s*(\d+)\b")
_YML_RETIRED_PIN = re.compile(r"(?m)^\s*retired_goldens:\s*(\d+)\b")

_RA_DOCSTRING = re.compile(r"(?P<pre>replayable case )\(\d+/\d+\)")
_RA_ASSERT = re.compile(r"(?m)^(?P<pre>\s*assert golden_count == )\d+\b")

_DEPTH_LEN = re.compile(r"(?m)^(?P<pre>\s*assert len\(goldens\) == )\d+\b")
_DEPTH_OUT = re.compile(r'(?P<pre>assert ")\d+(?P<post> goldens" in out)')
_DEPTH_MINTED = re.compile(
    r'(?m)^(?P<pre>\s*assert source\["minted_goldens"\] == )\d+\b')
_DEPTH_IMPORT_PIN = re.compile(r'assert source\["goldens"\] == (\d+)\b')


def rewrite_parity_yml_pins(text: str, counts: CorpusCounts) -> str:
    """parity.yml: ``minted_goldens:`` + the arithmetic comment. The
    import pin (``source.goldens``) and ``retired_goldens`` are guarded."""
    out = _sub_once(_YML_MINTED, rf"\g<pre>{counts.minted}", text,
                    "parity.yml minted_goldens")
    out = _sub_once(_YML_ARITH, rf"\g<pre>{counts.total}", out,
                    "parity.yml arithmetic comment")
    _guard_unchanged(_YML_IMPORT_PIN, text, out, "parity.yml source.goldens")
    _guard_unchanged(_YML_RETIRED_PIN, text, out,
                     "parity.yml source.retired_goldens")
    return out


def rewrite_replay_adapter_pins(text: str, counts: CorpusCounts) -> str:
    """test_replay_adapter.py: the ``(N/N)`` docstring + the
    ``assert golden_count == N`` corpus pin."""
    out = _sub_once(_RA_DOCSTRING,
                    rf"\g<pre>({counts.total}/{counts.total})", text,
                    "test_replay_adapter (N/N) docstring")
    return _sub_once(_RA_ASSERT, rf"\g<pre>{counts.total}", out,
                     "test_replay_adapter golden_count assert")


def rewrite_depth_test_pins(text: str, counts: CorpusCounts) -> str:
    """test_check_parity_depth.py: corpus-count assert, the report-banner
    substring, and the minted_goldens source assert. The IMPORT pin
    (``assert source["goldens"] == 465``) is guarded, never rewritten."""
    out = _sub_once(_DEPTH_LEN, rf"\g<pre>{counts.total}", text,
                    "test_check_parity_depth len(goldens) assert")
    out = _sub_once(_DEPTH_OUT,
                    rf"\g<pre>{counts.total}\g<post>", out,
                    "test_check_parity_depth report-banner substring")
    out = _sub_once(_DEPTH_MINTED, rf"\g<pre>{counts.minted}", out,
                    "test_check_parity_depth minted_goldens assert")
    _guard_unchanged(_DEPTH_IMPORT_PIN, text, out,
                     "test_check_parity_depth import pin")
    return out


def planned_pin_edits(counts: CorpusCounts) -> list[tuple[Path, str, str]]:
    """[(path, old_text, new_text)] for the three pin files at the given
    counts — pure over file text; unchanged files still appear (old == new)
    so the caller can report no-ops honestly."""
    plans: list[tuple[Path, str, str]] = []
    for path, rewrite in (
        (PARITY_YML, rewrite_parity_yml_pins),
        (REPLAY_ADAPTER_TEST, rewrite_replay_adapter_pins),
        (DEPTH_TEST, rewrite_depth_test_pins),
    ):
        old = path.read_text()
        plans.append((path, old, rewrite(old, counts)))
    return plans


# ---------------------------------------------------------- case resolution
def resolve_case(case_id: str) -> Any:
    """A GoldenCase for *case_id*: typed curated cases first
    (parity/cases/curated.py — where curated cases live, #193), then
    reconstruction from an existing golden document (the re-mint path).
    A NEW mint therefore requires a CURATED_CASES entry."""
    from parity.cases import CURATED_CASES

    for case in CURATED_CASES:
        if case.id == case_id:
            return case

    stem = case_id.replace(".", "_") + ".json"
    matches = sorted(GOLDENS_ROOT.glob(f"*/{stem}"))
    for path in matches:
        golden = json.loads(path.read_text())
        if golden.get("case_id") != case_id:
            continue
        from sb.adapters.parity.cases import reconstruct_case

        case = reconstruct_case(golden)
        if case is None:
            raise MintError(
                f"case {case_id!r} exists on disk ({path}) but is not "
                f"reconstructable (normalized custom_id) — add a typed "
                f"entry to parity/cases/curated.py to re-mint it")
        return case

    raise MintError(
        f"unknown case {case_id!r}: not in parity.cases.CURATED_CASES and "
        f"no golden {stem!r} on disk — new mints declare a typed case in "
        f"parity/cases/curated.py first")


def golden_target(case: Any) -> Path:
    from parity.harness.runner import golden_path

    return golden_path(GOLDENS_ROOT, case)


def check_overwrite(path: Path, *, force: bool) -> None:
    """#193: an existing golden is corpus truth — refuse without --force."""
    if path.exists() and not force:
        raise MintError(
            f"golden already exists: {path} — goldens are never hand-edited "
            f"or silently replaced (#193 / parity/README.md); pass --force "
            f"for a deliberate re-mint (a reviewed corpus change)")


# ------------------------------------------------------------- the capture
def prepare_golden_doc(raw_doc: dict[str, Any]) -> dict[str, Any]:
    """The doc that gets WRITTEN: the ruled dispositions applied via the
    existing mechanism (sb.adapters.parity.dispositions.apply_dispositions
    — reused, not reimplemented). Non-kernel docs lose the kernel spine
    per the kernel-surface-drift lists; ``subsystem: kernel`` docs keep
    it (the D-0075 inversion is apply_dispositions' own built-in skip)."""
    from sb.adapters.parity.dispositions import apply_dispositions

    return apply_dispositions(raw_doc)


def serialize_golden(doc: dict[str, Any]) -> str:
    """The corpus byte-form (matches the goldens on disk)."""
    return json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def dropped_surfaces(raw_doc: dict[str, Any],
                     prepared_doc: dict[str, Any]) -> tuple[list[str], list[str]]:
    """(tables, events) present in the raw capture but disposition-dropped
    from the written doc — printed so the strip stays visible."""
    raw_tables = set((raw_doc.get("db_delta") or {}).keys())
    kept_tables = set((prepared_doc.get("db_delta") or {}).keys())

    def events_of(doc: dict[str, Any]) -> set[str]:
        return {e.get("event") for step in doc.get("steps") or []
                for e in step.get("events") or []}

    return (sorted(raw_tables - kept_tables),
            sorted(events_of(raw_doc) - events_of(prepared_doc)))


def docs_byte_identical(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return serialize_golden(a) == serialize_golden(b)


async def _capture_once(case: Any) -> dict[str, Any]:
    """One INDEPENDENT harness boot → capture → close — the D-0075
    double-capture posture. Per-case process state is reset by
    capture_case itself (``harness.reset_case_state()`` + the
    capture-world reseeds); the old harness's ``apply_isolation_resets``
    is NOT used — its ``tests/_isolation.py`` registry no longer exists
    in the tree (dead reference in parity/harness/runner.py; the new-bot
    lane never called it)."""
    from sb.adapters.parity.boot import Harness
    from sb.adapters.parity.runner import capture_case

    harness = await Harness.start()
    try:
        return await capture_case(harness, case)
    finally:
        await harness.close()


def capture_docs(case: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """(raw, prepared) for one mint. Kernel cases (D-0075) capture TWICE
    across independent boots and must prepare byte-identically."""
    import asyncio

    raw = asyncio.run(_capture_once(case))
    first = prepare_golden_doc(raw)
    if case.subsystem != KERNEL_SUBSYSTEM:
        return raw, first
    second = prepare_golden_doc(asyncio.run(_capture_once(case)))
    if not docs_byte_identical(first, second):
        a, b = serialize_golden(first).splitlines(), \
            serialize_golden(second).splitlines()
        drift = [f"  line {i + 1}: {la!r} != {lb!r}"
                 for i, (la, lb) in enumerate(zip(a, b)) if la != lb][:8]
        if len(a) != len(b):
            drift.append(f"  length {len(a)} != {len(b)}")
        raise MintError(
            "kernel double-capture drift (D-0075: two independent boots "
            "must be byte-identical):\n" + "\n".join(drift))
    return raw, first


# --------------------------------------------------------------- reporting
_CHECKLIST = """\
MANUAL STEPS (the tool cannot vouch for these — procedure step b, D-0073):
  [ ] ORACLE-VERIFY the user-facing bytes BEFORE committing: read the
      captured calls' content/embeds/components against the superbot
      oracle (menno420/superbot @ the parity.yml source sha). A golden
      that pins OUR bytes instead of the oracle's is corpus corruption,
      not coverage. (Kernel-band goldens pin OUR spine contract instead
      — there is no oracle for the spine; D-0075.)
  [ ] NARRATE the mint: extend the minted-history comment block above
      `minted_goldens:` in parity/parity.yml and the count-pin comment
      blocks in test_replay_adapter.py / test_check_parity_depth.py —
      the tool rewrites numbers, not prose.
  [ ] If this is a NEW subsystem dir: add its `subsystems:` row in
      parity/parity.yml (R1 pairs rows with dirs both ways).
  [ ] NEVER hand-edit the written JSON (#193 / parity/README.md).
  [ ] Verify before push: python3 -m pytest && python3
      tools/run_golden_parity.py --gate (Postgres up)."""


def _print_pin_plan(plans: list[tuple[Path, str, str]], *, wrote: bool) -> None:
    verb = "rewrote" if wrote else "would rewrite"
    for path, old, new in plans:
        if old == new:
            print(f"  pins unchanged: {path.relative_to(REPO_ROOT)}")
            continue
        print(f"  {verb}: {path.relative_to(REPO_ROOT)}")
        for old_line, new_line in zip(old.splitlines(), new.splitlines()):
            if old_line != new_line:
                print(f"    - {old_line.strip()}")
                print(f"    + {new_line.strip()}")


# --------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mint_golden",
        description="Mint one parity golden per the D-0073 procedure "
                    "(D-0075 kernel inversion included) and re-pin the "
                    "corpus counts. Dry-run by default.")
    parser.add_argument("case_id", help="case id, e.g. karma.thanks_grant "
                                        "(curated) — dots become underscores "
                                        "in the golden filename")
    parser.add_argument("--write", action="store_true",
                        help="write the golden + rewrite the count pins "
                             "(default: capture and print the plan only)")
    parser.add_argument("--force", action="store_true",
                        help="allow overwriting an existing golden "
                             "(a deliberate, reviewed re-mint)")
    args = parser.parse_args(argv)

    try:
        case = resolve_case(args.case_id)
        target = golden_target(case)
        check_overwrite(target, force=args.force)

        kernel = case.subsystem == KERNEL_SUBSYSTEM
        print(f"case: {case.id} (subsystem {case.subsystem}"
              f"{', KERNEL band — double-capture, spine kept (D-0075)' if kernel else ''})")

        raw, prepared = capture_docs(case)
        if kernel:
            print("double-capture: byte-identical across two independent "
                  "boots")
        else:
            tables, events = dropped_surfaces(raw, prepared)
            if tables or events:
                print(f"disposition-stripped (kernel-surface drift + ruled "
                      f"classes): tables={tables} events={events}")

        payload = serialize_golden(prepared)
        is_new = not target.exists()

        if args.write:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(payload)
            print(f"wrote: {target.relative_to(REPO_ROOT)} "
                  f"({len(payload)} bytes)")
        else:
            print(f"would write: {target.relative_to(REPO_ROOT)} "
                  f"({len(payload)} bytes) — pass --write")

        # counts FROM DISK (the write above already changed disk in --write
        # mode; in dry-run, simulate the one new file).
        counts = compute_counts(GOLDENS_ROOT, PARITY_YML.read_text())
        if not args.write and is_new:
            counts = CorpusCounts(imported=counts.imported,
                                  retired=counts.retired,
                                  total=counts.total + 1)
        print(f"corpus: {counts.total} = {counts.imported} imported + "
              f"{counts.minted} minted - {counts.retired} retired "
              f"(import pin untouched)")

        plans = planned_pin_edits(counts)
        if args.write:
            for path, old, new in plans:
                if old != new:
                    path.write_text(new)
        _print_pin_plan(plans, wrote=args.write)

        print()
        print(_CHECKLIST)
        mode = "written" if args.write else "dry-run (nothing written)"
        print(f"mint_golden: OK — {case.id} → "
              f"{target.relative_to(REPO_ROOT)}, corpus {counts.total}, "
              f"{mode}")
        return 0
    except MintError as exc:
        print(f"mint_golden: RED — {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 — env failure (no Postgres), not behavior
        print(f"mint_golden: RED — capture failed "
              f"({type(exc).__name__}: {exc}); a live Postgres is required "
              f"(tools/setup_local_env.py locally, the CI service container)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
