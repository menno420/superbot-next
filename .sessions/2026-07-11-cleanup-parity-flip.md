# 2026-07-11 — cleanup parity flip (pending→ported, the thirteenth row)

> **Status:** `complete`

- **📊 Model:** Claude Fable 5 · high · feature build (Q-0194)

## Scope

Flip the `cleanup` parity row pending→ported through the A-16 door — the
first flip whose golden pins a Discord READ effect (`logs_from`).
Oracle: menno420/superbot `disbot/cogs/cleanup/panel.py`
(`CleanupPanelView`) + `disbot/cogs/cleanup_cog.py` (the word-menu view
+ `cleanup_history`); goldens: `parity/goldens/cleanup/` —
sweep_cleanup (the 🧹 hub), sweep_wordmenu (the 🔤 words manager) and
sweep_cleanuphistory (the channel-history scan). The band-2 manifest
already carried the word-filter K7 lane (`!word add/remove/list`,
prohibited_words store) and a placeholder read-view hub; this PR
replaces the placeholder with the REAL shipped panels and retires the
`!cleanuphistory` pending terminal.

## What shipped

1. **`!cleanup` opens the shipped Cleanup Hub byte-for-byte** —
   `sb/domain/cleanup/panels.py`: the 🧹 red embed (the shipped blurb;
   the LIVE `Prohibited Words` count field — `{n} configured` /
   `_None configured_`, marked inline via renderer_override; the
   Auto-Delete literal; the "Read-only summary." footer) over the
   shipped rows — 🔤 Prohibited Words / 📝 Logging Status / ⚙️ Settings
   / 🧹 Cleanup Policies, then 🔄 Refresh, then the shipped STANDARD
   nav row (`nav:help` + `nav:hub:moderation` "↩ Moderation" —
   `HUB_NAV_LABELS` grows its golden-pinned `moderation` entry). Every
   declared component carries its shipped PERSISTENT `cleanup:*`
   custom_id verbatim (`custom_id_override`; `session_lifecycle=True`
   with every id override-pinned — nothing minted, no `panel_anchors`
   row, the settings-hub precedent). K1: bare `refresh` is treasury's
   repo-global claim, so the action_id is `cl_refresh` under the
   verbatim wire override (the sm_refresh precedent). 🔤 routes to the
   ported words manager; 🔄 re-renders in place (REFRESH_PANEL); the
   rest land on declared + honest pending terminals.
2. **`!wordmenu` opens the shipped Prohibited Words Manager** — the 🔤
   red session view: NO description, the two fields, the "Use buttons
   below" footer, over ➕ Add Word / ➖ Remove Word / 🔄 Refresh and
   🔍 Scan History / 🛡️ Anti-evasion. The shipped view minted
   discord.py auto-ids — no overrides, `_mint_ephemeral` mints run ids
   in declared order (the golden pins `<cid:1>`..`<cid:5>`); no nav row
   (session-view never-strand exemption, the general-menu precedent).
3. **`!cleanuphistory` runs the shipped scan** — the pending terminal
   retires. A NEW domain history-reader port
   (`sb/domain/cleanup/service.py`, the moderation-actions posture:
   uninstalled ⇒ honest refusal) carries the shipped
   `ctx.channel.history(limit=...)` read; the parity twin
   (`ParityHistoryReader`) records the goldens' `logs_from` wire verb
   — the FIRST Discord-read effect in the flip lane. The handler ports
   the shipped clamp (min(limit, 1000)), mode vocabulary
   (prohibited default) and the 0-match summary copy verbatim
   ("Scanned 0 message(s) (requested 100, effective 100). Matched 0
   messages for `prohibited`."). Shipped tier: manage_messages →
   `moderator`; the panel doors gain the shipped `administrator` tier.
4. **Sim gate** — manifest/layout/cleanup.lock.json AMENDED additively
   (the 7 band-2 command rows stay) with both panels' arrangement rows;
   baseline regen. Compat pin amended additively (5 new `cleanup:*`
   legacy custom_ids — gate 6 fired as designed).
5. **The flip**: `parity.yml` `cleanup: ported` + the A-16 ratchet row
   `cleanup: {events: 1, tables: 2, settings: 0}` (xp +
   ai_decision_audit from the ported message pipeline). R2 is NOT
   vacuous: cleanup declares the `prohibited_words` store its three
   read-only goldens never write — one depth-exemption row lands under
   the EXISTING `covered-elsewhere` class (the K7 word lane's write
   bytes are pinned by goldens/_unmapped/sweep_word_add.json's
   prohibited_words row — the settings-flip sweep_setlogchannel
   precedent). The declared SettingSpec never bites: snapshot settings
   carry `settings_key`, not `key`, so R2's declared-settings set is
   structurally empty (checker fact, noted below).

Gate leg: 35/35 goldens across 13 ported subsystems GREEN against real
Postgres. Dashboard moves 12 → 13 ported (of 49); report leg 47 green
(of 465). Full suite 1277 passed.

## Notes

- **Deliberate under-ports (in-code notes):** the words manager's
  `Current Words` value is the golden-pinned literal `` `test` `` — the
  shipped view read `self.cog._word_cache` (process memory), and the
  capture's alphabetical sweep order left `!word add test` in that
  cache when `!wordmenu` ran (the per-case DB truncate cannot reach a
  cog attribute), so the golden pins LEAKED CACHE STATE, not a DB read;
  the live read + honest empty state land with the word-mutation panel
  slice. Same slice: the anti-evasion field literal, the word-menu
  button modals. The scan's transient ⚠️ over-limit helper
  (delete_after=7) and the matched>0 deletion leg are the channel-ops
  slice's port (the handler refuses honestly).
- The reasonless invoking-message/self deletes in all three goldens
  (cleanuphistory's summary was deleted TWICE — the helper sweep + the
  cleanup stage both hit it) ride the ruled `invoking-message-deletion`
  disposition (ORDER 009) — no new classes.
- R2 checker fact worth knowing: `declared_surfaces` reads setting
  dicts' `key` field, but the compiler serializes SettingSpec with
  `settings_key`/`name` — declared settings are structurally EMPTY for
  every subsystem, so a SettingSpec can never trip the floor today.

## 💡 Session idea

The A-16 R2 settings dimension is dead code: the snapshot serializes
`SettingSpec.settings_key`, but `check_parity_depth.declared_surfaces`
looks up `s["key"]` — so the "every declared setting key exercised or
exempt" floor has never examined a single setting (every ratchet
`settings:` count comes from the covered side only). One line in the
checker (`s.get("settings_key") or s.get("key")`) arms the dimension —
but it will RED several already-ported rows at once (utility, channel,
blackjack declare settings their goldens never touch), so it wants its
own sweep PR with the exemption rows prepared, not a drive-by fix.

## ⟲ Previous-session review

The settings card's R2 lesson ("scan the corpus for sibling oracles
BEFORE the flip commit") converted directly: the
`table:prohibited_words` exemption cited sweep_word_add on the first
depth-checker run — zero re-cycles, and the citation grep took one
command. What it under-delivered: it did not mention that
`covered-elsewhere` had only ever cited CONFIG-lane siblings; this row
needed a domain-store citation (`prohibited_words`), which the class
wording ("a named sibling oracle") covers fine — but the next flip that
finds NO sibling golden touching a declared store has no ruled class to
reach for (quicksetup-style park, or a new-class decision record).
