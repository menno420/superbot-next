# Owner-decision agenda — 2026-07-18

> **Status:** `owner-guidance`
>
> The consolidated morning agenda. It gathers **every "open question for the
> owner"** scattered across tonight's 2026-07-18 design docs — plus the standing
> owner-gated items in the completeness snapshot — into one prioritized list.
> Each row is a **decision that unblocks a build-slice**: answer it and a
> well-scoped slice becomes dispatchable. Answers can be given **inline in this
> doc** (edit the block) or in the **inbox** — either works.
>
> This is an agenda, not a re-explanation: each block links to the source design
> doc for the full argument. Every item carries a **real default recommendation**
> to react to (agree = fastest path); where a genuine judgement call needs owner
> context that no agent has, the block says so plainly.

Sources gathered: [D4 observability](D4-observability-surface.md) ·
[D2 minigame framework](D2-realtime-minigame-framework.md) ·
[B10 route-origin](B10-panel-route-origin.md) ·
[S security](S-security-rotation-and-least-privilege.md) ·
[O ops](O-ops-migration-backup-restore-rollback.md) ·
[D5 e2e/live-guild harness](D5-e2e-test-harness.md) ·
[B8 ux_lab wings](B8-ux-lab-wings.md) ·
[R resilience/delivery/db](R-resilience-delivery-and-db.md) ·
[completeness snapshot](../status/completeness-table-2026-07-18.md)
(C4 · A-items/ai/hermes · btd6). Every decision area now links to its source
design doc; rows 22 (B8), 24 (D5) and 25 (R) were upgraded from their source-
pending placeholders to the docs' actual open-questions.

## Answer-and-go summary

Ordered by leverage — the earlier the row, the cheaper the answer relative to
what it unblocks. `[?]` in the Rec column = a call that genuinely needs owner
context; the block explains why.

| # | Decision | Recommendation | Unblocks |
|---|---|---|---|
| **Tier 1 — quick high-leverage** |
| 1 | Readiness backpressure threshold | 60 s `ConfigSpec`, soft-degraded first | D4.3 `/readyz` + outbox-depth gate |
| 2 | `prometheus_client` in runtime lock | Confirm present + fail-closed boot smoke | D4.1 render smoke (whole metrics surface) |
| 3 | Required-at-boot secret manifest | Confirm the FAIL_FAST trio | S.1 malformed-secret shape guard + CI assertion |
| 4 | Integrity fixture ownership | `tests/fixtures/`; economy/treasury/xp/karma + audit slice | O.1/O.2 row-level integrity |
| 5 | Restore/rollback drill cadence | Per-PR seeded fixture + weekly real-artifact | O.1/O.2 triggers |
| 6 | Metric cardinality budget | Set a ceiling, warn-only before hard gate | `check_metric_cardinality` fleet ceiling |
| **Tier 2 — infrastructure (one answer cascades)** |
| 7 | Metrics backend + `/metrics` exposure/auth | Railway-native private-net scrape, no auth on private net | D4.2 manifest + scrape + alert routing |
| 8 | Secret store / rotation mechanism | Railway env vars now; vault later | S.2 runbook + `RotationProvider` install |
| 9 | Acceptable rotation downtime | One bounded redeploy behind `/ready` (no hot-swap seam) | S.2 drain-and-reboot runbook |
| 10 | Backup source + turn the net ON | Keep GH-Actions `pg_dump`; set `BACKUP_ENABLED=true` now | O.1 real-artifact leg; the whole RPO contract |
| 11 | Throwaway restore DB location | CI `postgres:18` service container | O.2 drill |
| 12 | Structured-log format + drain | JSON → Railway log drain | D4.4a formatter + stream redaction |
| 13 | Relay-health alert delivery path | `OperatorAlert` sink now; Alertmanager once backend lands | D4.1 alert wiring |
| **Tier 3 — scope / priority calls** |
| 14 | B10 route-origin — worth the engine cost? | Ship engine signal (opt-in, zero churn); defer role opt-in | B10.1–B10.3 vs a cheaper `parent=` fix |
| 15 | B10 scope | `role.hub` only first | B10.4 (one golden) |
| 16 | B10 back depth | Single-level (match oracle) | keeps golden matrix flat |
| 17 | B10 golden/minting/label mechanics | Click-time-parsed origin family; capture differing origins; `HUB_NAV_LABELS` + `server_management` entry | B10.3 harness origin dimension |
| 18 | D2 first target game | Reflex/timing casino minigame | D2.2 (proves the primitive) |
| 19 | D2 refactor fishing now? | Leave as reference impl (D2.3 optional/later) | protects fishing's byte-pinned goldens |
| 20 | D2 primitive home | `sb/kernel/panels/minigame.py` | D2.1 extraction |
| 21 | D2 window floor / multi-round / turn-timeouts | Single-shot first; platform window floor; defer blackjack/rps countdowns | D2.1 API shape |
| 22 | B8 ux_lab — port the dev surface at all? | LOW priority; render-only for the 3 special wings | B8 wing slices (no user-facing gap) `[?]` |
| 23 | S.3 least-privilege trim (intents + invite perms + DB role) | Yes: explicit intents, minimal invite scope, DDL/DML split | S.3 intent trim + role provisioning |
| 24 | D5 e2e/live-guild harness shape | Fake in-process PR tier (byte-assert); secret-gated LIVE tier (shape-assert, degraded-health signal not a merge-block); automated runs → unsigned `verified_live` lane | D5 harness slices `[?]` |
| 25 | R resilience bounds | Move retry to the delivery-ACK boundary (bounded backoff + 90d DLQ already ship); DB reconnect + breaker + bounded boot-retry; explicit refuse-write copy | R delivery-hardening slices `[?]` |
| **Tier 4 — access / credential gates (owner must provision)** |
| 26 | AI surface creds — `ANTHROPIC_API_KEY` / `CLAUDE_ROUTINE_*` | Provision to unblock; else keep honest refusals | A1/A2/A3 + ai NL lane + hermes egress |
| 27 | btd6 NK data account/ingestion | Provision Ninja-Kiwi source or keep named-successor refusal | btd6 live bracket standings |
| **Tier 5 — posture confirmations** |
| 28 | C4 tournament-TOCTOU | Keep accepted-posture (match oracle + boot-sweep recovery) | closes the standing C4 owner-gate |
| 29 | Rollback scope — schema vs data | Confirm forward-only + data-plane reverse-import is permanent | freezes O.2 drill semantics |
| 30 | Deploy rollback in scope? | Owner Railway-console action; only **data** rollback drilled | scopes O.3 runbook |
| 31 | Emergency-swap secret posture | Keep `ON_COMPROMISE`/`MANAGED` + a documented owner-driven lane | S.2 posture rows |

