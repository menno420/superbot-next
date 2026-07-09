# 2026-07-09 — vendored kit upgrade to substrate-kit v1.0.0

> **Status:** `complete`

## Scope

First real-world run of the kit's `upgrade` verb (founding plan §4.3): replace
this repo's pre-1.0 vendored `bootstrap.py` with the released v1.0.0 dist
(sha256 `5e518d4978a01926057bdece04d88bd5f1b7d433bbc19b36790bdeff14149313`,
verified against `release.json`). Closes the named follow-up from the
kit-version-pin session (the old dist's `Config.from_dict` drops `kit_version`
on any config round-trip; the new dist's declared field fixes it).

## What shipped

- Downloaded the three v1.0.0 release assets; sha256 verified locally
  (matches `bootstrap.py.sha256`) and again by the verb itself against
  `release.json`.
- Ran `python3 bootstrap.py.new upgrade` (no `--apply-docs` — see below):
  old dist archived to `.substrate/backup/bootstrap-unknown.py` + state.json
  banked **before** any overwrite; vendored `bootstrap.py` replaced; staged
  `.substrate/` artifacts regenerated (two newly derived provisional slots:
  `primary_language=Python`, `verify_command='python3 -m pytest'`);
  `kit_version: 1.0.0` recorded in state.json; `.substrate/upgrade-report.md`
  written. The backup dir is **committed** so `upgrade --rollback` stays
  usable from a fresh session container (uncommitted backups evaporate with
  the container).
- **Upgrade-report classification:** all 15 planted docs `consumer-edited`
  ("template unchanged — consumer-owned, nothing to apply") — the verb parsed
  the old dist's embedded templates and found them identical to v1.0.0's, so
  it did *better* than the plan's promised pre-1.0 worst case (everything
  `diverged`). Zero `template-improved` docs → `--apply-docs` had nothing to
  apply and was correctly not run; no consumer doc was touched.
- **Verified after:** `bootstrap.py --version` → `substrate-kit 1.0.0`;
  config load→save round-trip preserves `kit_version` (and
  `reconciliation_prs: 30`); state.json carries `kit_version`
  (`planted_doc_hashes` is absent — correct: the kit never wrote these docs,
  hashes record only on plant/`render --live`/`--apply-docs`);
  `check --strict` red only on this card's own born-red badge (the gate
  working as designed); tests 919 passed, checker fleet + manifest compile
  green.

## Kit finding (for substrate-kit, not fixed here)

**From-version misreport when the consumer pins `kit_version` in config
before upgrading** — which is exactly the order kit-lab D2 produced (PR #42
pinned `1.0.0`, this session upgraded). `run_upgrade` computes
`old_version = config.kit_version or dist_version(old_text)`, so the config
pin outranks the actual old dist header: the report title reads
"v1.0.0 → v1.0.0" and `last-upgrade.json` records `from_version: "1.0.0"`,
while the archive filename honestly says `bootstrap-unknown.py`. Harmless
here, but a rollback after a misreported upgrade would restore the wrong
`config.kit_version` string. Repro: pre-1.0 vendored dist + config
`kit_version: "1.0.0"` → run `bootstrap.py.new upgrade` → report says
v1.0.0 → v1.0.0. Suggested kit fix: prefer `dist_version(old_text)` when it
disagrees with the config pin (the code comment's copied-by-hand case is the
one where the *header* is new — distinguishable by comparing header to
`KIT_VERSION`).

## 💡 Session idea

Teach `upgrade` to clean up after itself: it knows its own invocation file
(`running`) and the `release.json` beside it, but leaves both at the repo
root after replacing the vendored copy — every consumer must remember to
delete `bootstrap.py.new` + `release.json` or they land in the upgrade PR.
A final `removed: bootstrap.py.new (self)` step (or at least a report line
telling the consumer to) would make the §4.3 flow truly one-command.

## ⟲ Previous-session review

The kit-version-pin session (PR #42) did the config half cleanly and — its
best move — *named this exact follow-up* with the precise trap (old-dist
round-trip strips the key) and the precise fix path (§4.3 flow, sha256, the
verbs to avoid meanwhile), which made this session near-zero-orientation.
It also verified the old dist tolerated the new key before pinning.
Improvement it surfaces: its 💡 idea (a `check --strict` advisory comparing
config `kit_version` to the running dist's stamped version) is now *directly
evidenced* by this session's from-version misreport — the same
config-vs-dist mismatch, caught by neither tool. That idea should be
promoted into the kit's checker suite.

## ⚑ Flags

- Self-initiated: committed `.substrate/backup/` (the rollback bank) rather
  than leaving it untracked — durability across ephemeral session containers;
  reversible by deleting the dir.
- Kit bug reported upstream via the coordinating session (from-version
  misreport above); not worked around — output-only, nothing functional
  depended on it.
