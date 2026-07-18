# 2026-07-18 — D1 render band: bump Pillow 11.3.0 → 12.3.0 (security)

> **Status:** `in-progress`
>
> Born-red first commit — this card alone holds the `substrate-gate` red while
> the security bump lands in the following commit; the `in-progress` →
> `complete` flip is the deliberate LAST step.

## Goal

Remediate a live vulnerability shipped to `main`: D1 Slice 1 (#560) landed
`pillow==11.3.0` in `requirements.lock`, and #560 auto-merged before the
follow-up security fix could push — `pip-audit` runs in `ci.yml` but is **not a
required gate**, so the red check did not block the merge. Every Pillow 11.x
release carries 14 PYSEC advisories fixed only in `>=12.3.0`. This PR bumps to
`pillow==12.3.0` — the first version clearing all 14 — and regenerates the
lock. It honors the authorized render-band Pillow decision's intent (adopt
Pillow for the render band) while satisfying the security gate; the decision's
literal `<12` bound is superseded by security necessity (flagged below).

## Scope

- `requirements.txt` — `Pillow>=11,<12` → `Pillow>=12.3.0,<13`.
- `requirements.lock` — regenerated (`pip-compile --generate-hashes
  --strip-extras`) so `pillow==12.3.0` is hash-pinned; a leaf dep, no
  transitive additions.
- Re-verify the `sb/kernel/render/` engine against the Pillow 12.x imaging API
  (fix any 11→12 breakage).

No `sb/` source change expected — the render engine's imaging surface is
version-stable across the 11→12 boundary (re-verified). If any 11→12 API
breakage surfaces, it is fixed here and noted.

## Plan

1. This born-red card (first commit) — holds the gate red.
2. The `requirements.txt` bump + regenerated `requirements.lock` (+ any engine
   fix 11→12 requires).
3. Flip to `complete` (last commit) once verification is captured.