---

## Tier 1 — Quick high-leverage
*A small answer (a number, a yes/no, a confirmation) unblocks a cheap, contained slice.*

### 1 — Readiness backpressure threshold
- **Decision:** What `outbox_pending_age_seconds` value flips `/readyz` to 503, and is backpressure a *hard* 503 (stop routing) or a *soft* degraded signal that still serves 200?
- **Options:** A) 60 s hard 503 · B) 60 s soft/degraded (still 200) · C) a different number.
- **Recommendation:** **60 s as a `ConfigSpec` override, soft-degraded first** — start observable-but-non-blocking so a wedged relay is visible before it can pull a replica out of rotation; promote to hard 503 once the number is trusted in prod.
- **Unblocks:** D4.3 (`/readyz` alias + outbox-depth readiness — self-contained in the http adapter).
- **Source:** [D4](D4-observability-surface.md) §Open questions 3.

### 2 — `prometheus_client` in the runtime image
- **Decision:** Confirm `prometheus_client` is in the hash-pinned runtime lock, and should the boot smoke assert its presence (fail-closed) rather than degrade silently to the empty-body `_NoOp`?
- **Options:** A) Confirm present + fail-closed boot smoke · B) Confirm present, tolerate absence (degrade).
- **Recommendation:** **Confirm + fail-closed** — if it is absent `/metrics` serves an empty body *by design*, so the entire observability surface is silently dark; a boot smoke asserting a non-empty exposition is the cheap trapdoor-closer.
- **Unblocks:** D4.1 (arm outbox metrics + render smoke) — the highest-signal, smallest observability slice.
- **Source:** [D4](D4-observability-surface.md) §Open questions 5.

### 3 — Required-at-boot secret manifest
- **Decision:** Confirm exactly which secrets must be present at boot — currently the FAIL_FAST trio `DISCORD_BOT_TOKEN_PRODUCTION`, `DATABASE_URL`, `SB_DATA_PLANE` — vs which stay optional/DORMANT.
- **Options:** A) Confirm the trio as the frozen required set · B) Add/remove a field.
- **Recommendation:** **Confirm the trio.** The posture assignments are already correct but only *incidental*; freezing them as a reviewed manifest turns them into a contract a CI assertion can defend.
- **Unblocks:** S.1 (malformed-secret shape guard + the required-at-boot CI assertion — an **S**-sized, highest-value security slice).
- **Source:** [S](S-security-rotation-and-least-privilege.md) §Open questions 3.

### 4 — Integrity fixture ownership
- **Decision:** Should the seeded row fixture + expected integrity values live under `tests/fixtures/` (owner-reviewable), and which stores are the mandatory value-bearing set beyond economy/treasury/xp/karma?
- **Options:** A) `tests/fixtures/`, set = economy/treasury/xp/karma + an `audit_log` slice · B) a wider mandatory set.
- **Recommendation:** **`tests/fixtures/`, that set + the append-only `audit_log` checksum slice** — the four value-bearing stores are the money rows; `audit_log` proves the append-only spine survived the round-trip.
- **Unblocks:** O.1 + O.2 (row-level restore integrity — "the money rows are all there", not just "boots clean").
- **Source:** [O](O-ops-migration-backup-restore-rollback.md) §Open questions 6.

