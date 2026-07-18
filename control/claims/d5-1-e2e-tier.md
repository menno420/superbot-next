# claim: D5.1 — in-process e2e adapter test tier (initial slice)

- **branch:** `claude/d5-1-e2e-tier-initial`
- **scope:** Stand up the D5.1 in-process e2e adapter test tier (the
  discord-installed variant per `docs/design/D5-e2e-test-harness.md`): a
  `tests/e2e/` directory + fixture that boots the real bot in-process on the
  existing parity `Harness` + real Postgres (reusing
  `tests/integration/conftest.py`'s machinery) and re-points the panel
  presenter + channel emitter at the REAL `sb/adapters/discord/*` modules
  (`build_embed`/`build_view`, `DiscordChannelEmitter`) so an exemplar command
  is driven end-to-end through real `discord`/`app_commands`/`ui` types. INITIAL
  slice: the tier scaffolding + 1–3 representative flows (help/utility read +
  the S11 egress trust policy) on stable, already-well-covered domains; broad
  per-domain coverage is explicit follow-up. Hermetic — no LIVE gateway/token
  (only the D5.2 LIVE tier is owner-gated; not touched here). Rides the
  `golden-parity` CI job's discord+Postgres environment.
- **date:** 2026-07-18
