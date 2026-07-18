# B10 — Role-hub route-origin back-button (a panel-engine route-origin signal)

> **Status:** `plan`
>
> A forward design proposal from the 2026-07-18 planning phase, opened per the
> completeness snapshot's recommendation to turn the decision-sized backlog
> items into fuller design docs (`docs/status/completeness-table-2026-07-18.md`).
> This is a PLAN, not built work — the owner reacts and prioritizes; the code and
> `docs/decisions.md` win once slices land. Evidence citations are `file:line` at
> HEAD `b39a37f` unless noted.

## TL;DR

The oracle's Server-Management hub appends a **dynamic** "↩ Server Management"
back button to each routed manager panel it opens — the back target depends on
*where the navigation came from*, injected by the opener onto the child it
opens (`disbot/views/server_management/hub.py:96-113,169`). superbot-next's
panel engine has **no per-navigation route-origin signal**: a panel's nav row
is a pure function of its own `NavigationSpec` (a static per-subsystem
`home_hub`, or the `FOLLOW_PARENT` rule), re-resolved from the registry at
click time with no memory of the panel it was reached from
(`sb/spec/panels.py:172-183`, `sb/kernel/panels/render.py:604-618`,
`sb/kernel/panels/engine.py:587-609`). So the ported role hub — opened FROM
the Server-Management hub via `PanelRef("role.hub")`
(`sb/domain/server_management/panels.py:176`) — always renders "↩ Community"
(`sb/domain/role/panels.py:172-173`), never "↩ Server Management". This doc
designs the missing engine capability: a **session-scoped route-origin signal**
threaded through navigation, plus a **`BACK_TO_ORIGIN`** NavigationSpec mode
that resolves at click time to the panel the user navigated *from*, falling
back to the static `home_hub`.

## Problem

### P1 — The oracle decides the back target from route ORIGIN

The oracle hub holds zero domain logic; it *composes* the specialised manager
panels by routing into each cog's `build_help_menu_view` hook at click time
(`disbot/views/server_management/hub.py:49-54,138-170`). Crucially, the back
button is **not** a property of the manager panel — it is injected by the
**opener** onto the child it just built:

- `_open_manager` builds the sub-view, then calls `_attach_back_to_hub(sub_view)`
  before editing it in place (`disbot/views/server_management/hub.py:169-170`).
- `_attach_back_to_hub` appends a control whose `parent_builder` rebuilds the
  hub itself — label `_BACK_LABEL = "↩ Server Management"`, custom_id
  `_BACK_CUSTOM_ID = "server_management:back"`
  (`disbot/views/server_management/hub.py:56-57,96-113`).
- The same injection runs for the Access-Map and Help-Preview subpanels
  (`disbot/views/server_management/hub.py:276,310`).

So the identical Roles manager view carries "↩ Server Management" when reached
through the hub, and its own normal nav (no hub back-button) when reached
directly. The back target is **route-dependent** because the opener — which
*is* the route origin — stamps it onto the child. The mechanism is a
closure-backed `parent_builder` (`disbot/views/navigation.py` `attach_back_button` /
`ParentBuilder` / the `BackTarget` chain), evaluated at click time.

### P2 — superbot-next's nav row is origin-BLIND

The ported engine deliberately **killed** the oracle's closure-backed
`BackTarget`/`chain_back` stacks in favour of a serializable `NavigationSpec`
whose routes are re-resolved fresh from the registry at click time
(`sb/spec/panels.py:172-176` — the docstring says exactly this). That buys
restart-safety and determinism, but it also means a panel's nav row is a pure
function of **its own spec**, with no input describing where it was opened
from:

- `NavigationSpec` carries `parent`, `home_hub` (default `FOLLOW_PARENT`),
  `show_help`, `show_home`, `show_rules`, `extra_routes`
  (`sb/spec/panels.py:178-183`) — every field is a static [S] declaration of
  the panel itself. `home_hub` is "the routing RULE, not a captured value"
  (`sb/spec/panels.py:179`); `FOLLOW_PARENT` resolves to the subsystem's
  *current* `parent_hub` (`sb/kernel/panels/registry.py:161-166`,
  `sb/spec/panels.py:63-66`).
- Render turns that into the nav row with **no origin input**: `show_home`
  emits a `nav:hub:<hub>` button labelled `↩ {HUB_NAV_LABELS.get(hub, 'Home')}`;
  `parent` emits a `nav:back:<parent>` button labelled "↩ Back"
  (`sb/kernel/panels/render.py:597-618`). `HUB_NAV_LABELS` maps `community` →
  "Community" (`sb/kernel/panels/render.py:127-132`).