### 5 — Restore/rollback drill cadence
- **Decision:** Per-PR seeded-fixture drill (gates migration/runner changes) plus a weekly real-artifact proof — is per-PR the right cost, or should the full drill be nightly + `workflow_dispatch` only? And should the restore proof become a **hard** required gate?
- **Options:** A) Per-PR seeded + weekly real-artifact · B) Nightly + dispatch only (keep PRs light) · C) Make restore a hard required gate now.
- **Recommendation:** **Per-PR seeded fixture (fast, deterministic) + weekly real-artifact; NOT a hard required gate yet** — gate migration/runner regressions in the PR where they are introduced, but keep the real-artifact proof off the critical path until it has a green track record.
- **Unblocks:** O.1 (PR-visible restore-verify) + O.2 (drill triggers).
- **Source:** [O](O-ops-migration-backup-restore-rollback.md) §Open questions 3.

### 6 — Metric cardinality budget
- **Decision:** Set an explicit fleet-wide total-series ceiling for the scrape (backend cost control), and should `tools/check_metric_cardinality.py` enforce it as a hard gate?
- **Options:** A) Set a ceiling, warn-only first · B) Set a ceiling, hard gate immediately · C) No fleet ceiling.
- **Recommendation:** **Set a ceiling, warn-only before promoting to a hard gate** — the per-family budgets already exist; a warn-only fleet ceiling surfaces cost drift without red-gating a legitimate new family on day one.
- **Unblocks:** the cardinality-budget half of D4.2 (scrape cost control).
- **Source:** [D4](D4-observability-surface.md) §Open questions 4.

---

## Tier 2 — Infrastructure choices
*One answer cascades into several slices — these are the highest-leverage picks on the page.*

### 7 — Metrics backend + `/metrics` exposure and auth
- **Decision:** Prometheus + Grafana (self-hosted / Grafana Cloud) or the Railway-native metrics / Grafana-Agent path? And is `/metrics` kept private-network-only (no auth, scraped inside the deploy) or exposed publicly behind a bearer/basic auth?
- **Options:** A) Railway-native agent + private-net `/metrics`, no auth · B) Prometheus+Grafana scraping a public `/metrics` behind a bearer token · C) Grafana Cloud agent, private-net.
- **Recommendation:** **Railway-native / Grafana-Agent scraping the private-network `/metrics`, no endpoint auth** — the health server already binds `::`/8080 for Railway private networking, so the lowest-friction posture is an in-deploy scrape with no public exposure to secure. Revisit if a Grafana Cloud dashboard the owner already runs argues for direct public scrape.
- **Unblocks:** D4.2 (scrape manifest shape) **and** the auth posture **and** feeds the alert-delivery pick (#13). One answer, three dependent decisions.
- **Source:** [D4](D4-observability-surface.md) §Open questions 1 + 2.

### 8 — Secret store / rotation mechanism
- **Decision:** Are secrets in Railway env vars only, or is a vault / secret-manager in scope?
- **Options:** A) Railway env vars only (now) · B) External vault / secret-manager.
- **Recommendation:** **Railway env vars now; vault a later track** — the whole S.2 runbook ("set the new env var → redeploy") and the `RotationProvider` install both key off this; env-vars-only matches the current deploy model and keeps the emergency-swap procedure a documented drain-and-reboot rather than a new integration.
- **Unblocks:** S.2 (rotation runbook **and** the CUT-1 `RotationProvider` install).
- **Source:** [S](S-security-rotation-and-least-privilege.md) §Open questions 1.

### 9 — Acceptable rotation downtime
- **Decision:** Is a single bounded Railway redeploy (drain-and-reboot behind `/ready`) an acceptable target for an emergency secret swap, or is true zero-downtime hot-swap required?
- **Options:** A) One bounded redeploy behind `/ready` · B) True zero-downtime hot-swap.
- **Recommendation:** **One bounded redeploy behind `/ready`** — the token is read once from a frozen `Config`, so hot-swap needs a new live-re-read seam that does not exist; the phase ledger already makes a drain-and-reboot crash-safe, and `/ready` gates traffic until the new token is live. Choose B only if a genuine no-downtime SLA justifies building the re-read seam.
- **Unblocks:** S.2 (the drain-and-reboot runbook framing + named downtime target).
- **Source:** [S](S-security-rotation-and-least-privilege.md) §Open questions 2.

### 10 — Backup source + turn the data-safety-net ON
- **Decision:** Stay on the GitHub-Actions `pg_dump` artifact (the only layer today — Railway volume backups are plan-gated), or move to a Railway managed-backup / PITR tier? And will you complete the three one-time enable steps (`DATABASE_PUBLIC_URL` secret, retention-400 raise, `BACKUP_ENABLED=true`)?
- **Options:** A) Keep GH-Actions `pg_dump`, enable it now · B) Move to Railway managed-backup / PITR.
- **Recommendation:** **Keep the GH-Actions `pg_dump` and set `BACKUP_ENABLED=true` now** — this is the single highest-value ops action on the page: all four scheduled runs to date `skipped`, so the entire RPO ≤ 24 h contract currently rides on a workflow that has never actually run. Enabling it is a one-time owner step, not a build.
- **Unblocks:** O.1's real-artifact leg + `restore-verify.yml` going green for the first time (turns the safety net from paper into a witness).
- **Source:** [O](O-ops-migration-backup-restore-rollback.md) §Open questions 1 + P3.

