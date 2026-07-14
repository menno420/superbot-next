# superbot-next

The ground-up rebuild of **superbot**, a production Discord bot.

Built fresh — not forked — from the canonical rebuild plan, adopting the portable workflow
substrate from [`substrate-kit`](https://github.com/menno420/substrate-kit) rather than copying the
old bot's code. The live `superbot` repo is the behavioural reference for golden-parity validation,
not the starting point.

**Status** (re-stamped 2026-07-14, EAP close-out): rebuilt through all seven port bands
(hash-pinned manifest snapshot; the 2026-07-13 completeness sweep counts 413 commands and
~200 panels across 49 subsystems with zero silent gaps —
[`docs/status/completeness-table-2026-07-13.md`](docs/status/completeness-table-2026-07-13.md));
boots to RUNNING on real PostgreSQL; port bands 1–4 live-tested in a real test guild; further
live-testing is parked owner-side (test-bot token — ORDER 001, heartbeat ⚑6). Current lane:
EAP close-out + the owner click-sweep (WP stack, DROP-list ratification). Live truth:
[`control/status.md`](control/status.md); week-in-review:
[`docs/audits/eap-project-audit-2026-07-14.md`](docs/audits/eap-project-audit-2026-07-14.md).

**Reading the CI:** the `golden-parity` **report** job — born red-by-design as the
red-until-parity dashboard — went **live green on 2026-07-13** (full-corpus parity: 484/484
goldens, 51/51 subsystems; run 29238825392). A red `report` is now a **real regression
signal**, not the expected state. It stays a non-required check; orientation:
[`docs/status/README-first.md`](docs/status/README-first.md).
