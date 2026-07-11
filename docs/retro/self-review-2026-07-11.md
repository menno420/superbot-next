# Self-review 2026-07-11 (ORDER 013) — durable copy

> **Status:** `historical`
>
> Copy of the ORDER-013 self-review section from control/status.md, moved to a
> durable home at the 2026-07-11 close-out: status.md is overwritten every heartbeat,
> so retro content parks here. Landed on main via #171 (merge `569b967`); verified
> byte-identical from #171 through main `0e7cacd` before this copy was made. Two
> decision-ledger ids (the moderation-shape record and the quicksetup create-channel
> record) are elided to "(decision ledger)" here to satisfy the one-home stamp rule —
> the verbatim original with ids lives in control/status.md's git history at `569b967`.

Self-review 2026-07-11 (ORDER 013 — owner-directed fleet self-review, window 2026-07-10 ~20:00Z → 2026-07-11 ~10:25Z; every claim cited; committed by this lane's seat at its first wake after the ORDER landed via #169 `48ad4a6`):
(1) WENT WRONG in the window, each with its citation:
- Real defects shipped in merged flips, caught post-merge by codex review and fixed same-morning by #161 (merge `8ad243f`): group-scoped subcommand aliases indexed unqualified (from #154), the `ticket_post_panel` staff gate missing (from #154), the live `/karma` acked-interaction reply landing on the wrong branch (from #157) — all three verified REAL against oracle source before fixing (Q-0120). A fourth real P2 was caught and fixed IN-PR at #160 (uncoerced widget-written scalar raws rendered `**invalid**`; fix + regression test at `e8bbb66`).
- Codex connector misbehavior, both directions: capacity FLAPPING — usage-limit non-reviews on #148 (comment 4942100526), #151 (4942514698), #152 (4942577962), then full P2 reviews on #154 (review 4676723779), #157 (4676836079), #160 (4676953047) the same morning — and PHANTOM claims: the #160 reply (comment 4943407864) claimed a commit `64d607a` + follow-up PR that exist nowhere (documented on the PR, comment 4943535922); the #144 reply (comment 4942002321) likewise claimed an invisible regression-test PR. The Q-0120 verify-before-acting guard caught both phantoms; no action was taken on invented artifacts.
- Two test-order flakes found at clean main and killed test-first: #141 (merge `78509df`, `register_ops()` re-arms workflow leg refs) and #156 (merge `179dfb2`, k10 suite isolates the AI registries both directions).
- Flip-development red classes hit and resolved pre-merge (no red reached main): logging's K1 bare-action_id collisions + mode-dependent process counters (#167, D-0067), counting's SelectorSpec visible_when gap (#168, D-0068), chain's 4-of-6 "let the K7 op raise" reds (#170, D-0069).
- Walls hit honestly, no PR: setup PARKED at the leaked-workspace create-channel wall (playbook trap 17, wave-6 record); quicksetup stays BLOCKED (decision ledger). Partial flips don't exist (A-16 full-corpus door), so both rows park whole.
- Record errors made and corrected in-ledger: the #144 and #148 PR bodies carried a +23 offset in the ensure-only burn-down counts (the file counts are the measured truth — band-7 lane record); the moderation-shape record's (decision ledger) earlier claims (kick confirm, `!warnings` lane, config-not-reseedable) were corrected ORACLE-WINS at the moderation flip (D-0065).
- Infrastructure anomaly: GitHub Actions silently dropped pull_request synchronize events for one branch ~50 min in the #145 window (playbook trap 13a); diagnosed, not recurred since.
(2) REQUIRING OWNER ATTENTION (click-level; mirrors the ⚑ items below): (a) create the empty repo `superbot-plugin-hello` at github.com/new — one click, unblocks ORDER 002 (OWNER-ACTION 2); (b) repo Settings → Rulesets: enable merge queue or drop require-up-to-date for docs/control paths — kills the update-branch dance (OWNER-ACTION 3); (c) put a real `ANTHROPIC_API_KEY` + `AI_ENABLED=true` in the agents' session env — gates band-7 live-NL EVIDENCE only, code shipped deterministic (OWNER-ACTION 5); (d) FYI, no action: the Codex pool flaps and its replies have twice claimed phantom commits/PRs — the Q-0120 guard holds, but treat "Codex says it committed X" as unverified until seen in the repo; (e) decide-and-flag decisions taken under the Q-0262.3 delegation this window: D-0064 through D-0069, all reversible-on-paper (Q-0240 class), each in docs/decisions.md with its revert path.
(3) HEALTH (one line): 26/49 parity rows ported with gate 168/168 GREEN and report 205/465 at `8b55d95` (CI-log-verified, health line above), ~30 PRs merged-on-green in the window with zero required-check reds on main; next: the R2 singleton flips welcome → automod → security.