### 11 — Throwaway restore DB location
- **Decision:** Does the drill run against a free CI `postgres:18` service container, or a dedicated Railway scratch DB for higher fidelity to prod Postgres?
- **Options:** A) CI service container · B) Railway scratch DB.
- **Recommendation:** **CI service container** — `restore-verify.yml` already uses one; it is free, ephemeral, and `postgres:18` matches the prod major version closely enough for schema+integrity assertions. A Railway scratch DB adds cost and setup for marginal fidelity.
- **Unblocks:** O.2 (the migrate + rollback drill).
- **Source:** [O](O-ops-migration-backup-restore-rollback.md) §Open questions 2.

### 12 — Structured-log format + drain
- **Decision:** JSON or logfmt for the structured stream? Which fields are mandatory beyond `correlation_id`? Is the Railway log drain the target, or a dedicated backend (Loki, etc.) that changes the field contract?
- **Options:** A) JSON → Railway drain · B) logfmt → Railway drain · C) JSON → dedicated backend (Loki).
- **Recommendation:** **JSON → Railway log drain**, mandatory fields = timestamp, level, logger, message, `correlation_id` — JSON is the safest default for an indexable drain and matches the correlation-join goal (log line ↔ `audit_log`/`event_outbox` row). Switch the field contract only if a dedicated backend is already chosen.
- **Unblocks:** D4.4a (JSON formatter + stream redaction) — independent of the heavier D4.4b correlation-context thread.
- **Source:** [D4](D4-observability-surface.md) §Open questions 6.

### 13 — Relay-health alert delivery path
- **Decision:** Should the relay-health alert (outbox age climbing while delivered stays flat) fire through the `OperatorAlert` sink, or through the metrics backend's alerting (Alertmanager / Grafana)?
- **Options:** A) `OperatorAlert` sink (Discord webhook / logging) · B) metrics-backend alerting · C) both.
- **Recommendation:** **`OperatorAlert` sink now; add backend alerting once the metrics backend (#7) lands** — the `LoggingAlertSink` + Discord `WebhookReporter` twin already exists and needs no external infra, so P1's alert can ship with D4.1; fold in Alertmanager/Grafana rules when the backend decision is settled.
- **Unblocks:** D4.1 (whether P1's "alert" is an `OperatorAlert` or a metric rule).
- **Source:** [D4](D4-observability-surface.md) §Open questions 7. *(Depends on #7.)*

---

## Tier 3 — Scope / priority calls
*Judgement calls on how far to build — the answer sizes the slice rather than unblocking a fixed one.*

### 14 — B10 route-origin: is it worth the engine cost?
- **Decision:** Is a kernel grammar + engine + session-state + golden-harness change worth fixing **one** back-button label ("↩ Community" when the operator came from Server Management), given a permanent origin dimension on every future golden — or is a cheaper fix acceptable?
- **Options:** A) Build the additive engine signal (opt-in, zero golden churn until a panel opts in) · B) Cheap fix: `role.hub` declares `parent=server_management.hub`, accept a static "↩ Back" (loses the direct-open "↩ Community") · C) Leave as-is.
- **Recommendation:** **A — ship B10.1–B10.3 (the engine signal, zero churn), then decide the role opt-in (B10.4) separately** — the capability lands with no golden cost and is fully unit-testable; the churn only arrives when you opt a panel in, so the expensive part stays deferrable. If back-button fidelity is genuinely low-value to you, **B** is a legitimately cheaper end state.
- **Unblocks:** B10.1–B10.3 (engine) vs a one-line cheaper fix vs nothing.
- **Source:** [B10](B10-panel-route-origin.md) §Open questions 1.

### 15 — B10 scope
- **Decision:** Just `role.hub`, or all four routed managers (moderation / channels / roles / cleanup) plus the Access-Map / Help-Preview subpanels?
- **Options:** A) `role.hub` only · B) all four managers · C) all four + subpanels.
- **Recommendation:** **`role.hub` only first** — it is the concrete reported symptom; each additional panel adds its own origin golden, so prove the pattern on one before a fleet rollout (each extra is one more small PR).
- **Unblocks:** B10.4 (a single origin golden).
- **Source:** [B10](B10-panel-route-origin.md) §Open questions 2.

### 16 — B10 back depth
- **Decision:** Single-level back (origin = immediate opener, all the oracle does), or a breadcrumb *stack* that unwinds one level per click?
- **Options:** A) Single-level · B) Multi-level breadcrumb stack.
- **Recommendation:** **Single-level** — it matches the oracle exactly and keeps the golden matrix flat; a stack is materially more engine complexity and a deeper golden matrix for a fidelity gain the oracle never had.
- **Unblocks:** keeps B10's engine + golden scope contained.
- **Source:** [B10](B10-panel-route-origin.md) §Open questions 3.

