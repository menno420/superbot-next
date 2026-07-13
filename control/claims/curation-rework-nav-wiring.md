# Curation rework — panel nav/handler wiring claim — `curation-rework-nav-wiring`

> **CLAIM (2026-07-13)** — curation rework lane (SuperBot World night run,
> ORDER 017 item 2; evidence: `docs/review/curation-report-2026-07-13.md`,
> PR #327). This lane claims the "panel nav/handler wiring" bundle — three
> trivial handler swaps that retire pending terminals whose live
> destinations already ship — so a concurrent fleet does not duplicate any
> wiring. Earlier-at-HEAD claim wins on any collision.

**Scope.** Three shipped buttons whose clicks land on pending terminals
while their live targets exist at HEAD:

1. `server_management.hub` — the Moderation / Roles / Cleanup manager trio
   forwards to the PORTED `moderation.hub` / `role.hub` / `cleanup.hub`
   panels (the Channels/Setup `PanelRef` pattern in the same spec).
2. `mining.workshop` — `ws_back` (↩ Workshop) navigates to the live
   `mining.hub` (the `sk_hub` / vault / forge back-button pattern).
3. `utility.panel` — the 🔗 Invite button routes to the live argless
   `utility.invite_view` handler (the `!invite` command's route).

**EXCLUDED.** Cleanup panels (`cleanup.words` + `cleanup.hub.logging` ride
a sibling curation-rework lane) and btd6 (paragon rides its own lane).

- `curation-rework-nav-wiring` · **curation rework — wire server_management hub nav (moderation/roles/cleanup) + mining ws_back + utility invite to live targets** — retires 5 pending terminals with existing live destinations · sb/domain/server_management/panels.py, sb/domain/mining/panels.py, sb/domain/utility/panels.py, tests/ · 2026-07-13