- Nav clicks re-resolve purely from the registry: `handle_nav` looks the target
  up by the static `NavBinding` and rebuilds it fresh — "parents are rebuilt
  fresh, never captured (§2.4)" (`sb/kernel/panels/engine.py:587-609`). The
  back/hub ids are minted into the ONE static table at registration
  (`sb/kernel/panels/registry.py:97,132-143`).
- **Nothing on the wire carries "opened-from".** `PanelContext` has `origin`
  but it is only `PanelOrigin.INTERACTION` / `PanelOrigin.ANCHOR` — the
  render-vs-boot distinction, not a source panel
  (`sb/kernel/panels/context.py:20-44`; set to `INTERACTION` at
  `sb/kernel/panels/engine.py:410-416`). `ResolveRequest` carries
  surface/actor/args/`origin` (an opaque surface handle the kernel never
  inspects) but no opened-from (`sb/kernel/interaction/request.py:96-108`). And
  `PanelSession` — the in-memory per-message state — stores panel_id,
  invoker_id, audience, page, message_ref, component_ids, channel_id, but no
  route origin (`sb/kernel/panels/engine.py:254-271`).

### P3 — The concrete symptom (the role hub)

`role.hub` declares `NavigationSpec(show_help=True, show_home=True,
home_hub="community")` (`sb/domain/role/panels.py:172-173`), so it always
renders "↩ Community". When an operator opens it **through** the Server-
Management hub — `server_management.hub`'s Roles button routes via
`handler=PanelRef("role.hub")` (`sb/domain/server_management/panels.py:171-177`)
— the engine opens `role.hub` and it *still* shows "↩ Community". The operator's
mental "back" is the hub they came from; the panel offers the wrong destination,
and there is no grammar to express "back to wherever I was opened from". This is
the exact capability the oracle had and the port dropped when it serialized the
nav grammar.

## Proposed design

A panel-engine **route-origin signal**: a session-scoped "opened-from"
captured on `PanelRef` navigation, threaded to render, and consumed by a new
dynamic back-button mode. This is a **KERNEL** change confined to
`sb/kernel/panels/*` + the `sb/spec/panels.py` grammar leaf — no domain edge,
and it enters through the audited engine seam like every other nav route
(§2.4). It is strictly **additive and opt-in**: panels that do not request it
render exactly as today.

### B10.1 — The grammar: a `BACK_TO_ORIGIN` NavigationSpec mode

Add a sentinel + a mode to `NavigationSpec` (`sb/spec/panels.py:172-183`),
mirroring the existing `FOLLOW_PARENT` sentinel pattern
(`sb/spec/panels.py:63-66`):

