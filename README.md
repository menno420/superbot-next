# superbot-next

The ground-up rebuild of **superbot**, a production Discord bot.

Built fresh — not forked — from the canonical rebuild plan, adopting the portable workflow
substrate from [`substrate-kit`](https://github.com/menno420/substrate-kit) rather than copying the
old bot's code. The live `superbot` repo is the behavioural reference for golden-parity validation,
not the starting point.

**Status:** rebuilt through all seven port bands (41 subsystems, 276 commands, hash-pinned
manifest snapshot); boots to RUNNING on real PostgreSQL; port bands 1–4 live-tested in a real
test guild, band 5 (governance/roles/platform) live-testing in flight. Live truth:
[`control/status.md`](control/status.md).

**Reading the CI:** the `golden-parity` **report** job is **red by design** (red-until-parity
dashboard, never a required check) — read [`docs/status/README-first.md`](docs/status/README-first.md)
**before** interpreting any red here.
