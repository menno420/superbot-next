# Requests to the IDEA project — feature expansions and net-new proposals wanted (2026-07-12)

> **Status:** `plan`
>
> Cross-project request doc, addressed to the sibling **IDEA** project on
> the owner's directive of 2026-07-12: expand existing features and propose
> new ones. Routing is via the owner / fleet manager (see
> [`README.md`](README.md)). Current-state claims below were re-verified
> against this repo at main `764a393` (#260); the deeper evidence trail is
> `docs/review/program-review-2026-07-12.md` (the 2026-07-12 program
> review).

Format per area: **current state (cited) → what expansion/ideas are wanted
→ constraints.** Standing constraints for every proposal: parity discipline
(goldens are the read-only acceptance oracle for ported surfaces,
`parity/README.md`), and the kernel/domain layer map (`sb/__init__.py` —
spec/namespace are leaves, kernel never imports domain, adapters import
kernel+spec, `sb/app` is the sole composition root).

---

## IDEA-REQ-1 — Web-based bot editing (control-API bridge + dashboard)

**Current state.** The only HTTP surface is the read-only health server —
four GET routes, no POST (`sb/adapters/http/health.py`; the package
contains only `__init__.py` + `health.py`). The bridge is already
deferred-named successor work in the decision ledger
(`docs/decisions.md:311`, band-5 slice 3): `sb/adapters/http/control.py` —
ping/authority/manifest/settings GET+POST fronting the audited seams, the
sliding-window write limiter, hmac compare — ported from the old bot's
working `disbot/control_api.py`, with the dormant `CONTROL_API_TOKEN`
SecretSpec (`sb/spec/config.py:234-238`) and its credential-registry row
already landed. The old bot additionally had a Discord-OAuth FastAPI
dashboard (`dashboard/`) that edited per-guild settings live.

**Wanted.** Expansion ideas beyond the 1:1 port: what *should* be
web-editable (settings, command access, help appearance, plugin
enable/disable?); dashboard UX for a single-owner hobby deployment; auth
model (OAuth vs token vs both); whether the dashboard is a separate service
or rides the bot's aiohttp app; a read-only public status page story.

**Constraints.** Every write must front the existing audited workflow
seams — no new write path (the settings scalar lane and command-access
lanes already exist); env config is frozen at boot and stays
non-web-editable by design; manifests are compiled code — web may read the
snapshot, never write it.

## IDEA-REQ-2 — Rich interactive UI v2

**Current state.** The v1 read-views are a ledgered regression against the
shipped bot: the old bot's button-grid operator hubs, settings
panel-actions, help overlays, setup wizard flows, and PNG rank cards are
all captured in goldens but v1 ships flat declaration-first read-views —
the "successor-boundary render drift" class, with the interactive
BrowserView engine named-but-unbuilt
(`docs/status/rebuild-completion-report-2026-07-09.md` §4.4, flag 41;
program review Q2). Meanwhile the band-7 AI surface already ships live
choosers, pagers, settings widgets, and modal editors — so the interaction
machinery exists in one corner of the product.

**Wanted.** A v2 interaction design: the BrowserView/browse engine shape;
which hubs deserve buttons vs slash-first flows; how the band-7
chooser/widget patterns generalize to the operator hubs; net-new UI ideas
the old bot never had (the goldens pin the old bot's UI as the *floor*,
not the ceiling).

**Constraints.** Ported surfaces replay byte-exact in the required gate —
UI changes on golden-pinned surfaces need the corpus-integrity lane
(reviewed re-mints), not silent drift; interaction depth is nearly
un-goldened today (1 click + 3 modals in 468 cases — see the sim-lab
request doc), so v2 should land with its own interaction goldens.

## IDEA-REQ-3 — Deploy packaging + cutover story

**Current state.** Zero deploy artifacts exist — no Dockerfile,
docker-compose, railway config, fly.toml, or Procfile anywhere in the repo
(program review Q4 item 2, searched at the audited HEAD); Railway is the
assumed host in prose only (`sb/spec/config.py:220-221`). The composition
root is explicitly the "CUT-1 test-mode main()" (`sb/app/main.py:1`);
CUT-2/CUT-3 (token swap, rollback window) are unexecuted checklist items
(`docs/status/rebuild-completion-report-2026-07-09.md` §3), and no cutover
work is scheduled anywhere in `control/`.

**Wanted.** Packaging proposals (container vs Railway-native; how the
migrations chain and the health server fit the deploy lifecycle); a
CUT-2/CUT-3 runbook shape (token swap choreography, rollback window,
old-bot decommission); process-supervision story (restart policy is
currently the unpackaged orchestrator's job); secrets/rotation flow at
deploy time.

**Constraints.** The rollback playbook forbids cutover without a fresh
restore witness (`docs/operations/rollback-playbook.md:29-30` — see
IDEA-REQ-6); prod boot rails (`SB_DATA_PLANE=prod` + attestation) are
declared but never exercised — a proposal should include the first
prod-plane boot rehearsal.

## IDEA-REQ-4 — Onboarding / quickstart UX

**Current state.** No quickstart or getting-started doc exists anywhere in
the repo (searched `docs/` + `README.md`); the root README is agent/CI
oriented and stale (it says 41 subsystems / 276 commands; measured HEAD is
48 / 396 — program review Q2, ledger-staleness item). Environment setup
exists only as the kit hook `scripts/env-setup.sh`. In-product, the setup
wizard subsystem is ported and gate-green (setup 9/9 goldens) but its rich
wizard flow is part of the flag-41 read-view regression.

**Wanted.** Two onboarding stories: (a) operator onboarding — from clone
to a booted bot on the test plane in N steps, doc + script; (b) guild
onboarding — what a fresh guild's first 10 minutes look like (setup
wizard v2, sensible defaults, a "what can this bot do" tour). Plus ideas
for keeping the README's status head honest automatically (it drifted
within three days).

