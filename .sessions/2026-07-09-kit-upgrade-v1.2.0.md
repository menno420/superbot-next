# 2026-07-09 — vendored kit upgrade to substrate-kit v1.2.0 + engagement render

> **Status:** `in-progress`

## Scope

Second real-world run of the kit's `upgrade` verb (first was v1.0.0, PR #46):
move the vendored `bootstrap.py` from v1.0.0 to the released v1.2.0
(sha256 `258ab02aa54811d91b013f67a15d4bf13e8fc917421434746dd3ca26bc59098c`,
verified against `release.json`), then walk the new KL-7 engagement gate to
GREEN — this repo was fleet-flagged as stranded (9 planted docs still under
the adopt-time UNRENDERED banner with 8 unfilled `${...}` interview slots).
Plan: upgrade per §4.3 (archive-first, hash-classified doc report), verify
the two fixes filed from this repo's #46 run (from-version honesty +
input self-cleanup), answer the 8 open interview slots with real values
derived from this repo, `render --live`, end at `check --strict` exit 0.

- **📊 Model:** claude-fable-5 · high · mechanical refactor
