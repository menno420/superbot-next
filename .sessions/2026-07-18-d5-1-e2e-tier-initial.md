# Session — D5.1 in-process e2e adapter test tier (initial slice)

> **Status:** `complete`

- **📊 Model:** opus-4.8 · high · test writing

## Order

Build + land an INITIAL, tightly-scoped slice of **D5.1 — the in-process e2e
adapter test tier** (discord-installed variant), authorized by the D5
decision-ready doc (`docs/design/D5-e2e-test-harness.md`) and PR #571 (tier-A
pick resolved = discord-installed, agent-decidable; only the D5.2 LIVE tier is
owner-gated). Decide-and-flag build.

## What this slice is

A MINIMAL but REAL in-process e2e tier that proves the concept: it boots the
real bot in-process on the existing parity `Harness` + real Postgres (reusing
`tests/integration/conftest.py`'s machinery) and **re-points the panel presenter
and channel emitter at the REAL `sb/adapters/discord/*` modules** — the ~19
adapter modules the golden-parity fake transport deliberately skips (D5 doc P1).
An exemplar command is then driven end-to-end through real
`discord`/`app_commands`/`ui` types and asserted on the materialized egress.

## Scaffolding

- `tests/e2e/conftest.py` — the tier fixture: `boot_e2e_harness()` reuses
  `tests/integration/conftest.py:boot_harness()` (real-Postgres `Harness.start`)
  and installs a `RealAdapterRecorder` that swaps the parity presenter/emitter
  for the real discord adapter (`build_embed`/`build_view`,
  `DiscordChannelEmitter`) over recording fakes. Skips (never fails) when
  `discord` or Postgres is unavailable — the guarded-absence discipline, same as
  the integration tier.

## Exemplar flows (initial — NOT exhaustive)

1. `!help` prefix command → real `panel_view.build_embed`/`build_view`: asserts a
   real `discord.Embed` (`help.home`, title "📚 Help Menu", 6 fields) + a real
   `PanelRuntimeView` (`discord.ui.View`) carrying a `Select`.
2. `!ping` utility command → real `build_embed`: asserts a real `discord.Embed`
   (`utility.pong`, title "🏓 Pong!").
3. S11 egress trust policy → real `DiscordChannelEmitter` + `allowed_mentions_for`:
   UNTRUSTED `@everyone` → real `discord.AllowedMentions.none()` + neutralized
   body; SYSTEM allowlist → real `discord.Object` user mention.

## Flags

- Decide-and-flag: this is the agent-decidable in-process tier per the D5 doc;
  the owner may reshape the tier's conventions. Only the D5.2 LIVE tier is
  owner-gated (not touched here).
- Breadth is explicit follow-up: this slice stands up the tier + proves it with a
  few exemplars. Per-domain e2e coverage (and the D5.2 LIVE tier) are separate
  slices.

## Verification

- `python3 -m pytest -q --ignore=examples` (Postgres + discord present) →
  **3527 passed, 2 skipped** (the 2 skips are pre-existing inverse-path guards:
  `test_db_pool` / `test_misfire` — unrelated). All 4 new `tests/e2e/` tests
  PASS by name, not skip.
- `tests/e2e -q` alone → **4 passed**.
- Guards clean (0 fires): `check_namespace`, `check_symbol_shadowing`,
  `check_config_usage`, `check_no_skip`.
- No dependency change — `requirements.lock` untouched, so pip-audit gate n/a.
- Postgres provisioned the CI-shaped way: `pg_ctlcluster 16 main start` +
  `python3 tools/setup_local_env.py` (parity role/DB, DATABASE_URL/SB_DATA_PLANE
  /SB_TEST_DB_HOSTS). discord-py 2.7.1 already in the runtime lock.

## ⟲ Previous-session review

Predecessor in this thread: the D5 decision-ready refinement (#571) that
resolved the tier-A pick as agent-decidable = discord-installed and flagged the
in-process tier as "buildable now with no owner input." That call held up under
build: `requirements.lock` already ships `discord-py==2.7.1` and
`tests/integration/conftest.py` already boots the same `Harness.start()` against
a service Postgres, so the tier landed with **zero `sb/` source edits** and no
owner input, exactly as flagged. One honest gap the refinement didn't surface:
the parity `Harness` bypasses the adapter at the *presenter/emitter* seam, so the
real exercise had to be wired by re-installing those two ports — a clean swap,
but worth naming for the next slice.

## ⟲ This-session review

The recorder drives the real `panel_view.build_embed`/`build_view` (the real
`discord.Embed`/`ui.View` construction — P1's "real panel-view render") and the
real `DiscordChannelEmitter` (S11 mass-ping fence), which is the highest-signal
initial exercise of the un-driven adapter band. It does NOT yet drive the
`DiscordPanelPresenter` dispatch *branches* (channel_anchor vs interaction-reply
vs followup) — that needs a discord-shaped recording `origin` threaded through
the harness dispatch, a natural next slice. Kept the exemplar count at 3 to make
the tier legible rather than chasing breadth; per-domain coverage is follow-up.

## 💡 Idea

A `--record` bridge (D5.3): have the e2e recorder dump each captured
`(RenderedPanel → real discord objects)` pair into a fixture the next hermetic
run replays — turning an e2e exercise into a cheap adapter-surface regression,
the convergence point with golden-parity the D5 doc sketches.
