# 2026-07-11 — chain parity flip (pending→ported, the twenty-sixth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `chain` parity row pending→ported through the A-16 door.
Oracle: menno420/superbot `disbot/cogs/chain_cog.py` @58040c6 (the
group + create/delete/setlimit/removelimit/list subcommands, the
_ChainMenuView and its modal quartet, build_embed — reconstructed via
search_code fragments; full-file oracle reads stay denied, playbook
trap 3/15f). Goldens: `parity/goldens/chain/` — sweep_chain,
sweep_chain_create, sweep_chain_delete, sweep_chain_list,
sweep_chain_removelimit, sweep_chain_setlimit, sweep_chainmenu.
Pre-flip 1/7 (only the bare-group usage hint was exact) → post 7/7.

## What shipped

1. **Handler-owned guard bytes** (sb/domain/chain/service.py): the
   shipped cog validated args/state ITSELF and replied its own
   literals; the band-6 port let the K7 ops raise, so four sweeps
   rendered the kernel's generic "Missing/invalid argument: …"
   envelope. Moved to the shipped sequencing: create's missing-word
   usage literal, delete's store pre-check ("❌ No active chain found
   in <#…>."), setlimit's `None or <= 0` guard (the shipped setlimit
   REJECTS 0 — the band-6 "0 removes it" affordance retired, modal
   field label updated), removelimit's not_found info branch
   ("ℹ️ No word limit is set in <#…>."), the list empty-state byte
   ("ℹ️ There are no active chains or word limits in this server.").
2. **The shipped _ChainMenuView** (sb/domain/chain/panels.py):
   session-lifecycle (run-minted `<cid:N>`, zero panel_anchors, NO nav
   row), the shipped rows — ➕ Create Chain / 🗑️ Delete Chain / 📏 Set
   Limit / 🚫 Clear Limit on row 0, 🔄 Refresh on row 1, emoji INSIDE
   the labels — under the blue "⛓️ Chain Manager" embed with the
   state-dependent description and the "Use buttons below to manage
   chains." footer via renderer_override (embed-only; the declared
   components delegate to render_panel — the logging/counting lane).
   The G-10 modal quartet keeps its compat-pinned modal_ids; the
   invented List button came off (the shipped view had none). Refresh
   re-opens a fresh send (the projmoon edit-in-place class, ledgered).
3. **parity.yml**: chain ported (26/49); ratchet
   `chain: {events: 1, tables: 2, settings: 0}` (raw covered-side).
   ONE depth exemption on a **NEW reason class `guard-only-capture`**
   (decision record D-0069, the D-0063/D-0064 vocabulary-growth
   pattern): `table:chain_channels` — the writing commands ARE
   corpus-expressible (no modal/select/channel-provision wall), but
   the imported sweep drove every subcommand BARE, so each captured
   case pins the guard byte (all five now answered verbatim) and no
   imported golden can carry a row. None of the existing classes'
   grounds (structural inexpressibility / env resource / schema epoch)
   hold — the honest ground is capture COVERAGE, minted in the open
   with its own deletion clause (first argful capture). Compensator
   allowlist stays EMPTY; zero sim-gate/compat churn (trap 12d).
4. **Under-port note (in-code)**: the shipped non-empty `!chain list`
   is an EMBED ("Active Chains and Word Limits", green, channel-name
   fields) — Reply carries text only; the embed shape lands with a
   result-card slice. No golden pins the branch.

## Traps confirmed / new intel

- **The band-6 "let the op raise" shape is a proven red class**: the
  oracle's cogs answered guard literals BEFORE their service calls —
  any sweep pinning a ❌/ℹ️-prefixed plain-content reply that the port
  renders as "Missing/invalid argument: …" means the guard belongs in
  the handler, not the engine envelope. Four of chain's five reds were
  this one class.
- **A new depth reason class is the honest move when the write is
  expressible but unswept** — stretching modal-driven/select-driven to
  a command lane would misstate the ground; the closed vocabulary's
  own "reviewed schema change" rule is the sanctioned door (D-0069;
  check_parity_depth reads the class list from parity.yml, no code or
  pinned-test growth needed).
- **Emoji-in-label vs separate emoji field is per-VIEW, not per-bot**:
  chain's shipped buttons carry emoji inside the label strings (the
  `label="➕ Create Chain"` form) while channel/ticket used the
  decorator emoji= field — check the golden's wire shape per panel
  (trap 15a's advice held again).
- Traps 1 (ratchet scratch-learn/restore/hand-apply), 12d (zero
  lock/compat churn for session panels), 16e (importlib
  `_replay_corpus`) confirmed as written.

## Verification

- goldens/chain 7/7 green (isolation replay); full gate **168/168
  across 26 ported** on real Postgres; report leg 205/465 green,
  465/465 replayable; check_parity_depth OK — 49 subsystems (26
  ported), 465 goldens; check_sim_gate OK (1040 [A], 355 auto-exempt);
  check_compat_frozen OK (modal_ids unchanged); check_namespace /
  intent_survival / slash_cap / egress / no_skip clean; unit suite
  **1356 passed, 2 skipped** local (canonical order).

## 💡 Session idea

`guard-only-capture` likely fits several remaining pending rows whose
sweeps were also argument-less (welcome, security, image_moderation
are settings-heavy R2 singletons the LANE END note pre-named) — when
those flips hit the same "expressible but unswept" wall, cite D-0069
instead of re-arguing; and a future ARGFUL capture sweep (one pass
driving each mutating command with a canonical argument) would delete
the whole class in one corpus regeneration.

## ⟲ Previous-session review

(This previous-session review covers the counting flip, #168.) The
counting card's claim that the #167 channel-select/required machinery
needed zero transport work held for chain too — zero transport edits
this slice. The counting session-hub lane (override composes the
embed, components stay declared) transferred verbatim; chain needed
no component-set filtering since the shipped view is state-independent
in its controls, confirming the counting override's component-drop is
the exception, not the default. The @codex question on #168 (unminted
canonical ids on a future edit-in-place remap) got no reply before
merge — capacity flap; the question stands on the thread.