### 17 — B10 golden strategy, minting, and label source
- **Decision:** (a) Key the parity harness on which origins — every (panel × reachable-origin) pair, or only origins that differ from the `home_hub` fallback? (b) Origin back-id: registration-time mint over the route graph, or the click-time-parsed origin family? (c) Where does the origin label come from?
- **Options:** (a) all-pairs vs differing-only · (b) registration-mint vs click-time-parse · (c) `HUB_NAV_LABELS` vs origin panel's own nav label vs per-route `NavRouteSpec.label`.
- **Recommendation:** **(a) capture only origins that differ from the fallback** (+ a compile-time warning for a `BACK_TO_ORIGIN` panel with no opted-in opener, so the mode can't drift dead); **(b) click-time-parsed origin family** (matches the existing `nav:browse:`/`nav:selwin:` precedent, avoids a route-graph walk); **(c) `HUB_NAV_LABELS`, adding a `server_management` entry**. These three fold into one coherent mechanical answer.
- **Unblocks:** B10.3 (the harness origin dimension — a hard prerequisite of B10.4).
- **Source:** [B10](B10-panel-route-origin.md) §Open questions 4 + 5 + 6.

### 18 — D2 first target game
- **Decision:** Is a reflex/timing casino minigame the right proving ground for D2.2, or is there a specific roadmap minigame that should drive the primitive's API shape?
- **Options:** A) Reflex/timing casino minigame · B) a named roadmap game.
- **Recommendation:** **Reflex/timing casino minigame** — it is new code (no goldens to protect), squarely in the arm-window → resolve-on-click shape, and exercises the primitive end-to-end without touching the fishing reference impl. *If* a specific game is already on your roadmap, name it — the API is best designed against the real second consumer, so that would override.
- **Unblocks:** D2.2 (the primitive's real validation).
- **Source:** [D2](D2-realtime-minigame-framework.md) §Open questions 1.

### 19 — D2 refactor fishing now, or leave as reference?
- **Decision:** Consolidate fishing onto the shared primitive eventually, or is "fishing is the reference, new games use the primitive" an acceptable permanent state?
- **Options:** A) Leave fishing as reference (D2.3 optional/later) · B) Consolidate fishing onto the primitive.
- **Recommendation:** **Leave fishing untouched until the primitive is proven on a green second consumer** — fishing's determinism is byte-pinned across its timing goldens; keeping the refactor off the critical path avoids risking the reference impl. Adoption later is a mechanical, golden-gated swap you can schedule or decline.
- **Unblocks:** protects the fishing timing goldens; keeps D2.1/D2.2 additive.
- **Source:** [D2](D2-realtime-minigame-framework.md) §Open questions 2.

### 20 — D2 primitive home
- **Decision:** Does the minigame primitive live in the K8 panels band (`sb/kernel/panels/minigame.py`) or a new dedicated `sb/kernel/minigame/` band?
- **Options:** A) `sb/kernel/panels/minigame.py` · B) new `sb/kernel/minigame/` band.
- **Recommendation:** **`sb/kernel/panels/minigame.py`** — it composes the K8 panels seams (timers + push-edit), so beside them is the lowest-friction home and matches where the timer/push-edit seams were minted "beside their only consumer". A dedicated band is cleaner long-term but heavier for one primitive.
- **Unblocks:** D2.1 (the extraction).
- **Source:** [D2](D2-realtime-minigame-framework.md) §Open questions 5.

