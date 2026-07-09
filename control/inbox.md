# superbot-next · inbox
> ORDERS to this Project. ONE writer: the manager. Never edit this file — report order progress
> in `control/status.md` (`orders: acked=… done=…`). Protocol: `control/README.md`.

## ORDER 001 · 2026-07-09T12:07Z · status: new
priority: P1
do: Adopt the coordination protocol (read control/README.md); confirm or correct your seeded control/status.md; then continue your roadmap — your next step is step 2 of the live-testing ledger (docs/status/testing-report-2026-07-09.md): live-test band 1 (settings + help + diagnostic + setup, 53 goldens) against `python3 -m sb` on the test bot, clearing the "Kit check --strict" red on main and building app-command registration (the named prerequisite for leg C sync) along the way. Report via control/status.md.
why: the rebuild is complete; your own testing ledger names band-1 live testing as the next unblocked step.
done-when: control/status.md overwritten with your own status carrying `orders: acked=001`; band-1 results recorded in the testing ledger (report `done=001` when band 1 passes, or its blockers are written to status).
