# superbot-next · status
updated: 2026-07-10T17:26Z
phase: band-5 — BUILD leg (#95, four seams fixed forward, D-0062) + REPLAY leg (#97, worldcard Reply fix) landed earlier; pre-live-drive runtime fixes landed via #105 (merge `2c222e1`): compensators for `moderation.timeout` + `proof_channel.end_access`, the class-killer compensator invariant (`tests/unit/workflow/test_compensator_invariant.py` — 97 ops scanned, allowlist empty), and the ORDER-009 flag-13 dispositions applied to the parity machinery (`sb/adapters/parity/dispositions.py` + `parity/parity.yml` `dispositions:` + `docs/parity/flag-13-disposition-2026-07-10.md`). ▶ NEXT LANE: band-5 LIVE-DRIVE (testing ladder step 7 — replay leg done, live leg pending; ORDER 011 hosts-optional binds the prep), then band-6 (games — highest state-machine risk)
health: green with the standing red-by-design (golden-parity dashboard red while rows are `pending`; parity 0/465 green, 0/49 ported; bands 1-4 0/91 classified, band-5 0/12 classified). Unit suite 1140 passed 4 skipped (local, this session, post-#105); 6/6 required checks green on #105 (the 7th `report` check is the red-by-design dashboard, not required). Flag-13 dispositions are now IN the machinery, so the first pending→ported flip (help — ORDER-004 item 2) is UNBLOCKED and is the next parity move
kit: v1.6.0 · check: green · engaged: yes
last-shipped: #105 (merge `2c222e1` — compensators + invariant + flag-13 dispositions, ORDER 009) + the session-close PR carrying this heartbeat (enders for #99/#101/#105 sessions, ORDER 010 doctrine in docs/collaboration-model.md). Note: #104 (merge `926908c`) landed from another lane — inbox reconciliation appending ORDER 011 (SB_TEST_DB_HOSTS optional+silent, renumbered after the manager's ORDER 010 took the slot via #103)
blockers: ORDER 002 done-when still hangs ONLY on the owner-created separate repo (OWNER-ACTION 2 below); old SuperBot still shares `!` in the test guild (flag 15, owner-side) — a live-drive nuisance, see the grants block below
orders: acked=001,002,003,004,005,006,007,008,009,010 done=003,005,006,007,008,009,010
⚑ needs-owner: two OWNER-ACTION items below (six-field format per control/README.md). OWNER-ACTION 1 (flag-13 corpus-red ruling) is CLEARED — accepted per ORDER 009 / Q-0262.3, applied in #105, decision record `docs/parity/flag-13-disposition-2026-07-10.md`

ORDER 008 record (required by its done-when — the exact call + outcome, armed by the coordinator session 2026-07-10):
Tool: mcp__claude-code-remote__create_trigger. Arguments: {"name":"builder-wake","cron_expression":"0 */2 * * *","persistent_session_id":"cse_01HRfuSKiQSnGHXKne3yzadg","prompt":"2-HOURLY WAKE (Builder): sync to origin/main HEAD; read control/inbox.md at HEAD; advance the current band; decide-and-flag owner questions (resolve reversible ones yourself; park true owner-only asks as six-field OWNER-ACTION entries); ship something real every wake (a build is better than no build); heartbeat overwrite last. If this trigger is one-shot rather than recurring, re-arm it for +120 minutes before ending the turn."}
Outcome: SUCCESS — trigger trig_01VYZQ7GHxYq3ecSw8UNZek8, name builder-wake, cron "0 */2 * * *", enabled=true, recurring, target session_01HRfuSKiQSnGHXKne3yzadg (coordinator), next_run_at 2026-07-10T18:02:45Z, created_via meta_mcp, verified via list_triggers. Note: even-hour :00 slot is shared with substrate-kit's routine; fleet-manager reads at :30 — per §5 stagger spec, acceptable.

live-drive grants (§0.4 pre-live-drive readiness, checked this session):
- test app token: PRESENT in session env (`DISCORD_BOT_TOKEN_PRODUCTION` — connects as the test bot; env var NAME only, no value recorded)
- privileged-intent env flags: `SB_INTENT_MSGCONTENT_OK` / `SB_INTENT_MEMBERS_OK` NOT set in the current env (portal toggles documented ON; unset ⇒ degrade-by-design)
- prefix conflict: NOT cleared — old SuperBot still shares `!` in the test guild (flag 15, owner-side)
- test guild id: present in docs (1350952413737259151)
- live-drive leg NOT started — it is the next session's lane

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
notes: ORDER 010 is done= above: the rule now lives durably in `docs/collaboration-model.md` § Standing @codex review (+ a one-line ritual pointer in control/README.md), and the first substantive Builder PR after the order (#105) carried the @codex question on its final head. ORDER 008 is done= on the strength of the record above (routine ACTIVE, recurring, verified via list_triggers). ORDER 009 is done=: dispositions applied in #105 + OWNER-ACTION 1 cleared this overwrite. ORDER 011 (hosts-optional, appended via #104 from another lane) is read but NOT claimed — it binds the live-drive prep and belongs to the next session's lane per its own "execute BEFORE the live-drive leg". Ender catch-up in this PR: the #101 session had no session log (catch-up log `.sessions/2026-07-10-effect-leg-gaps-idea.md` created, honestly marked); the #99 session's log (`.sessions/2026-07-10-idea-seeds.md`) already existed complete with both enders — no change needed. Follow-up seeded, not done: `docs/ideas/effect-leg-compensation-gaps-2026-07-10.md` frontmatter still says `shipped_pr: null` although #105 shipped it — the next docs pass should flip it
