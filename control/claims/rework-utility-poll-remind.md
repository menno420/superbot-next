# Curation rework — utility panel Poll/Remind modal ingress — `rework-utility-poll-remind`

> **CLAIM (2026-07-13)** — curation rework lane (evidence:
> `docs/review/curation-report-2026-07-13.md` L1356-1357 REWORK rows +
> the consolidated backlog's "utility.panel poll/remind ×2" item). Modal
> ingress collecting the args, submit delegating to the live
> `utility.poll_view` / `utility.remind_view` code paths; the
> `utility.poll_pending` / `utility.remind_pending` terminals retire.
> EXCLUDED: the 🔗 Invite button + row-1 lead comment (PR #332's hunks,
> same file, different lines).

- `claude/rework-utility-modals` · **curation REWORK rows utility.panel.poll + utility.panel.remind — modal ingress onto live poll_view/remind_view ops** — G-10 ModalSpecs on the two buttons, submit handlers share the command twins' outcome lanes, the two pending terminals retire · sb/domain/utility/, tests/, manifest.snapshot.json · 2026-07-13
