# superbot-next · status
updated: 2026-07-10T18:25Z
phase: band-5 — testing ladder step 7 COMPLETE: replay leg (#95, four seams fixed forward, D-0062; #97, worldcard Reply fix) + LIVE-DRIVE leg done via #109 (merge `b813324`; artifacts: `docs/status/testing-report-2026-07-09.md` step-7 block + `.sessions/2026-07-10-band5-live-drive.md`). Live leg: bot booted to gateway READY on the test plane, all ported role/proof_channel surfaces exercised live, the #105 compensators fired live with zero stranded rows, DB left clean. ▶ NEXT LANE: band-5 live-bug fix lane — 3 live-only bugs found in #109's ledger: (1) role pending terminals unregistered live (RefUnresolved: `handler:role.create_pending`; root cause `ensure_handler_refs()` never invoked by the live root with zero plugins), (2) setrole/unsetrole/removereactrole acks read nonexistent `result.after["record"]` → "None" copy over correct writes, (3) `!temprole` failure copy leaks raw WorkflowResult repr — plus role/proof_channel live EFFECT action ports (GuildRoleActions, ChannelPermActions unarmed) — then band-6 (games — highest state-machine risk)
health: green with the standing red-by-design (golden-parity dashboard red while rows are `pending`; parity 0/465 green, 0/49 ported; bands 1-4 0/91 classified, band-5 0/12 classified). Unit suite 1143 passed 2 skipped (post-#107); 6/6 required checks green on #107/#108/#109 (the 7th `report` check is the red-by-design dashboard, not required). Flag-13 disposition machinery landed in #105 — NEXT PARITY MOVE: first pending→ported flip = help (ORDER-004 item 2), now unblocked
kit: v1.6.0 · check: green · engaged: yes
last-shipped: #107 (ORDER 011 — SB_TEST_DB_HOSTS fully optional/silent; merge `5fcc1a9`; unit suite 1143 passed 2 skipped) + #108 (proof_channel.end_access compensator race fix — codex review 4673572674 CONFIRMED against source; compensation now insert-only via `insert_lock_if_absent` ON CONFLICT DO NOTHING + regression test `test_end_access_compensation_yields_to_concurrent_regrant`; idea-doc effect-leg-compensation-gaps frontmatter flipped to `shipped_pr: 105`; merge `02c4664`; parked follow-up: symmetric `_compensate_lock` delete-only race, documented in docstring) + #109 (live-drive artifacts; merge `b813324`). All merged green on the 6-check ruleset ("report" red-by-design)
blockers: ORDER 002 done-when still hangs ONLY on the owner-created separate repo (OWNER-ACTION 2 below). No band-5 owner blockers remain — both anticipated live-leg blockers cleared owner-side (intent flags present; flag 15 resolved, see grants block)
orders: acked=001,002,003,004,005,006,007,008,009,010,011 done=003,005,006,007,008,009,010,011
⚑ needs-owner: two OWNER-ACTION items below (six-field format per control/README.md). OWNER-ACTION 1 (flag-13 corpus-red ruling) is CLEARED — accepted per ORDER 009 / Q-0262.3, applied in #105, decision record `docs/parity/flag-13-disposition-2026-07-10.md`

ORDER 008 record (required by its done-when — the exact call + outcome, armed by the coordinator session 2026-07-10):
Tool: mcp__claude-code-remote__create_trigger. Arguments: {"name":"builder-wake","cron_expression":"0 */2 * * *","persistent_session_id":"cse_01HRfuSKiQSnGHXKne3yzadg","prompt":"2-HOURLY WAKE (Builder): sync to origin/main HEAD; read control/inbox.md at HEAD; advance the current band; decide-and-flag owner questions (resolve reversible ones yourself; park true owner-only asks as six-field OWNER-ACTION entries); ship something real every wake (a build is better than no build); heartbeat overwrite last. If this trigger is one-shot rather than recurring, re-arm it for +120 minutes before ending the turn."}
Outcome: SUCCESS — trigger trig_01VYZQ7GHxYq3ecSw8UNZek8, name builder-wake, cron "0 */2 * * *", enabled=true, recurring, target session_01HRfuSKiQSnGHXKne3yzadg (coordinator), next_run_at 2026-07-10T18:02:45Z, created_via meta_mcp, verified via list_triggers. Note: even-hour :00 slot is shared with substrate-kit's routine; fleet-manager reads at :30 — per §5 stagger spec, acceptable.

live-drive grants (§0.4 readiness — LIVE-VERIFIED this session via the #109 live leg):
- test app token: PRESENT in session env (`DISCORD_BOT_TOKEN_PRODUCTION` — connects as the test bot; env var NAME only, no value recorded)
- privileged-intent env flags: `SB_INTENT_MSGCONTENT_OK` / `SB_INTENT_MEMBERS_OK` ARE present (=true) in env — zero degrade markers at gateway READY
- prefix conflict: RESOLVED owner-side (flag 15) — old SuperBot removed from test guild 1350952413737259151 (REST 404 Unknown Member); `!` prefix now uncontested
- app-command sync: `SB_APPCMD_SYNC_GUILD_ID=1522099141671653417` now targets the new owner guild "Superbot Admin" (12 commands synced there; test guild retains the earlier 13) — deserves an owner confirm-of-intent line but is NOT a blocker
- env fact: `HEALTH_HOST` default `::` cannot bind in the build container (no IPv6); `HEALTH_HOST=127.0.0.1` required
- test guild id: present in docs (1350952413737259151)
- live-drive leg: DONE (#109, merge `b813324`)

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

carried (unchanged, full detail in the retro §2): sacrificial member (flag 9), settings-EDIT/setup-FLOW boundary (flags 14/17a), hub topology (flag 21), band-7 AI key envelope, owner hand-pass of presentation surfaces — incl. the band-4 human keystroke check (a real message should earn 15-25 XP on a 60s cooldown via !rank). Flag 15 dropped from this list — resolved owner-side (grants block above)
notes: ORDER 011 is done= above with its done-when fully met: live boot verified with SB_TEST_DB_HOSTS unset (one loud WARNING line, gateway READY, clean SIGTERM exit) + tests pin the new behavior + docs updated (#107, merge `5fcc1a9`). ORDER 008 remains done= on the strength of the record above (routine ACTIVE, recurring, verified via list_triggers). The #105 follow-up flagged last heartbeat is CLOSED: `docs/ideas/effect-leg-compensation-gaps-2026-07-10.md` frontmatter flipped to `shipped_pr: 105` in #108. New parked follow-up from #108: the symmetric `_compensate_lock` delete-only race, documented in the compensator docstring. The 3 live-only bugs in the phase line (from #109's ledger) are the fix lane's work queue — none is owner-blocking