### 21 — D2 window floor, multi-round, and turn-timeout consumers
- **Decision:** (a) Expose the reaction window as a per-game knob only, or also a platform-wide floor so no game ships an unwinnable sub-second window? What is the live-cue-edits-per-round budget before Discord rate limits bite? (b) Model multi-round natively, or single-shot first? (c) Stretch to cover blackjack/rps turn-timeout countdowns, or stay reflex-focused?
- **Options:** (a) per-game only vs +platform floor · (b) multi-round native vs single-shot first · (c) turn-timeouts in vs out.
- **Recommendation:** **(a) per-game knob + a platform-wide floor** (a sub-second window is unwinnable across a Discord round trip — the floor is cheap insurance), budget ~3–4 cue edits/round; **(b) single-shot first**, add round-sequences when a consumer needs them; **(c) out of scope** — blackjack/rps are coarse whole-turn clocks already served by panel `timeout_s`; keep the primitive focused on the reflex shape.
- **Unblocks:** D2.1 (the primitive's API surface).
- **Source:** [D2](D2-realtime-minigame-framework.md) §Open questions 3 + 4 + 6.

### 22 — B8 ux_lab: port the dev surface at all?
- **Decision:** The B8 doc surfaces five: **(1)** port the admin-only ux_lab dev/diagnostic surface (9 wings) at all, or leave it parked as declared-refused (posture C)? **(2)** full port vs **render-only** for the 3 special wings (pil_cards = image bytes / probe_bench = version+date+live-errors / components_v2 = channel-side CV2 + external URLs)? **(3)** golden strategy for that non-deterministic/binary output — byte-exact (frozen clock+version+PIL), shape-only (assert an `X.png` attachment exists, not its bytes), or a deterministic injected `Clock`/version seam? **(4)** priority vs the resilience/observability lanes? **(5)** registry home — does the ported pattern registry live in `sb/spec/*` (if a kernel/spec consumer must read `category_counts()`) or as `sb/domain/ux_lab/*` data (if only the ux_lab domain reads it)?
- **Options:** (1) don't port / render-only / full · (2) render-only vs full-fidelity inside the zero-write fence · (3) byte-exact vs shape-only vs injected-seam · (4) now vs later-quarter · (5) `sb/spec/*` vs `sb/domain/ux_lab/*`.
- **Recommendation:** **`[?]` LOW priority — build Slice 0 (registry + exhibit-browser grammar + home `_EXHIBITS` re-derive) + per-wing embeds as a proof, keep the 3 special wings render-only**, pin their output **shape-only** (an `X.png` exists, not its bytes), and **home the registry in `sb/domain/ux_lab/*`** — the re-derived home `_EXHIBITS` line is rendered by the ux_lab panel provider, so the deciding consumer is the domain, not spec (promote to `sb/spec/*` only if a kernel/spec surface later needs `category_counts()`). This is an **admin-only, zero-write dev tool** with **no user-facing gap** (the 9 wings are honest pending refusals fronting a fully-ported home), so it is genuinely deferrable — I cannot rank it above user-facing work without knowing how much *you personally* use the dev surface.
- **Unblocks:** B8 wing slices (Slice 0 foundation = registry + `ExhibitWingView`/exhibit-browser grammar + home re-derive, then per-wing embeds → the 3 special wings).
- **Source:** [B8](B8-ux-lab-wings.md) §Open questions 1–5; [completeness snapshot](../status/completeness-table-2026-07-18.md) B8 row.

### 23 — S.3 least-privilege trim (intents + invite permissions + DB role)
- **Decision:** (a) Replace `Intents.default()` with an explicit consumed-feeds intent set? (b) Re-scope the bot's invite permissions to the minimal set the installed mutation ports need (accepting a re-invite)? (c) Split a DDL migration role from a DML-only runtime role for `DATABASE_URL`?
- **Options:** each is yes/no; (b) and (c) carry an ops cost (re-invite / two roles).
- **Recommendation:** **All three yes** — (a) is a contained, evidence-backed adapter change (voice/typing/invites are on with no consumer); (b) trims real blast radius for a one-time portal re-invite; (c) stops the live runtime role holding DDL it never uses. (a) can land immediately; (b)/(c) are deployment changes that need your portal + DB-provisioning action, so they follow.
- **Unblocks:** S.3 (intent trim = code now; permission + DB-role split = ops artifacts + your provisioning).
- **Source:** [S](S-security-rotation-and-least-privilege.md) §Open questions 5 + 6.

### 24 — D5 e2e / live-guild test harness shape
- **Decision:** Seven, from the D5 doc: **(1)** the in-process Discord dependency (D5.1's central call) — a hermetic **fake `discord` module** (stays in the pyyaml-only CI env, proves only our code) vs **`discord.py` installed** in a dedicated job like `golden-parity` (exercises real library types), or both at different tiers? **(2)** how/when the **LIVE** tier runs and how often — a `workflow_dispatch` job holding `DISCORD_BOT_TOKEN_PRODUCTION` on a network-capable runner, an owner-local runbook, or a scheduled cadence (the container/session window is too tight for long serial live work — what is the budget)? **(3)** which command set the LIVE sweep scripts — the full hub set (`!help`/`!settings`/`!diagnostics`/`!setup` + a minigame + a role/channel effect) or a minimal boot-health smoke (boot → `/ready` 200 → one command → clean drain)? **(4)** pass/fail thresholds — is a single non-response a hard fail, or is the live tier a **degraded-health signal** (report reds, never block a merge — the `verified_live` debt-list model), and what response latency bounds a "no answer" (the gateway READY bound is 75 s)? **(5)** assert on **rendered bytes or structural shape**? **(6)** does a green LIVE run mint a `verified_live` record automatically, and if so **who/what signs an automated run** (V2 requires a signer + `signed_at` + `build_sha`) — a bot identity, or a separate non-signed lane that leaves signing to the owner? **(7)** guild hygiene — a dedicated **ephemeral** test channel it creates + deletes per run (needs the channel-effect port armed) or a fixed `#bot-activity`-style channel the owner tolerates accumulating?
- **Options:** (1) fake vs installed vs both · (2) dispatch+secret-gated vs owner-local vs scheduled · (3) full hub sweep vs minimal boot-health smoke · (4) hard-fail vs degraded-health signal · (5) byte-exact vs structural · (6) auto-mint + signer vs unsigned lane · (7) ephemeral self-cleaning vs fixed accumulating channel.
- **Recommendation:** **`[?]` reasonable default:** **fake in-process for the PR tier** (deterministic, no secrets, **byte-assertable** against goldens) + an installed-`discord.py` **LIVE** tier gated behind a secret + `workflow_dispatch`/nightly; **structural (shape) asserts** on the live tier (a real guild's payloads carry non-deterministic ids/timestamps) while the headless tier stays byte-exact; script a **bounded curated sweep** (a few hub commands + one effect), not the full set; treat the live tier as a **degraded-health signal that reports reds but never blocks a merge**; have an automated green run write to a **separate non-signed lane** and leave `verified_live` **signing to the owner** (don't mint a bot-signed trust record); post into an **ephemeral per-run channel it creates and deletes** once the channel-effect port is armed. Cadence, the exact command set, and the guild-hygiene posture are genuine owner calls — hence the `[?]`.
- **Unblocks:** the D5 harness slices (D5.1 the in-process adapter tier, D5.2 the secret-gated LIVE tier, D5.3 the optional record/replay bridge).
- **Source:** [D5](D5-e2e-test-harness.md) §Open questions 1–7.

### 25 — R resilience: delivery + DB hardening bounds
- **Decision:** The R doc **corrects the greenfield framing** first: the outbox **already ships** bounded exponential backoff (base 5 s, cap 300 s, `MAX_ATTEMPTS = 12`), a `DEAD` dead-letter (90 d retention), and dead-letter metrics — so this is **not** "add backoff / add a DLQ". The real gaps and their questions: **(1)** now that the retry boundary must move from `bus.emit` (publish-accepted, per-handler-isolated — *not* delivered) to the **Discord ack** (a slower, rate-limited egress where the effectful subscriber currently swallows its own `HTTPException`, so a 429/blip is dropped and the row is falsely marked delivered), are 12 attempts over a ~300 s-capped curve still right, or do durable effects get a longer tail? **(2)** egress signal shape — a typed re-raise vs a `deliver() -> DeliveryOutcome` port that separates **permanent** (403/404 deleted channel) from **transient** (429/5xx) so permanent failures dead-letter without burning 12 attempts? **(3)** keep the **90 d** dead-letter retention, and is `replay()` operator-only or a capped auto-replay-after-cooldown for a subset? **(4)** breaker thresholds — consecutive-failure count to open, cooldown to half-open, probe cadence (default: open after 5, 10 s cooldown, `ConfigSpec` overrides), and per-pool or finer-grained? **(5)** on an open breaker, **refuse the write** (the current fail-closed posture) or **queue-and-warn** with replay when the DB returns (only safe for idempotency-anchored writes)? **(6)** boot-retry posture — retry-with-backoff for a bounded window then crash (fail-fast for the supervisor) vs wait indefinitely through a maintenance window? **(7)** alerting on dead-letter growth / the breaker opening — through the `OperatorAlert` sink (as #13) or the metrics backend (depends on `outbox_dead_letter_total`, D4.1)? **(8)** golden determinism — seed the backoff jitter + freeze the breaker clock in tests, or keep jitter off any golden-observed path?
- **Options:** a policy/numeric choice per axis; the load-bearing structural call is (2) typed re-raise vs a `DeliveryOutcome` port.
- **Recommendation:** **`[?]` reasonable defaults:** **move the retry boundary to the Discord ack** and adopt a `deliver() -> DeliveryOutcome` port so permanent vs transient failures are distinguished (permanent dead-letters at once; transient rides the *existing* capped backoff, honoring `retry_after` + jitter); **keep the 90 d dead-letter retention with operator-only manual replay** (never auto-replay a poison message); add a **DB reconnect-with-backoff + circuit breaker + fast fail-closed** on the pool seam (default: breaker opens after ~5 consecutive fails, 10 s cooldown to half-open, `ConfigSpec` overrides), anchored on the idempotency ledger so a refused write leaves no half-applied state and replays cleanly; **keep refuse-write UX as an explicit honest "write refused" reply** (never a silent success), with **bounded boot-retry then fail-fast** for the supervisor; route both the dead-letter-growth and breaker-open alerts through the `OperatorAlert` sink (#13) until the metrics backend lands. The queue-and-warn-vs-refuse UX and the exact numeric bounds are genuine owner calls — hence the `[?]`.
- **Unblocks:** the R delivery-hardening slices (P1 the outbox→Discord delivery boundary, P2 the DB reconnect/breaker/fail-closed).
- **Source:** [R](R-resilience-delivery-and-db.md) §Open questions 1–8.

---

## Tier 4 — Access / credential gates
*Not a design call — these need you to provision a credential or an account before any slice can be built. Nothing an agent can do unblocks them.*

### 26 — AI surface credentials (`ANTHROPIC_API_KEY` / `CLAUDE_ROUTINE_*`)
- **Decision:** Provision the AI-lane env creds, or keep the honest refusals?
- **Options:** A) Provide `ANTHROPIC_API_KEY` (+ `CLAUDE_ROUTINE_*`) to a secure store · B) Keep the current declared refusals until later.
- **Recommendation:** **Provide the creds when you want the AI surface live** — A1/A2/A3, the ai NL lane, and hermes egress are all OWNER-ONLY because the creds are dark; the code paths front honest refusals today (no silent gap), so this is purely a provisioning decision on your timeline. If provided, route them through whatever secret store #8 settles on.
- **Unblocks:** A1/A2/A3 + ai NL lane + hermes egress build slices.
- **Source:** [completeness snapshot](../status/completeness-table-2026-07-18.md) OWNER-GATED row.

### 27 — btd6 NK bracket standings — data account / ingestion
- **Decision:** Provision a Ninja-Kiwi data source/account for live btd6 bracket standings, or keep the named-successor refusal?
- **Options:** A) Provision the NK data account + stand up ingestion · B) Keep the honest refusal.
- **Recommendation:** **Keep the refusal unless btd6 live standings matter to you** — this needs an external NK data account **and** a new ingestion subsystem (not a mint), so it is the heaviest access-gated item; the current surface is an honest named-successor refusal with no user-facing surprise. Provision only if the feature earns the subsystem.
- **Unblocks:** btd6 live bracket standings (external ingestion subsystem).
- **Source:** [completeness snapshot](../status/completeness-table-2026-07-18.md) btd6 OPEN row.