- A new module sentinel `BACK_TO_ORIGIN = "__back_to_origin__"` and a
  `home_hub`-adjacent field (e.g. `back_mode: str = STATIC` where `STATIC` is
  today's behaviour and `BACK_TO_ORIGIN` opts in). Keeping it a **serializable
  string rule** — not a captured closure — preserves the exact property the
  NavigationSpec docstring was built to guarantee (`sb/spec/panels.py:174`): no
  un-persistable state, resolution at click time.
- Semantics: when `back_mode == BACK_TO_ORIGIN`, render resolves the back
  button to *the panel the user navigated here from*, and **falls back to the
  static `home_hub`** (its existing `↩ <label>` button) when there is no origin
  — direct open, or a post-restart session with no origin in memory. The
  fallback is what makes the change safe: worst case is today's behaviour.

### B10.2 — Capture: record origin on PanelRef navigation

Origin is captured in the engine when one panel opens another via a component
click. The source panel is already knowable: a clicked component routes through
the static table to a `ComponentBinding` that carries its owning `panel_id`
(`sb/kernel/panels/registry.py:51-61,104-129`), and a manager route is a
`PanelActionSpec` whose `handler` is a `PanelRef` (e.g.
`server_management.hub`'s Roles action → `PanelRef("role.hub")`,
`sb/domain/server_management/panels.py:176`). So:

- Thread the source panel_id into `open_panel` / `_render_and_present`
  (`sb/kernel/panels/engine.py:419-481`) when the OPEN is dispatched from a
  component click on another panel (the resolve() `OPEN_PANEL` terminal already
  knows the clicked binding). A fresh open (prefix/slash, no source panel) sets
  origin `None`.
- Store it on the opened panel's `PanelSession` — a new
  `opened_from: str | None` field alongside `page`/`channel_id`
  (`sb/kernel/panels/engine.py:254-271`), written at `_store_session`
  (`sb/kernel/panels/engine.py:461-466`). Session-scoped, in-memory, dies with
  the process exactly like the rest of the session — never persisted (the
  restart fallback in B10.1 covers the reopened case).

### B10.3 — Resolve: thread origin into render

- Add an `opened_from: str | None` field to `PanelContext`
  (`sb/kernel/panels/context.py:25-44`), set by `_context_from_request` from the
  session when re-rendering, so render is still a pure function of its context
  (no session lookup inside render.py).
- In the nav-row builder (`sb/kernel/panels/render.py:597-618`), when
  `nav.back_mode == BACK_TO_ORIGIN` **and** `ctx.opened_from` is set, emit a
  `nav:back:<opened_from>` button — reusing the existing back-nav wire family
  and label convention (a route-origin label, e.g. resolved from
  `HUB_NAV_LABELS` when the origin is a hub, else the origin panel's own nav
  label). When `opened_from` is `None`, fall through to the normal
  `show_home`/`home_hub` render — byte-identical to today.
- Click dispatch needs **no new kind**: `nav:back:<origin>` is already a
  `NavBinding(kind="back", target=<origin>)` that `handle_nav` rebuilds fresh
  from the registry (`sb/kernel/panels/engine.py:599-600`). The only wrinkle is
  minting: today `nav:back:*` ids are minted only for a panel's declared
  `parent`/`extra_routes` (`sb/kernel/panels/registry.py:132-137`). An
  origin-dependent back id must be registerable for **any** panel that a
  `BACK_TO_ORIGIN` panel can be opened from — so either mint the back-id for
  every hub/opener panel that routes into a `BACK_TO_ORIGIN` child (a
  registration-time closure over the route graph), or parse origin back-ids at
  click time inside the nav namespace (the posture `nav:browse:` /
  `nav:selwin:` already use for combinatorial id spaces,
  `sb/kernel/panels/registry.py:36-47`). **Recommendation: the click-time-parsed
  origin family** — it avoids a registration-time route-graph walk and matches
  the engine's existing "parse the combinatorial nav id, re-resolve fresh"
  precedent.

### B10.4 — Opt the role hub in (the first consumer)

Flip `role.hub`'s `NavigationSpec` to request the mode
(`sb/domain/role/panels.py:172-173`): keep `home_hub="community"` as the
fallback, add `back_mode=BACK_TO_ORIGIN`. Opened from `server_management.hub`
it now renders "↩ Server Management"; opened directly (its own `!rolemenu`
anchor / a Community-hub route) it still renders "↩ Community". No other
subsystem changes unless the owner scopes it wider (Open Questions).

### Layer & seam notes

Every touched file is `sb/spec` (grammar leaf) or `sb/kernel/panels/*` (the
panel band) plus one `sb/domain/role` opt-in — no kernel→domain import edge,
and the route still flows through the one audited engine seam
(`handle_nav` / `open_panel`). The signal is serializable-rule + in-memory
session state, never a captured closure — it keeps the property that made the
port drop the oracle's `BackTarget` in the first place
(`sb/spec/panels.py:174`).

## Affected surfaces

| Band | Files | Slice |
|---|---|---|
| spec (grammar leaf) | `sb/spec/panels.py:172-183` (`BACK_TO_ORIGIN` sentinel + `back_mode` field on `NavigationSpec`) | B10.1 |
| kernel / panels — engine | `sb/kernel/panels/engine.py:254-271` (`PanelSession.opened_from`), `:419-481` (capture on open), `:410-416` (thread to context) | B10.2, B10.3 |
| kernel / panels — context | `sb/kernel/panels/context.py:25-44` (`PanelContext.opened_from`) | B10.3 |
| kernel / panels — render | `sb/kernel/panels/render.py:597-618` (origin-dependent back button + fallback) | B10.3 |
| kernel / panels — registry | `sb/kernel/panels/registry.py:36-47,132-143` (origin back-id family — click-time-parsed vs registration-time mint) | B10.3 |
| domain / role (opt-in) | `sb/domain/role/panels.py:172-173` (`back_mode=BACK_TO_ORIGIN`) | B10.4 |
| goldens / parity | `goldens/role/*` (role.hub now renders differently by origin — a new origin dimension), plus any panel opted in later | B10.3, B10.4 |

No `sb/adapters/*` change: the wire ids stay in the existing `nav:back:*`
family the component adapter already routes.

## Rough size + suggested PR slicing

Likely **M–L**: the engine signal + grammar is a contained M, but the golden
churn (every opted-in panel now renders per-origin) pushes it toward L.
Suggested slicing:

- **B10.1 + B10.2 + B10.3 — the engine signal** — **M**. Grammar sentinel +
  session field + context field + capture + render resolver + the origin
  back-id decision. Landable with **no** consumer opted in (every panel stays
  `back_mode=STATIC`), so it ships zero golden churn on its own — a pure
  capability add, fully unit-testable against a synthetic two-panel open graph.
- **B10.4 — opt `role.hub` in** — **S–M**, but this is where the **golden churn
  lands**: `role.hub` opened from `server_management.hub` now renders "↩ Server
  Management", so the parity harness needs an origin-parameterized golden for
  that path (and the direct-open golden must still pin "↩ Community"). Land
  after the engine slice, standalone, so the byte delta is isolated and
  reviewable.

Suggested order: **B10.1–B10.3 (engine, no churn) → B10.4 (role opt-in +
golden)**. Any wider rollout (other routed managers) is one more S PR per
subsystem, each with its own origin golden.

**Key RISK — determinism / golden strategy.** The whole port rests on
render being a deterministic pure function pinned by byte-exact goldens. This
change makes the *same* panel render *different bytes depending on origin*,
which the current parity harness does not model (a panel is captured once, from
its direct open). The harness must gain an **origin dimension**: capture a
`BACK_TO_ORIGIN` panel from each opener that can reach it (at minimum: direct
open → `home_hub` fallback bytes; opened-from-hub → origin bytes). If origin is
not part of the golden key, the same panel yields two byte-strings for one
golden and parity is nondeterministic — so the harness change is a **hard
prerequisite** of B10.4, not an afterthought.

## Open questions for the owner

1. **Is it worth it?** This is a KERNEL grammar + engine + session-state +
   golden-harness change to fix **one** back-button label. Is the operator
   confusion ("↩ Community" when I came from Server Management) worth the engine
   complexity and the permanent origin dimension on every future golden — or is
   a cheaper fix acceptable (e.g. role.hub declares `parent=server_management.hub`
   and accepts a static "↩ Back", losing the direct-open "↩ Community")?
2. **Scope.** Just `role.hub`, or all four routed managers the oracle back-buttons
   (moderation / channels / roles / cleanup —
   `disbot/views/server_management/hub.py:49-54`), plus the Access-Map / Help-
   Preview subpanels (`disbot/views/server_management/hub.py:276,310`)? Each
   adds its own origin golden.
3. **Depth.** Single-level back (origin = the immediate opener, which is all the
   oracle does) — or a breadcrumb *stack* (Help → Server-Management → Roles →
   sub-panel, unwinding one level per click)? The oracle's `BackTarget`/
   `chain_back` supported multi-level; the port deliberately dropped it. A stack
   is materially more engine complexity and a deeper golden matrix.
4. **Golden strategy for origin-dependent renders.** How should the parity
   harness key origin — capture every (panel × reachable-origin) pair, or only
   the origins that actually differ from the `home_hub` fallback? And should a
   `BACK_TO_ORIGIN` panel with no opted-in opener be a compile-time warning
   (dead mode) so the grammar can't drift into a declared-but-unreachable state?
5. **Origin back-id minting.** Registration-time mint over the route graph
   (every opener that can reach a `BACK_TO_ORIGIN` child gets a `nav:back:`
   entry) vs the recommended click-time-parsed origin family (the
   `nav:browse:`/`nav:selwin:` posture, `sb/kernel/panels/registry.py:36-47`)?
   The latter avoids a static route-graph walk but puts one more parsed family
   in the nav namespace.
6. **Label source.** When origin is a hub, `HUB_NAV_LABELS` gives "Server
   Management"-style copy (`sb/kernel/panels/render.py:127-132`) — but
   `server_management` is not currently in that map. Does the origin label come
   from `HUB_NAV_LABELS` (needs a `server_management` entry), from the origin
   panel's own declared nav label, or from a per-route `NavRouteSpec.label`
   (`sb/spec/panels.py:165-169`) the opener declares?
