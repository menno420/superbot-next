# B10 route-origin — implementation plan (execute-on-approval)

> **Status:** `plan`
>
> The concrete implementation **plan** for B10
> ([`B10-panel-route-origin.md`](B10-panel-route-origin.md)) — what gets built
> IF the owner approves the one load-bearing cost/benefit call. This is a PLAN,
> not built code: the code and `docs/decisions.md` win once slices land. The
> mechanical design questions (B10's Q2–Q6) are resolved here as flagged
> **decide-and-flag** defaults (PL-001); the single go/no-go (B10's Q1) is routed
> to the owner in [`../question-router.md`](../question-router.md) and gates the
> whole plan. Evidence citations are `file:line` at HEAD `5776b12` unless noted;
> oracle citations are `disbot/views/server_management/hub.py` (the port's
> reference tree).

## TL;DR

B10 proposes a **session-scoped route-origin signal** + a `BACK_TO_ORIGIN`
NavigationSpec mode so a panel's back button can point to *where the user
navigated from* instead of its static `home_hub`. The proposal is sound and its
citations verify (see "Verification" below). This doc makes it executable: it
scopes the work as **two slices** onto seams that already exist — the engine
capability (grammar sentinel + a `PanelSession.opened_from` field + a
`PanelContext.opened_from` field + capture-on-open + render resolver +
click-time-parsed origin back-id), landable with **zero** golden churn because no
consumer is opted in; then the **role-hub opt-in** where the origin golden churn
lands. Every mechanical choice B10 left open is resolved here as a flagged
default; the only thing this plan waits on is the owner's yes/no on whether the
kernel surface is worth the mostly-cosmetic payoff.

## The one gate this plan waits on

**B10 Q1 — is a kernel-engine change worth fixing one back-button label?** This
is a genuine cost/benefit product call, not a worker decision, so it is routed to
the owner in [`../question-router.md`](../question-router.md) (Open questions)
with a recommended default. **Everything below is execute-on-"go".** If the owner
says keep static `FOLLOW_PARENT`, this plan is shelved and B10 closes as
"considered, declined" — no code lands.

## Verification (proposal citations re-read at HEAD `5776b12`)

Before planning the build, the B10 citations were confirmed against live code:

- **The nav row is origin-blind.** `NavigationSpec` carries only static [S]
  fields — `parent`, `home_hub` (default `FOLLOW_PARENT`), `show_help`,
  `show_home`, `show_rules`, `extra_routes` (`sb/spec/panels.py:172-183`); the
  `FOLLOW_PARENT` sentinel resolves to the subsystem's current `parent_hub`
  (`sb/kernel/panels/registry.py:161-166` `resolve_home_hub`). The render nav-row
  builder emits `nav:hub:<hub>` / `nav:back:<parent>` from that spec with **no
  origin input** (`sb/kernel/panels/render.py:606-627`).
- **Session state exists but has no origin field.** `PanelSession` — the
  in-memory per-message state — stores `panel_id`, `invoker_id`, `audience`,
  `page`, `message_ref`, `component_ids`, `channel_id`, and no route origin
  (`sb/kernel/panels/engine.py:254-271`). **This is the seam the origin signal is
  built onto** (see "Where session state lives" below).
- **The role hub is statically homed.** `role.hub` declares
  `NavigationSpec(show_help=True, show_home=True, home_hub="community")`
  (`sb/domain/role/panels.py:172-173`), so it always renders "↩ Community" even
  when opened through the Server-Management hub.
- **A click-time-parsed nav-id precedent already exists.** `nav:browse:` and
  `nav:selwin:` are combinatorial nav families parsed at click time rather than
  pre-minted into the static table, staying inside the nav namespace
  (`sb/kernel/panels/registry.py:36-47`) — the posture B10.3 recommends for the
  origin back-id, adopted below.
- **Back-ids are registration-minted today.** `register_panel` mints
  `nav:back:<parent>` only for a panel's declared `parent`/`extra_routes`
  (`sb/kernel/panels/registry.py:132-137`) — so an origin-dependent back target
  needs the click-time-parsed family, not the static mint.

### Where session state lives (the seam B10 builds onto)

The route-origin signal is **not** a new persistence layer — it rides the
existing in-memory `PanelSession` (`sb/kernel/panels/engine.py:254-271`),
keyed per message, written at the engine's `_store_session` on open and read at
re-render. It dies with the process exactly like `page`/`channel_id`, and the
B10.1 fallback (below) covers the post-restart / no-origin case by rendering
today's static `home_hub` bytes. No new store, no wire-format change, no adapter
change.

## The build, IF approved — two slices

### Slice 1 — the engine capability (no consumer, zero golden churn)

Lands the whole mechanism with every panel still `back_mode=STATIC`, so it ships
**no byte delta** — a pure capability add, unit-tested against a synthetic
two-panel open graph. Rough size **M**.

1. **Grammar (spec leaf).** Add a module sentinel `BACK_TO_ORIGIN =
   "__back_to_origin__"` and a `back_mode: str = STATIC` field on
   `NavigationSpec` (`sb/spec/panels.py:172-183`), mirroring the existing
   `FOLLOW_PARENT` sentinel (`sb/spec/panels.py:63-66`). `STATIC` is today's
   behaviour; the value stays a **serializable string rule**, never a captured
   closure — preserving the exact property the NavigationSpec docstring guards
   (`sb/spec/panels.py:174`).
2. **Capture (engine).** Add `opened_from: str | None = None` to `PanelSession`
   (`sb/kernel/panels/engine.py:254-271`). When an OPEN is dispatched from a
   component click on another panel (the resolve `OPEN_PANEL` terminal already
   knows the clicked `ComponentBinding`, which carries its owning `panel_id` —
   `sb/kernel/panels/registry.py:51-61`), thread that source `panel_id` into the
   open path and write it at `_store_session`. A fresh open (prefix/slash, no
   source panel) leaves it `None`.
3. **Resolve (context + render).** Add `opened_from: str | None = None` to
   `PanelContext` (`sb/kernel/panels/context.py:25-44`), set from the session by
   the engine's context builder so render stays a pure function of its context
   (no session lookup inside `render.py`). In the nav-row builder
   (`sb/kernel/panels/render.py:606-627`): when `nav.back_mode == BACK_TO_ORIGIN`
   **and** `ctx.opened_from` is set, emit a `nav:back:<opened_from>` button;
   otherwise fall through to today's `show_home`/`home_hub` render — byte-identical
   to current output.
4. **Dispatch (registry).** Route the origin back-id via a **click-time-parsed
   origin family** inside the nav namespace (the `nav:browse:`/`nav:selwin:`
   posture, `sb/kernel/panels/registry.py:36-47`) — `handle_nav` re-resolves the
   `<origin>` panel fresh from the registry, exactly as it rebuilds a declared
   `nav:back:<parent>` today. No registration-time route-graph walk.

**Tests for slice 1:** unit tests over a synthetic two-panel open graph — (a)
open B directly → `back_mode=BACK_TO_ORIGIN` with `opened_from=None` renders the
`home_hub` fallback bytes; (b) open B from A via a component click → renders
`nav:back:A`; (c) click that origin back-id → `handle_nav` rebuilds A fresh; (d)
a `STATIC` panel is byte-identical before/after (a regression pin proving zero
churn). No golden changes — the parity harness is untouched in slice 1.

### Slice 2 — opt the role hub in (the golden churn lands here)

Rough size **S–M**. Flip `role.hub`'s `NavigationSpec`
(`sb/domain/role/panels.py:172-173`): keep `home_hub="community"` as the
fallback, add `back_mode=BACK_TO_ORIGIN`. Opened from `server_management.hub`
(the Roles action routes `handler=PanelRef("role.hub")`,
`sb/domain/server_management/panels.py:171-177`) it now renders "↩ Server
Management"; opened directly (its `!rolemenu` anchor / a Community-hub route) it
still renders "↩ Community".

**Golden/tests for slice 2 (the hard prerequisite):** the parity harness gains an
**origin dimension** for `BACK_TO_ORIGIN` panels — `role.hub` is captured from
each opener that can reach it: the direct-open golden must still pin "↩
Community" (the `home_hub` fallback bytes), and an opened-from-`server_management`
golden pins "↩ Server Management" (the origin bytes). Per the decide-and-flag
default D4 below, only origins whose bytes **differ** from the fallback get their
own capture, and a `BACK_TO_ORIGIN` panel with **no** opted-in opener is a
compile-time warning (dead mode) so the grammar can't drift into a
declared-but-unreachable state.

## Layer & seam safety

Every touched file is `sb/spec` (grammar leaf) or `sb/kernel/panels/*` (the panel
band), plus one `sb/domain/role` opt-in in slice 2 — **no kernel→domain import
edge**, and the route flows through the one audited engine seam (`handle_nav` /
`open_panel`). Kernel imports spec only; the sentinel + field live in the spec
leaf and are consumed by the kernel resolver. The signal is a serializable-rule +
in-memory session field, never a captured closure — it keeps the property that
made the port drop the oracle's `BackTarget` in the first place
(`sb/spec/panels.py:174`). No `sb/adapters/*` change: the origin back-id stays in
the existing `nav:back:*` family the component adapter already routes.

## Mechanical questions resolved (decide-and-flag defaults)

B10's Q2–Q6 are mechanical design details, not product-intent calls, so this plan
resolves them as flagged defaults (PL-001) — the owner can override any of them
when reacting, but they do not block the go/no-go.

| # | B10 question | Flagged default | Rationale |
|---|---|---|---|
| **D2** | Scope — role.hub only, or all four routed managers + subpanels? | **role.hub only** as the first consumer; each further subsystem is one more **S** PR with its own origin golden. | Smallest reviewable byte delta; proves the seam before breadth. Widening is additive and owner-scoped (B10 Q2). |
| **D3** | Depth — single-level back or a breadcrumb stack? | **Single-level** (origin = the immediate opener). | Matches exactly what the oracle's `_attach_back_to_hub` does; a stack is materially more engine complexity + a deeper golden matrix for no proven need (B10 Q3). |
| **D4** | Golden strategy for origin-dependent renders. | Capture only the **(panel × origin) pairs whose bytes differ** from the `home_hub` fallback; a `BACK_TO_ORIGIN` panel with **no** opted-in opener is a **compile-time warning** (dead mode). | Keeps the golden matrix minimal and self-pruning; the dead-mode guard stops the grammar drifting into declared-but-unreachable state (B10 Q4). |
| **D5** | Origin back-id minting — registration-time mint vs click-time-parsed. | **Click-time-parsed origin family** (the `nav:browse:`/`nav:selwin:` posture). | Avoids a static route-graph walk; matches the engine's existing "parse the combinatorial nav id, re-resolve fresh" precedent (`registry.py:36-47`). B10.3's own recommendation. |
| **D6** | Label source when origin is a hub. | The origin's own **declared nav/home label**; for a hub origin, add a `server_management` entry to `HUB_NAV_LABELS` (`render.py:127-132`). | Reuses the existing label convention; `server_management` is simply missing from the map today, so one entry closes the gap without a new per-route label field (B10 Q6). |

## Rough size + suggested order

Per B10's own slicing: **Slice 1 (engine, no churn) → Slice 2 (role opt-in +
origin golden)**. Slice 1 is a contained **M** landable with zero consumers;
slice 2 is **S–M** and is where the golden churn is isolated and reviewable. Any
wider rollout (D2) is one more **S** PR per subsystem, each with its own origin
golden. Record a `docs/decisions.md` entry citing the router go/no-go when slice
1 lands.

## Key risk — the golden determinism model

The port rests on render being a deterministic pure function pinned by byte-exact
goldens; `BACK_TO_ORIGIN` makes the *same* panel render *different bytes by
origin*, which the current parity harness does not model (a panel is captured once
from its direct open). The **origin dimension in the harness is a hard
prerequisite of slice 2**, not an afterthought (D4). Slice 1 carries zero risk
here — it ships no consumer, so no golden changes until the harness gains the
origin key.