---

## Tier 5 — Posture confirmations
*Accept-or-flip confirmations on a standing posture. A "confirm" costs one word and closes an open gate; the default is to keep the deliberate current posture.*

### 28 — C4 tournament open-flag TOCTOU
- **Decision:** Keep matching the oracle's non-atomic open-flag guard (the current `accepted-posture` + boot-sweep recovery), or fence it atomically?
- **Options:** A) Keep accepted-posture (byte-match the oracle) · B) Fence it (diverge from the oracle with an atomic guard).
- **Recommendation:** **Keep the accepted-posture** — the non-atomic guard deliberately matches the oracle's shipped behaviour, with boot-sweep recovery as the safety net; `docs/ideas/tournament-open-flag-toctou-2026-07-12.md` already records `outcome: accepted-posture`. Fence it only if you now want to *diverge* from the oracle for a stronger guarantee (a deliberate parity break, not a bug fix). A sibling branch `claude/tournament-open-toctou` exists but has no open PR — do not harden without this call.
- **Unblocks:** closes the standing C4 owner-gate (either confirm, or dispatch the fence slice).
- **Source:** [completeness snapshot](../status/completeness-table-2026-07-18.md) C4 row; `docs/ideas/tournament-open-flag-toctou-2026-07-12.md`.
- **Decided (2026-07-18):** Keep accepted-posture — confirmed under decide-and-flag (fm ORDER 048 / PL-001), logged as [D-0092] in `docs/decisions.md`. No fence dispatched; the strict fence stays an available future owner-decision. Closes the standing C4 owner-gate.