**Constraints.** Setup flows are golden-pinned where ported; boot rails
(data-plane allowlist, intent markers) are deliberate friction that
onboarding docs should explain, not remove.

## IDEA-REQ-5 — Plugin ecosystem directions

**Current state.** The hello-world plugin path is proven end-to-end: the
contract doc is `docs/game-plugin-contract.md`; the in-tree example lives
at `examples/superbot-plugin-hello/`; the external repo
`menno420/superbot-plugin-hello` was seeded 2026-07-12 at commit
`bbaccec5` (the ORDER-014 record in `control/status.md`); host-side
discovery admits installed plugins hash-pinned via `plugins.lock.json`;
and the live render is proven — `!hello` posted a real plugin panel into
the test guild (`docs/status/testing-report-2026-07-09.md`, step-4 row).
Dedicated game repos (mining; exploration/D&D) are the declared consumers
(`control/inbox.md` ORDER 002 context).

**Wanted.** Ecosystem ideas: which kernel seams to expose next beyond the
granted set (economy, game-XP, EffectiveStats, panels — what about
scheduler lanes, AI tasks, settings namespaces?); plugin
versioning/compatibility policy against a moving host; a
registry/marketplace story even at hobby scale (even just "a curated list
+ lockfile recipe"); developer experience for the game repos (test
harness, golden capture for plugin surfaces); whether deep-game ports
(deep mining, poker, creature battles — the parked ~40-golden surface,
program review Q2) should land as plugins instead of in-tree subsystems.

**Constraints.** Plugins consume seams, the host keeps ownership
(audited write path, manifest compilation, hash-pinned admission); a
plugin's manifest compiles and pins like in-tree subsystems — proposals
must not create an unaudited side door.

## IDEA-REQ-6 — Backup / disaster-recovery operational story

**Current state.** Both workflows exist but have never operated: they gate
on the owner-set `BACKUP_ENABLED` variable
(`.github/workflows/backup-db.yml:57`,
`.github/workflows/restore-verify.yml:45`); measured via the GitHub API at
the program review's audited HEAD, **all 4 scheduled backup runs concluded
`skipped` and restore-verify has ZERO runs ever** (program review Q4
item 3). The rollback playbook's own rule — a stale restore witness means
"do not cut over" (`docs/operations/rollback-playbook.md:29-30`) — has
never been satisfied.

**Wanted.** An operational design the owner can turn on with one click:
retention policy, restore-drill cadence, off-platform copy story, alerting
when the restore witness goes stale, and how backup/restore interacts with
the migrations checksum chain. Plus: what minimal evidence should exist
before cutover (one green restore-verify? a timed restore drill?).

**Constraints.** The gate variable is deliberately owner-only — proposals
should assume agent work stops at "armed and documented", with the flip
itself an owner action; test-plane vs prod-plane data separation rails
must survive any restore path.

---

## Net-new ideas — explicitly invited

Per the owner's ask, the IDEA project is invited to propose features with
**no current-state anchor at all** — things neither bot has. Seed
directions the repo's own evidence hints at (each traceable above): a
telemetry/usage sidecar (usage-weighted coverage is a named follow-up in
`parity/COVERAGE.md`), long-horizon economy events (seasons, resets —
pairs with the sim-lab economy request), cross-guild features, and
AI-native surfaces beyond the ported stack once the live key lands. Wilder
proposals welcome; the constraints sections above are the only hard
fences.
