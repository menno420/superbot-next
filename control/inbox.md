# superbot-next · inbox
> ORDERS to this Project. ONE writer: the manager. Never edit this file — report order progress
> in `control/status.md` (`orders: acked=… done=…`). Protocol: `control/README.md`.

## ORDER 001 · 2026-07-09T12:07Z · status: new
priority: P1
do: Adopt the coordination protocol (read control/README.md); confirm or correct your seeded control/status.md; then continue your roadmap — your next step is step 2 of the live-testing ledger (docs/status/testing-report-2026-07-09.md): live-test band 1 (settings + help + diagnostic + setup, 53 goldens) against `python3 -m sb` on the test bot, clearing the "Kit check --strict" red on main and building app-command registration (the named prerequisite for leg C sync) along the way. Report via control/status.md.
why: the rebuild is complete; your own testing ledger names band-1 live testing as the next unblocked step.
done-when: control/status.md overwritten with your own status carrying `orders: acked=001`; band-1 results recorded in the testing ledger (report `done=001` when band 1 passes, or its blockers are written to status).

## ORDER 002 · 2026-07-09T14:15Z · status: new
priority: P2
do: Game-plugin contract (owner decision 2026-07-09: each new game lives in its OWN repo as a plugin package the host consumes — this order builds the host side; do NOT let it derail live-testing, interleave after the current band). Deliver: (1) a packaging/import strategy so an external repo can develop against the kernel (sb.spec / manifest types) — e.g. installable sb package or documented git-dependency pattern; (2) plugin discovery + registration at the composition root (an installed plugin exports its SubsystemManifest; host compiles + hash-pins it like in-tree subsystems); (3) a minimal hello-world plugin example (one command + one panel) proving the path; (4) docs: the plugin contract (what a plugin may declare, which kernel seams it gets — economy, game-XP, EffectiveStats, panels — and what stays host-owned). Dedicated game Projects (mining; exploration/D&D) will build against this.
why: unblocks the fleet's game-domain Projects on the architecture the manifest system was built for.
done-when: hello-world plugin from a separate repo registers and renders in the test guild; contract doc committed; status reports done=002.
