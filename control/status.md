# superbot-next · status
updated: 2026-07-09T19:31Z
phase: vendored substrate-kit upgraded v1.2.0 → v1.6.0 (third real-world `upgrade` run; sha256 verified against release.json + .sha256 + asset digests; archive-first, from_version honest, inputs self-cleaned). Inherited since 1.2.0: v1.3.0 `kit:` heartbeat line + adopters registry, v1.4.0 configurable heartbeat_files, v1.5.0 docs/CAPABILITIES.md + orientation wiring, v1.6.0 owner-action six-field checker + order-claim convention. Three template-improved docs applied via `--apply-docs` (CONSTITUTION, collaboration-model, AGENT_ORIENTATION); two diverged control docs manually merged (this file's format + control/README.md protocol extensions). Band 5 (governance/roles/platform, ladder step 7) remains the next build lane — unchanged by this kit-maintenance session
health: red-by-design (golden-parity dashboard red while rows are `pending` — unchanged class; bands 1-4 0/91 all classified). Everything else green: pytest, manifest recompile, checker fleet, `check --strict` (sole red during the session was this session's own born-red card — the gate as designed; owner-action advisory settled by this six-field rewrite)
kit: v1.6.0 · check: green · engaged: yes
last-shipped: #96 — kit upgrade v1.2.0 → v1.6.0 (CAPABILITIES.md planted + hash-recorded, control protocol extensions merged, heartbeat format upgraded); before it #94 (band-4 status debt heartbeat), #92 (ORDER-006 project review), #93 (ORDER-007 ping ack)
blockers: ORDER 002 done-when still hangs ONLY on the owner-created separate repo (menno420/superbot-plugin-hello — see OWNER-ACTION 2 below); ORDER-004 item 2 (help byte-parity + first A-16 flip) still ⚑ GATED on the flag-13 kernel-surface-drift ruling (see OWNER-ACTION 1 below; no ruling in the inbox as of 19:31Z — inbox still ends at ORDER 007)
orders: acked=001,002,003,004,005,006,007 done=003,005,006,007
⚑ needs-owner: three OWNER-ACTION items below (six-field format per control/README.md; full ten-item leverage-ordered list: docs/retro/project-review-2026-07-09.md §2 — items there predate the VERIFIED-NEEDED field)

⚑ OWNER-ACTION 1 — corpus-red disposition ruling (flag 13)
WHAT: Decide what to do with the three known "old bot vs new bot output differs" classes so parity rows can be marked done.
WHERE: append an inbox ORDER to control/inbox.md (or a doc in docs/ the ORDER points at).
HOW: choose per class — exemption rows / normalizer scope / accepted-forever red — for kernel event+audit shapes, the old `xp.coins` alias column, and the invoking-message deletion.
WHY-IT-MATTERS: bands 1-4 are 0/91 with every red already classified; the classification work is done and only the POLICY call is missing.
UNBLOCKS: ORDER-004 item 2 (help byte-parity, the first A-16 pending→ported flip), every later band's flips, the `report` CI leg going green.
VERIFIED-NEEDED: this is a product-policy decision (which output differences the owner accepts forever), not a technical wall — agents wrote the class ledger but cannot ratify acceptance on the owner's behalf.

⚑ OWNER-ACTION 2 — create the hello-plugin repo (flag 18a)
WHAT: Create one new empty GitHub repository named superbot-plugin-hello.
WHERE: https://github.com/new (owner account menno420).
HOW: name `superbot-plugin-hello`, public, no template — agents then move `examples/superbot-plugin-hello/` verbatim (pin hashes the manifest, not the repo — no re-pin needed).
WHY-IT-MATTERS: it proves a game plugin can live in its own repo, the architecture the mining/exploration game Projects will copy.
UNBLOCKS: ORDER 002 → done; the game Projects' reference pattern.
VERIFIED-NEEDED: attempted repo-create with the integration token — GitHub returns 403 on repo creation for this token class (recorded in docs/retro/project-review-2026-07-09.md §2 item 2); only the owner account can create repos.

⚑ OWNER-ACTION 3 — kill the branch-update merge dance
WHAT: Change the repo merge settings so PRs stop needing a manual "update branch" click before merging.
WHERE: github.com/menno420/superbot-next → Settings → Rules/Rulesets (or Settings → General → merge queue).
HOW: enable the merge queue, or drop the require-up-to-date rule for `docs/**` + `control/**` paths.
WHY-IT-MATTERS: every session lost time to the update-branch dance and one session's tail was stranded on it (PRs #86/#87), and the same dance triggered a rate-limit stall.
UNBLOCKS: unattended session wrap-ups; less API traffic.
VERIFIED-NEEDED: repo Settings/Rulesets are admin-only — agent tokens can read but not modify rulesets (the #86/#87 stranding is the captured evidence of the wall in effect); an agent re-verified it cannot edit the ruleset when un-stranding those PRs.

carried (unchanged, full detail in the retro §2): sacrificial member (flag 9), old SuperBot shares `!` (flag 15), settings-EDIT/setup-FLOW boundary (flags 14/17a), hub topology (flag 21), band-7 AI key envelope, owner hand-pass of presentation surfaces — incl. the band-4 human keystroke check (a real message should earn 15-25 XP on a 60s cooldown via !rank)
notes: this heartbeat was written by the kit-upgrade session (PR #96), not a band session — band-5 state is carried unchanged from the 18:11Z heartbeat. Kit specifics: upgrade-report classification consumer-edited 7 · diverged 2 (control/README.md + this file — both manually merged this session) · missing 1 (docs/CAPABILITIES.md — replanted fully rendered, hash recorded) · template-improved 3 (applied) · unchanged 6. `check:` green above = the verdict once this session's card flips complete (during the session the sole strict red was that born-red card; the v1.6.0 owner-action advisory fired on the old heartbeat format and is settled by this rewrite). The staged .substrate/ci/substrate-gate.yml remains deliberately NOT installed (ci.yml already runs `check --strict`; the owner's 6-check ruleset stands — same decision as the v1.2.0 upgrade). Claim convention note: this session executed no inbox order (kit maintenance, coordinator-dispatched), so no claimed-by line; ORDER-claiming is now live protocol per control/README.md § Claiming an order
