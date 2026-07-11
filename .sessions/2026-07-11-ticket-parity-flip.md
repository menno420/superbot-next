# 2026-07-11 — ticket parity flip (pending→ported, the twenty-first row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `ticket` parity row pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/cogs/ticket_cog.py` +
`disbot/views/tickets/{hub,_shared,launcher}.py` +
`disbot/services/{ticket_service,ticket_mutation}.py` @7f7628e1.
Goldens: `parity/goldens/ticket/` — sweep_ticket (the hub panel),
sweep_ticket_new / _add / _remove / _claim / _close (guard bytes).
Pre-flip state: 0/6 green. Post: 6/6 on the FIRST local replay.

## What shipped

1. **A brand-new subsystem end to end** — `ticket` had NO domain
   package, NO manifest module, NO layout lock (first fully-from-zero
   flip since the lane's groundwork rows): `sb/domain/ticket/`
   (service + handlers), `sb/manifest/ticket.py`,
   `manifest/layout/ticket.lock.json` (6 legacy-seed Exempt rows, the
   a627153/#66 seed shape) + `check_sim_gate --write-baseline`;
   compat pin regenerated (new subsystem key, 6 command rows incl. the
   shipped `new` aliases open/create, the `ticket.open_form` modal id).
2. **`!ticket` → the shipped hub** (`@commands.group(name="ticket",
   invoke_without_command=True)` → `open_ticket_hub`): blurple
   `🎫 Support tickets` embed; the STATE-dependent description
   (`cfg is None or not cfg.is_set_up` → the not-set-up copy) via
   renderer_override adjusting ONLY the description (proof_channel-hub
   precedent); the three shipped buttons verbatim with label + emoji
   as SEPARATE wire fields (`@discord.ui.button(label=..., emoji=...)`
   → `{"emoji": {"id": null, "name": "🎫"}}` — the channelmenu-proven
   twin serializer, NOT the economy glyph-in-label shape); nav row
   nav:help + nav:hub:community (`home_hub="community"` explicit pin,
   cleanup precedent; HUB_NAV_LABELS gains `"community": "Community"`
   — the golden pins "↩ Community"). Ctx-bound timeout view
   (`view.message = await ctx.send(...)`) ⇒ `session_lifecycle=True`:
   `<cid:1>..<cid:3>`, no panel_anchors row.
3. **The five subcommand guard lanes, shipped order verbatim**:
   `!ticket new` → empty-subject usage byte FIRST ("Describe your
   issue: `!ticket new <subject>`."), then the open lane's
   REASON_NOT_CONFIGURED eligibility refusal;
   `!ticket add/remove/claim/close` → "This isn't an open ticket
   channel." (the in-channel guard runs BEFORE the staff/opener
   authority re-checks — those need the ticket row). No perms
   decorators on the shipped subcommands (in-body checks only) ⇒
   `audience_tier="user"` everywhere.
4. **G-10 modal**: "Open a ticket" opens the shipped TicketOpenModal
   ("Open a support ticket", subject field) — `DeferMode.MODAL`,
   submit → the not-configured refusal at the v1 epoch.
5. **Zero declared surfaces, zero exemptions** — the shipped ticket
   config/rows lived in the oracle's OWN tables ("not the generic
   set_setting pipeline"); neither exists in the v1 schema epoch, and
   this slice declares only what it fully carries: `stores=()` /
   `settings=()` / `events=()` ⇒ the A-16 floor passes with NO
   depth.exemptions rows (first flip since the floor got teeth to
   need none). Under-port boundary centralized in
   `sb/domain/ticket/service.py` (config store, provisioning open
   flow, launcher/control panels, `!ticketsetup`/`!ticketpanel`/
   `!ticketblacklist` → the ticket-mutation slice). Zero-vs-ensure:
   every guard lane was a PURE read — goldens pin the absence of any
   ticket-owned db_delta row.
6. **The deletes cost nothing**: every golden's trailing
   `delete_message` is reason-less → the `invoking-message-deletion`
   disposition (parity.yml) drops it from both docs.

## Flip mechanics

- parity.yml: `ticket: ported`; ratchet `{events: 1, tables: 2,
  settings: 0}` (scratch-learned via `--write-ratchet`, file restored,
  hand-applied — the raw covered-side counts: xp.awarded; xp +
  ai_decision_audit).
- Gate: 124/124 goldens across 21 ported subsystems green on real
  Postgres; `check_parity_depth` OK; sim gate OK (1004 assignments,
  339 auto-exempt); namespace clean; 1302 tests.

## New traps (playbook-worthy)

- (a) A golden CAN pin a wire `emoji` field next to the label — check
  the shipped view's decorator form before reaching for
  glyph-in-label; `PanelActionSpec.emoji` + the twin's
  `_component_payload` already carry it.
- (b) A subsystem whose goldens are ALL guard bytes can flip with
  `stores=()` and ZERO depth exemptions — don't invent stores just to
  exempt them; declare only what the slice fully carries and
  centralize the under-port boundary in the service module.
- (c) `HUB_NAV_LABELS` growth is golden-cited one label at a time
  (community joined admin/moderation here).

## 💡 Session idea

(Backfilled 2026-07-11 in kit-upgrade PR #159, grammar-only: the original
session recorded no idea. Backfill exists so the strict session-gate's
newest-card-by-mtime pick cannot red CI on this card — see PR #159's card.)

## ⟲ Previous-session review

(Backfilled 2026-07-11 in kit-upgrade PR #159, grammar-only: the original
session recorded no previous-session review.)
