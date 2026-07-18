# 2026-07-18 — D1 render band: bump Pillow 11.3.0 → 12.3.0 (security)

> **Status:** `complete`
>
> Flipped `in-progress` → `complete` as the deliberate LAST commit (per
> `.sessions/README.md`), releasing the born-red `substrate-gate` HOLD. First
> commit was this card alone (held the gate red); the bump + lock regen landed
> in the second commit; this flip is the last.

- **📊 Model:** opus-4.8 · high · security-bump

## Goal

Remediate a live vulnerability shipped to `main`: D1 Slice 1 (#560) landed
`pillow==11.3.0` in `requirements.lock`, and #560 auto-merged before the
follow-up security fix could push — `pip-audit` runs in `ci.yml` but is **not a
required gate**, so the red check did not block the merge. Every Pillow 11.x
release carries 14 PYSEC advisories fixed only in `>=12.3.0`. Bump to
`pillow==12.3.0` (the first version clearing all 14) and regenerate the lock,
honoring the authorized render-band Pillow decision's intent (adopt Pillow)
while satisfying the security gate.

## Scope

- `requirements.txt` — `Pillow>=11,<12` → `Pillow>=12.3.0,<13`.
- `requirements.lock` — regenerated (`pip-compile --generate-hashes
  --strip-extras -o requirements.lock requirements.txt`) so `pillow==12.3.0` is
  hash-pinned; a leaf dep, no transitive additions.
- Re-verify `sb/kernel/render/` against the Pillow 12.x imaging API.

## Deliver

- `requirements.txt` (`Pillow>=12.3.0,<13`) + regenerated `requirements.lock`
  (`pillow==12.3.0`, hash-pinned). **No `sb/` source change** — the render
  engine is version-stable across the 11→12 boundary.

## Verification

- `pip-audit -r requirements.lock --require-hashes --disable-pip` → **"No known
  vulnerabilities found"** (verbatim) on `pillow==12.3.0`. Same command against
  the pre-bump lock reported the 14 PYSEC advisories that motivated this PR.
- `python3 tools/check_lockfile_fresh.py` → `OK (34 pinned dists, 1102 hashes)`;
  `--regen` → `OK (…, regen-verified)` — the lock is `pip-compile
  --generate-hashes --strip-extras` byte-for-byte reproducible.
- `python3 -m pytest -q --ignore=examples` → **3481 passed, 29 skipped, 1
  warning in 66.85s** (the pre-existing `examples/` plugin-example collection
  gap is excluded per the standing note). Render band in isolation: **36
  passed** on Pillow 12.3.0.
- **11→12 API re-verification:** the engine's imaging surface — `Image.new`,
  `Image.open`, `.convert`, `.resize`, `.paste`; `ImageDraw` `ellipse` /
  `rounded_rectangle` / `rectangle` / `text` / `textlength`; `ImageFont.truetype`
  / `load_default`; PNG+JPEG `save` — is unchanged across the boundary. No
  deprecated-API removal touched the engine; **zero code change required**.

## Deviation ledger

- **Pillow bound `<12` → `>=12.3.0,<13`** (deviation from the authorized
  render-band Pillow decision's `<12` bound). The decision named `>=11,<12`,
  but all 11.x is uniformly vulnerable (14 PYSEC advisories fixed only in
  `>=12.3.0`), the fix exists only in the 12.x major, and the mandatory
  `pip-audit -r requirements.lock --require-hashes` gate (ci.yml) has no
  allowlist configured. `>=12.3.0` is the only bound honoring the decision's
  INTENT (adopt Pillow for the render band) while passing security. Flagged for
  the owner: the `<12` intent is superseded by security necessity, not
  preference — worth a one-line update to the decision's home doc when next
  reconciled.

## 💡 Session idea

The root cause of this whole remediation is process, not code: `pip-audit`
lives in `ci.yml` but is **not one of the six required named gates**, so a lock
carrying a known-vulnerable dist can auto-merge on green (exactly what #560
did). **Guard recipe:** either (a) add a `pip-audit` job to
`.github/workflows/named-gates.yml` (or fold a `--require-hashes` audit into the
existing `manifest-validate` gate, the way `check_escape_hatches` rides inside
it) so a vulnerable lock is a *required* red; or (b) add a
`tools/check_lock_advisories.py` that runs at merge-tree re-validation and fails
when `requirements.lock` introduces a dist with an open advisory — anchor it to
the same lock the `lockfile` job already parses. Without one of these, the next
vulnerable pin merges the same silent way this one did.

## ⟲ Previous-session review

Reviewed `.sessions/2026-07-18-d1-render-band-slice1.md` (the `origin/main` HEAD
at branch time, #560 — my own immediately-prior session). It landed the D1
render-band scaffold and adopted Pillow, but its `<12` bound is exactly what
this session had to correct: the scaffold PR's own deviation ledger *predicted*
this (the follow-up bump commit I pushed there never made it into main because
#560 auto-merged first). The lesson carried forward: a security-material dep
adoption should raise its bound to a pip-audit-clean version **in the adopting
PR itself**, before the first green auto-merge — not as a follow-up commit that
races the lander. This card closes that gap on main and files the process-guard
idea (above) so the race can't recur silently.

## Close-out

- **PR #561** — https://github.com/menno420/superbot-next/pull/561 (branch
  `claude/d1-pillow-12-security-bump`, base `main`).
- Commits: born-red card `b21a781`, bump `67341b9`, this flip.
- Files: `requirements.txt`, `requirements.lock` (pins `pillow==12.3.0`), this
  card. No `sb/` source change. pip-audit clean; lock regen-verified; full
  `pytest --ignore=examples` green (3481 passed / 29 skipped).
- Server-side lander merges on green (the six required named gates).