### 29 — Rollback scope: schema vs data
- **Decision:** Confirm the design premise — rollback is **data-plane reverse-import**, and the migration chain is **forward-only with no down-migrations** — as the permanent posture?
- **Options:** A) Confirm forward-only + data-plane reverse-import · B) Eventually want reversible/down migrations.
- **Recommendation:** **Confirm forward-only + data-plane reverse-import** — down-migrations are a much larger change to `sb/kernel/db/migrations.py` and every `migrations/*.sql`; the reverse-importer round-trip is the honest recovery model the drill (O.2) is built to prove.
- **Unblocks:** freezes O.2's drill semantics (rehearse the reverse importer, not schema-down).
- **Source:** [O](O-ops-migration-backup-restore-rollback.md) §Open questions 4.

### 30 — Deploy rollback in scope?
- **Decision:** Since merge = deploy on Railway, is *deploy* rollback (redeploy a prior GHCR image / prior commit) part of the recovery loop, or strictly your Railway-console action with only **data** rollback drilled?
- **Options:** A) Deploy rollback is owner Railway-console action; drill only data rollback · B) Bring deploy rollback into the drilled loop.
- **Recommendation:** **A — deploy rollback stays your Railway-console action; the drill covers only data rollback** — deploy rollback is a platform-console operation, not something CI can rehearse against ephemeral Postgres; document it in the runbook (O.3) as an owner step, keep the drilled legs data-only.
- **Unblocks:** scopes the O.3 consolidated runbook.
- **Source:** [O](O-ops-migration-backup-restore-rollback.md) §Open questions 5.

### 31 — Emergency-swap secret posture
- **Decision:** Should `discord_prod_bot_token` (`ON_COMPROMISE`) and `prod_dsn` (`MANAGED`) keep their current no-cadence postures, or gain a documented rotation lane so the two highest-blast secrets aren't the only ones with no autonomous path?
- **Options:** A) Keep current postures + a documented owner-driven rotation lane · B) Add an autonomous cadence.
- **Recommendation:** **Keep the postures, add a *documented owner-driven* lane** — an autonomous cadence on the two secrets whose swap forces a worker restart is risky; a documented drain-and-reboot procedure (S.2) gives the emergency path without arming an autonomous rotation on the highest-blast credentials.
- **Unblocks:** the S.2 posture rows (`sb/spec/credentials.py`).
- **Source:** [S](S-security-rotation-and-least-privilege.md) §Open questions 4.

---

## How to answer

- **Inline:** edit the recommendation into a decision (e.g. add `> **Owner:** go with B, 30s`) — a follow-up slice reads it straight from here.
- **Inbox:** answer by number (e.g. "1: agree; 7: Grafana Cloud, public+bearer; 22: skip") — the numbers are stable.
- The `[?]` rows (22, 24, 25) are the ones where a real default is offered but the *right* answer needs your product context; everything else has a default that agrees = the fastest path.
