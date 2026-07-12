# 2026-07-12 — ORDER 014: seed superbot-plugin-hello, flip ORDER 002 done, drop OWNER-ACTION 2

> **Status:** `complete`

- **📊 Model:** fable-5 · high · control/distribution (Q-0194)

## Scope

Execute ORDER 014 (inbox @ `97aa41e`, P1, filed by the fleet manager):
the one sanctioned out-of-repo write — seed the owner-created, verified-
empty `menno420/superbot-plugin-hello` — then flip ORDER 002 done via
`orders: done=` and drop the OWNER-ACTION 2 ask. Control-only in this
repo: `control/status.md`, this card, one telemetry row.

## What shipped

1. **Seed (out-of-repo, sanctioned):** plugin repo root-commit
   `bbaccec50aa21fc744b8d37ecded8666365a63a1` on `main` — the in-tree
   `examples/superbot-plugin-hello/` moved VERBATIM (5 files) per
   OWNER-ACTION 2's HOW and `docs/game-plugin-contract.md`'s preamble,
   plus `substrate.config.json` pinning `kit_version` `1.13.0`
   (mirroring the host's pin file/format at substrate.config.json:47;
   the relay's "expected v1.12.1" was stale — #251 `559a0d8` upgraded
   the pin before this order fired). Emptiness re-verified before
   writing (empty clone, zero refs at origin).
2. **Verbatim proven, pin intact:** GitHub Contents API blob SHAs at
   HEAD equal `git hash-object` of the in-tree files (README.md
   `3959258e`, pyproject.toml `4e3a8b46`, `__init__.py` `0955ef91`,
   manifest.py `3ea3145c`, tests/test_manifest.py `a9f23e20`) — so the
   committed `plugins.lock.json` manifest-hash pin
   (`sha256:06023075…93a0`) stays valid with NO re-pin, exactly as the
   ask predicted.
3. **Control flips:** `orders:` acked= gains 014, done= gains 002 and
   014 (the 002 flip is ORDER-014-DIRECTED); OWNER-ACTION 2 block
   removed (done-when: "the ask is gone"; items 3/5/6 keep their
   numbers); blockers + ⚑ needs-owner lines brought current; full
   "ORDER-014 round 2026-07-12" record added with per-claim citations.
4. **Deliberate omissions, ledgered:** no LICENSE seeded (the host repo
   carries none — mirrored, not invented); the ORDER 002 "registers and
   renders in the test guild" live leg NOT re-run this round — named as
   an honest follow-up in the status record.

## 💡 Session idea

The separate-repo install → `tools/plugin_pin.py` → live registration
drive is now one bounded live-session slice: `pip install --no-deps
git+https://github.com/menno420/superbot-plugin-hello@bbaccec5`, boot,
drive `!hello` in the test guild — it would convert the ORDER-014-directed
002 flip into gateway-evidence, and doubles as the reference recipe the
mining/exploration game repos will copy.

## ⟲ Previous-session review

(Covers `.sessions/2026-07-12-program-review.md`, the most recent
completed card at branch time.) Its method held up as a template here:
re-measure at HEAD instead of trusting relayed state — applied twice
this session, catching the stale kit-pin expectation (v1.12.1 relayed
vs v1.13.0 actual at substrate.config.json:47) and re-verifying the
plugin repo's emptiness before writing rather than trusting the order's
two-day-old 409. Its Top-10 gaps list did not name the plugin-repo
seed (it was OWNER-ACTION-gated, not builder-actionable, at audit
time); the gate opened via ORDER 014 and closed here.

## Close-out

Both halves landed: the plugin repo seeded and API-verified at
`bbaccec50aa21fc744b8d37ecded8666365a63a1` (6 files, listed above), and
the control PR carrying the status flips + this card + the telemetry
row merged on the 6 required checks green (`report` red-by-design,
non-required). No code, parity data, docs/, or inbox writes; no other
lane's files touched. The one follow-up is named in the 💡 idea and in
the status record: the live registration drive from the separate-repo
install.
