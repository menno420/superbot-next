# Session — D5.1 in-process e2e adapter test tier (initial slice)

**Status:** in-progress

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

(to be filled at close-out)
