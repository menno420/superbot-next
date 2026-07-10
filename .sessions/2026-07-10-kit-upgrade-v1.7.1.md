# 2026-07-10 — vendored kit upgrade to substrate-kit v1.7.1

> **Status:** `complete`

## Scope

Fifth run of the kit's `upgrade` verb on this repo (v1.0.0 → v1.2.0 →
v1.6.0 → v1.7.0 → now v1.7.1): move the vendored `bootstrap.py` from
v1.7.0 to the released v1.7.1 (tag `1cbd666`, release asset sha256
`2aa4feddf7de7e20b00f46866826985ca8fd11f40bc51ebe261bbdef3118486d`).
Kit-owned files only — no domain work; `control/inbox.md` and
`control/status.md` untouched by directive (Q-0261.3; the lane's own next
heartbeat records the `kit:` line).

- **📊 Model:** claude-fable-5 · high · mechanical kit upgrade

## What shipped

- **Upgrade per §4.3 / the v1.7.1 adopter checklist:** release asset
  digest verified before running (full sha256 recorded above, matches the
  GitHub release asset digest byte-for-byte), `release.json` placed next
  to `bootstrap.py.new` so the verb's own sha256+version verification
  engaged (not silently skipped), then `python3 bootstrap.py.new upgrade`.
  Inputs self-cleaned by the verb; vendored `bootstrap.py` replaced
  v1.7.0 → v1.7.1; `kit_version: "1.7.1"` recorded in config;
  `last-upgrade.json` honest (`from_version: "1.7.0"`, archived dist
  `.substrate/backup/bootstrap-1.7.0.py`).
- **#137 regression check — PASS:** this run banked EXACTLY ONE dist, the
  OLD one: `.substrate/backup/bootstrap-1.7.0.py` sha256
  `00f4f4cd…5238` == the pre-upgrade vendored `bootstrap.py` (byte-equal,
  verified against `origin/main:bootstrap.py`), and NO spurious
  `bootstrap-1.7.1.py` archive appeared. (The file was already present
  byte-identically — the v1.7.0 upgrade's spurious new-dist banking, the
  very bug #137 fixed — so git shows it unmodified.)
- **Upgrade-report classification:** unchanged 10 · consumer-edited 9
  (all left alone, including both control seam files) · diverged 0 ·
  template-improved 0 — first upgrade on this repo with zero manual-merge
  lanes (the v1.7.0 session's `control/README.md` merge is why).
  **Carve-out section: ABSENT — zero carve-outs reported**, as expected:
  no live `.github/workflows/substrate-gate.yml` exists on this repo
  (deliberate since v1.2.0 — `ci.yml` runs `check --strict`), so the
  v1.7.1 kit-owned live-gate regeneration is N/A here; no
  `substrate-gate.pre-regen-*.yml` bank (correct — nothing to bank).
- **Staged `.substrate/` artifacts regenerated;** byte changes only in
  the staged `ci/substrate-gate.yml` (+35/−2) — which now wires
  `--inbox-base` (line 78: `check --strict --status-only --inbox-base
  "$basefile"`, the previously-LATENT inbox append-only gate) and carries
  the carve-out-protected regen header — and `ci/quality.yml.example`
  (+5: the kit-owned-gate note). Still NOT installed as a live workflow —
  same deliberate decision as the v1.2.0/v1.6.0/v1.7.0 sessions.
- **Verified after:** `bootstrap.py --version` → 1.7.1; `check --strict`
  exit 0 (one pre-existing, never-exit-affecting
  `[owner-ask-wall-unrecorded]` advisory on `control/status.md`
  OWNER-ACTION 3 — same one the v1.7.0 session flagged, still owed to the
  lane's heartbeat session, out of this session's directed scope);
  `python3 -m pytest tests/ -q` (CI's exact invocation): 1173 passed /
  2 skipped; `manifest_compile` green.

## Kit findings / flags for the lane

- The v1.7.0 session's spurious-backup observation shipped fixed in this
  release exactly as advertised (#137) and the fix verified clean on this
  repo — the find-upstream-fix-next-release loop closed again.
- The `[owner-ask-wall-unrecorded]` advisory on OWNER-ACTION 3 remains
  open for the lane's next heartbeat session (CAPABILITIES.md append +
  the `kit: v1.7.1` status line), both deliberately out of scope here.

## 💡 Session idea

The #137 fix means `.substrate/backup/` now accumulates one honest
archive per hop — but the *pre-#137* spurious archives (this repo's
`bootstrap-unknown.py`, and the already-present `bootstrap-1.7.0.py` this
run happened to legitimize) are indistinguishable from honest banks
without reading `last-upgrade.json` history. Cheap kit follow-up: have
`upgrade` write an append-only `.substrate/backup/ledger.jsonl` line per
bank (file, sha256, from→to, date, reason: pre-upgrade|pre-regen), so a
later `check` can flag orphan archives and a cleanup verb can safely
prune superseded dists (the directory grows by ~550KB per hop forever
otherwise).

## ⟲ Previous-session review

The v1.7.0 upgrade session (#116) again executed its predecessor's
template almost verbatim and left this session a clean runway: its manual
merge of the `control/README.md` additive delta is precisely why this
upgrade saw zero diverged docs — the first fully-mechanical upgrade in
the repo's history. Its forecast idea ("predict which classification rows
the NEXT upgrade will see") wasn't adopted kit-side yet, but its
prediction implicitly held (it expected the gate-regen wave to arrive
with this release — it did, and correctly no-op'd here). What it could
have done better: it noted the spurious `bootstrap-1.7.0.py` bank only in
passing rather than flagging that the NEXT upgrade would silently
legitimize that exact file — a one-line "expect git to show
bootstrap-1.7.0.py unmodified on the v1.7.1 hop" would have saved this
session a verification detour. System improvement: upgrade-lane cards
should carry a standing "expected artifacts next hop" stanza — it turns
each card into the next session's regression fixture.

## ⚑ Flags

- Deviation, directed (Q-0261.3): `control/status.md` `kit:` line NOT
  updated this session — the checklist step is deliberately skipped; the
  lane's own next heartbeat records `kit: v1.7.1`.
- Deviation from generic convention, deliberate (same as
  v1.2.0/v1.6.0/v1.7.0): auto-merge armed as the LAST step after this
  card flipped complete — this repo's `check --strict` runs in the
  non-required `checkers` job, so a born-red card cannot hold auto-merge
  here (#44 lesson).
- Local-only: two `check`-run guard-fire lines appended to
  `.substrate/guard-fires.jsonl` were NOT committed (pre-existing stamp
  findings, not upgrade artifacts; kept the PR kit-upgrade-shaped).
