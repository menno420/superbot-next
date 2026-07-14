"""Curated deep-flow goldens — multi-step scenarios the sweep cannot reach.

Selection rationale (mirrors the grammar spike's difficulty spread):
karma (simple domain + audited seam + typed errors), economy (INV-F money
paths), logging (operator config: scalar + binding lanes), settings hub +
help (the generated-panel surfaces the rebuild replaces), blackjack
(stateful game session — the escape-hatch-heavy class).
"""

from __future__ import annotations

from parity.harness.cases import GoldenCase, Step

__all__ = ["CURATED_CASES"]

CURATED_CASES: tuple[GoldenCase, ...] = (
    # ------------------------------------------------------------- karma
    GoldenCase(
        id="karma.thanks_grant",
        subsystem="karma",
        steps=(
            Step(
                kind="command",
                content="!thanks <@900000000000000103> for the parity help",
                persona="member",
                mentions=("second_member",),
            ),
            Step(
                kind="command",
                content="!karma <@900000000000000103>",
                persona="member",
                mentions=("second_member",),
            ),
        ),
        notes="grant + card; asserts the audited karma seam + karma.granted event",
    ),
    GoldenCase(
        id="karma.self_grant_rejected",
        subsystem="karma",
        steps=(
            Step(
                kind="command",
                content="!thanks <@900000000000000102>",
                persona="member",
                mentions=("member",),
            ),
        ),
        notes="typed SelfKarmaError → friendly rejection, no DB delta",
    ),
    GoldenCase(
        id="karma.repeat_cooldown",
        subsystem="karma",
        steps=(
            Step(
                kind="command",
                content="!thanks <@900000000000000103>",
                persona="member",
                mentions=("second_member",),
            ),
            Step(
                kind="command",
                content="!thanks <@900000000000000103>",
                persona="member",
                mentions=("second_member",),
            ),
        ),
        notes="second grant inside the per-recipient cooldown → typed error",
    ),
    GoldenCase(
        id="karma.slash_card",
        subsystem="karma",
        steps=(Step(kind="slash", name="karma", persona="member"),),
        notes="slash front door — ephemeral card via interaction response",
    ),
    # ----------------------------------------------------------- economy
    GoldenCase(
        id="economy.balance_and_daily",
        subsystem="economy",
        steps=(
            Step(kind="command", content="!balance", persona="member"),
            Step(kind="command", content="!daily", persona="member"),
            Step(kind="command", content="!balance", persona="member"),
        ),
        notes="INV-F: daily grant lands in economy + economy_audit_log",
    ),
    # ----------------------------------------------------------- logging
    GoldenCase(
        id="logging.enable_and_bind",
        subsystem="logging",
        steps=(
            Step(kind="command", content="!logging", persona="admin"),
            Step(kind="command", content="!logging enable", persona="admin"),
            Step(
                kind="command",
                content="!logging set mod __CHANNEL_MOD-LOG__",
                persona="admin",
            ),
        ),
        notes="operator config flow: scalar toggle + channel pointer write",
    ),
    # ------------------------------------------------------ settings hub
    GoldenCase(
        id="settings.hub_open",
        subsystem="settings",
        steps=(Step(kind="command", content="!settings", persona="admin"),),
        notes="the settings hub panel — component tree is the golden",
    ),
    # -------------------------------------------------------------- help
    GoldenCase(
        id="help.panel_open",
        subsystem="help",
        steps=(Step(kind="command", content="!help", persona="member"),),
        notes="the help panel projection + nav components",
    ),
    # --------------------------------------------------------- blackjack
    GoldenCase(
        id="blackjack.solo_round_hit",
        subsystem="blackjack",
        steps=(
            Step(kind="command", content="!daily", persona="member"),
            Step(kind="command", content="!blackjack 10", persona="member"),
            Step(
                kind="click",
                target_message=2,
                component_index=0,
                persona="member",
            ),
        ),
        notes=(
            "stateful game session: escrow through INV-F, dynamic session "
            "custom_ids, first button (Hit) clicked"
        ),
    ),
    # --------------------------------------------------------- creature PvP
    GoldenCase(
        id="creature.battle_accept",
        subsystem="creature",
        # both fighters own a full one-per-element team so the 6v6 resolves
        # (the collection-log writer — !catch — is capture-skipped for
        # unseeded RNG, so the pool is fixture-seeded, like the stateful
        # game cases; D-0079). Seeded BEFORE the before-snapshot, so the
        # rows never appear in db_delta — only the battle's own writes do.
        fixture_sql=(
            "INSERT INTO creature_collection_log "
            "(user_id, guild_id, creature, count, first_caught, last_caught) "
            "VALUES "
            "(900000000000000102, 700000000000000001, 'Cindling', 1, 1000000000, 1000000000),"
            "(900000000000000102, 700000000000000001, 'Rippling', 1, 1000000000, 1000000000),"
            "(900000000000000102, 700000000000000001, 'Sproutle', 1, 1000000000, 1000000000),"
            "(900000000000000102, 700000000000000001, 'Voltkit', 1, 1000000000, 1000000000),"
            "(900000000000000102, 700000000000000001, 'Pebblet', 1, 1000000000, 1000000000),"
            "(900000000000000102, 700000000000000001, 'Zephyrl', 1, 1000000000, 1000000000)",
            "INSERT INTO creature_collection_log "
            "(user_id, guild_id, creature, count, first_caught, last_caught) "
            "VALUES "
            "(900000000000000103, 700000000000000001, 'Emberpaw', 1, 1000000000, 1000000000),"
            "(900000000000000103, 700000000000000001, 'Splashfin', 1, 1000000000, 1000000000),"
            "(900000000000000103, 700000000000000001, 'Thornkit', 1, 1000000000, 1000000000),"
            "(900000000000000103, 700000000000000001, 'Sparkpup', 1, 1000000000, 1000000000),"
            "(900000000000000103, 700000000000000001, 'Gravelpup', 1, 1000000000, 1000000000),"
            "(900000000000000103, 700000000000000001, 'Gustling', 1, 1000000000, 1000000000)",
        ),
        steps=(
            Step(
                kind="command",
                content="!cbattle <@900000000000000103>",
                persona="member",
                mentions=("second_member",),
            ),
            # only the challenged player (second_member) may Accept — the
            # first component on the challenge card (D-0079).
            Step(
                kind="click",
                target_message=1,
                component_index=0,
                persona="second_member",
            ),
        ),
        notes=(
            "challenge -> Accept auto-resolves the 6v6 and records the W/L "
            "pair + battle-win game-xp (creature.record_battle_result); the "
            "resolved outcome card now carries the live 🔄 Rematch button"
        ),
    ),
    GoldenCase(
        id="creature.cbattle_bot_guard",
        subsystem="creature",
        steps=(
            # !cbattle against the guild's bot member (World.BOT_USER_ID) —
            # the shipped opponent.bot guard, now live over MemberInfo.is_bot.
            Step(
                kind="command",
                content="!cbattle <@500000000000000001>",
                persona="member",
            ),
        ),
        notes=(
            "the shipped opponent.bot guard: !cbattle against a bot member "
            "is BLOCKED ('🤖 You can't battle a bot…') with no challenge "
            "card and an empty db_delta — the MemberInfo.is_bot seam"
        ),
    ),
    GoldenCase(
        id="creature.challenge_picker",
        subsystem="creature",
        steps=(
            # open the hub, then the shipped Challenge button opens the
            # native user-select opponent picker (wire type 5)…
            Step(kind="command", content="!creatures", persona="member"),
            Step(kind="click", target_message=1, component_index=2,
                 persona="member"),
            # …and selecting a trainer opens the challenge card (the
            # selected id rides the ordinary select `values` round-trip).
            # The picker is an ephemeral followup (no click-targetable
            # message id), so the select is driven by its stable custom_id
            # on the originating hub message — the dex-browse control
            # precedent (goldens/creature/creature_dex_filter_element).
            Step(kind="click", target_message=1,
                 custom_id="creature.challenge_select.challenge_opponent",
                 component_type=5, persona="member",
                 values=("900000000000000103",)),
        ),
        notes=(
            "the native member picker: hub Challenge opens a user_select "
            "(wire type 5); selecting a trainer routes through "
            "creature.challenge_pick into the Accept/Decline challenge card"
        ),
    ),
    # NOTE (slice 3 — Rematch): the 🔄 Rematch button rides the resolved
    # OUTCOME card, which is an in-place edit (edit_followup, no
    # click-targetable message id) whose session-minted button custom_ids
    # cannot be referenced from the static case model — so a rematch-CLICK
    # golden is not cleanly capturable here. The affordance's rendered bytes
    # ARE pinned: creature.battle_accept's resolved-card output now carries
    # the live 🔄 Rematch button (re-minted this slice). The handler
    # (creature.challenge_rematch) is unit-covered.
    # ------------------------------------------------------------- casino
    GoldenCase(
        id="casino.poker_full_hand",
        subsystem="casino",
        steps=(
            Step(kind="command", content="!poker", persona="admin"),
            Step(kind="click", target_message=1, component_index=0,
                 persona="member"),                          # Join
            Step(kind="click", target_message=1, component_index=2,
                 persona="admin"),                           # Start → deal
            Step(kind="click", target_message=2, component_index=1,
                 persona="admin"),                           # preflop SB call
            Step(kind="click", target_message=2, component_index=1,
                 persona="member"),                          # BB check
            Step(kind="click", target_message=2, component_index=1,
                 persona="member"),                          # flop check
            Step(kind="click", target_message=2, component_index=1,
                 persona="admin"),                           # flop check
            Step(kind="click", target_message=2, component_index=1,
                 persona="member"),                          # turn check
            Step(kind="click", target_message=2, component_index=1,
                 persona="admin"),                           # turn check
            Step(kind="click", target_message=2, component_index=1,
                 persona="member"),                          # river check
            Step(kind="click", target_message=2, component_index=1,
                 persona="admin"),                           # river check → showdown
        ),
        notes=(
            "minted (D-0073): a full headless Texas Hold'em hand — lobby → "
            "seat → deal → check/call betting rounds → showdown, public "
            "spectator embed pinned per action (per-player ephemeral hands "
            "ride the owner-armed live step, D-0045)"),
    ),
    # --------------------------------------------------------- blackjack
    GoldenCase(
        id="blackjack.tournament_full_flow",
        subsystem="blackjack",
        steps=(
            # open a free, single-round tournament (fee 0, rounds 1)
            Step(kind="command", content="!bjtournament 0 1", persona="admin"),
            # member signs up via the 🃏 Join button
            Step(kind="click", target_message=1, component_index=0,
                 persona="member"),
            # member clicks Join again → the duplicate-registration refusal
            Step(kind="click", target_message=1, component_index=0,
                 persona="member"),
            # a second player signs up → the roster reaches two
            Step(kind="click", target_message=1, component_index=0,
                 persona="second_member"),
            # admin launches: per-entrant welcome + first round table view
            Step(kind="command", content="!bjstart", persona="admin"),
            # each entrant Stands their single round (Stand = 2nd button)
            Step(kind="click", target_message=3, component_index=1,
                 persona="member"),
            Step(kind="click", target_message=5, component_index=1,
                 persona="second_member"),
        ),
        notes=(
            "full tournament wire: open → Join button sign-ups (incl. the "
            "'You're already registered!' duplicate refusal) → !bjstart "
            "launch → per-entrant round → all-done settle → champion payout "
            "+ results embed (self-cleaning: end_tournament + clear_active)"
        ),
    ),
    GoldenCase(
        id="blackjack.tournament_paid_flow",
        subsystem="blackjack",
        # Both entrants are pre-funded via fixture_sql (BEFORE the
        # before-snapshot, so the seed credits never appear in db_delta —
        # only the tournament's own money legs do). 100 🪙 each clears the
        # 25 🪙 join affordability gate; the fee debits at launch, not join.
        fixture_sql=(
            "INSERT INTO economy_balances (user_id, guild_id, coins) VALUES "
            "(900000000000000102, 700000000000000001, 100), "
            "(900000000000000103, 700000000000000001, 100)",
        ),
        steps=(
            # open a PAID single-round tournament (fee 25, rounds 1)
            Step(kind="command", content="!bjtournament 25 1", persona="admin"),
            # member signs up via the 🃏 Join button (affordability passes)
            Step(kind="click", target_message=1, component_index=0,
                 persona="member"),
            # a second player signs up → the roster reaches two
            Step(kind="click", target_message=1, component_index=0,
                 persona="second_member"),
            # admin launches: per-entrant fee debit (tournament:entry_fee)
            # + first round table view
            Step(kind="command", content="!bjstart", persona="admin"),
            # each entrant Stands their single round (Stand = 2nd button)
            Step(kind="click", target_message=3, component_index=1,
                 persona="member"),
            Step(kind="click", target_message=5, component_index=1,
                 persona="second_member"),
        ),
        notes=(
            "minted (D-0073): the PAID-pot money path #302's free-tournament "
            "golden left unpinned — open (fee 25) → two Join sign-ups → "
            "!bjstart debits each entrant 25 (tournament:entry_fee) → "
            "per-entrant round → all-done settle → champion paid the pooled "
            "50 pot (blackjack:tournament_win) + clear_active, self-cleaning. "
            "CONSERVATION: the two 25 entry_fee debits sum to the single 50 "
            "tournament_win payout — the exact economy_audit_log rows are the "
            "golden's assertion (no coins minted or stranded on the paid leg)"
        ),
    ),
    # ----------------------------------------------------- rps tournament
    GoldenCase(
        id="rps.tournament_foreign_active_refusal",
        subsystem="rps_tournament",
        # a live blackjack tournament owns the shared active_tournament flag
        fixture_sql=(
            "INSERT INTO guild_settings (guild_id, key, value) "
            "VALUES (700000000000000001, 'active_tournament', 'blackjack')",
        ),
        steps=(
            Step(kind="command", content="!rpsregister", persona="admin"),
        ),
        notes=(
            "cross-game guard (#277): !rpsregister refuses to open on top of "
            "a foreign (blackjack) tournament with the oracle-verbatim copy — "
            "the regression lock for the stranded-pot money bug"
        ),
    ),
    # ------------------------------------------------------------ events
    GoldenCase(
        id="moderation.warn_flow",
        subsystem="moderation",
        steps=(
            Step(
                kind="command",
                content="!warn <@900000000000000103> parity test warning",
                persona="admin",
                mentions=("second_member",),
            ),
            Step(
                kind="command",
                content="!warnings <@900000000000000103>",
                persona="admin",
                mentions=("second_member",),
            ),
        ),
        notes="moderation.action_taken event + mod_logs write + server_logging fan-out",
    ),
    GoldenCase(
        id="xp.chat_award",
        subsystem="xp",
        steps=(
            Step(kind="command", content="hello parity world", persona="member"),
            Step(kind="command", content="!rank", persona="member"),
        ),
        notes="message-pipeline XP award (xp.awarded event) + rank card",
    ),
    # ------------------------------------------ browse-interaction goldens
    # Multi-step click/select captures for the two armed browse surfaces (the
    # shared BrowserView engine, D-0034): open the panel → drive a browse
    # control (a `nav:browse:*` sort/filter/page click or the dex element
    # filter select) → capture the RE-RENDERED panel. These fix the corpus's
    # interaction blind spot (before: one button click corpus-wide; the
    # sort/filter selects had none). Seed data rides fixture_sql (the D-0073
    # btd6_strategies-insert precedent) so the re-render provably differs from
    # the default open. The member (id …102) views their OWN inventory, so the
    # detail provider's target defaults to the actor; the seeded category is
    # the only non-empty one, so its hub button is component_index 0. The
    # browse control's static `nav:browse:*` id fully encodes the panel + state
    # (browserview.encode), so it re-renders on the same interaction turn (a
    # type-7 update) regardless of which minted message carries it.
    GoldenCase(
        id="inventory.browse_sort_quantity",
        subsystem="inventory",
        fixture_sql=(
            "INSERT INTO inventory (user_id, guild_id, item_name, quantity) "
            "VALUES (900000000000000102, 700000000000000001, 'diamond', 1), "
            "(900000000000000102, 700000000000000001, 'gold', 5), "
            "(900000000000000102, 700000000000000001, 'iron', 50), "
            "(900000000000000102, 700000000000000001, 'stone', 3), "
            "(900000000000000102, 700000000000000001, 'wood', 7)",),
        steps=(
            Step(kind="command", content="!inventory", persona="member"),
            Step(kind="click", target_message=1, component_index=0,
                 persona="member"),
            Step(kind="click", target_message=1,
                 custom_id="nav:browse:sort:inventory.cat_mining_materials:0:0:-1:0",
                 values=("-quantity",), persona="member"),
        ),
        notes=(
            "BrowserView sort select: open Mining Materials (default rarity "
            "sort: Diamond/Gold/Iron/Stone/Wood) then pick '-quantity' — the "
            "re-render reorders highest-first (Iron 50 → Diamond 1), proving "
            "the sort click path"),
    ),
    GoldenCase(
        id="inventory.browse_filter_ore",
        subsystem="inventory",
        fixture_sql=(
            "INSERT INTO inventory (user_id, guild_id, item_name, quantity) "
            "VALUES (900000000000000102, 700000000000000001, 'diamond', 1), "
            "(900000000000000102, 700000000000000001, 'gold', 5), "
            "(900000000000000102, 700000000000000001, 'iron', 50), "
            "(900000000000000102, 700000000000000001, 'stone', 3), "
            "(900000000000000102, 700000000000000001, 'wood', 7)",),
        steps=(
            Step(kind="command", content="!inventory", persona="member"),
            Step(kind="click", target_message=1, component_index=0,
                 persona="member"),
            Step(kind="click", target_message=1,
                 custom_id="nav:browse:filter:inventory.cat_mining_materials:0:0:-1:0",
                 values=("Ore",), persona="member"),
        ),
        notes=(
            "BrowserView filter select: open Mining Materials (all 5 items) "
            "then filter to type 'Ore' — the re-render drops to the three Ore "
            "items (Gold/Iron/Stone), proving the filter click path"),
    ),
    GoldenCase(
        id="inventory.browse_page_next_prev",
        subsystem="inventory",
        # 11 non-catalogue items land in the 'Other' category (page_size 8), so
        # the detail paginates to two pages — the only way to exercise the page
        # buttons (no single catalogue category holds >8 items).
        fixture_sql=(
            "INSERT INTO inventory (user_id, guild_id, item_name, quantity) "
            "VALUES " + ", ".join(
                f"(900000000000000102, 700000000000000001, 'trinket_{i:02d}', {i + 1})"
                for i in range(11)),),
        steps=(
            Step(kind="command", content="!inventory", persona="member"),
            Step(kind="click", target_message=1, component_index=0,
                 persona="member"),
            Step(kind="click", target_message=1,
                 custom_id="nav:browse:next:inventory.cat_other:0:0:-1:0",
                 persona="member"),
            Step(kind="click", target_message=1,
                 custom_id="nav:browse:prev:inventory.cat_other:0:0:-1:1",
                 persona="member"),
        ),
        notes=(
            "BrowserView page buttons: open Other (Page 1/2, items 1–8) → "
            "next (Page 2/2, items 9–11) → prev (back to Page 1/2), proving "
            "both page-turn click paths and the bound-disable states"),
    ),
    GoldenCase(
        id="creature.dex_filter_element",
        subsystem="creature",
        # the dex renders all 36 catalog creatures (caught or not), so the
        # element filter re-renders differently with no seed data.
        steps=(
            Step(kind="command", content="!creatures", persona="member"),
            Step(kind="click", target_message=1, component_index=1,
                 persona="member"),
            Step(kind="click", target_message=1,
                 custom_id="nav:browse:filter:creature.dex:0:-1:-1:0",
                 values=("Stone",), persona="member"),
        ),
        notes=(
            "dex element filter select: open the interactive dex via the hub "
            "Dex button (default: the first page across all six elements) then "
            "filter to 'Stone' — the re-render shows only the Stone creatures, "
            "proving the element-filter select path"),
    ),
    # ---------------------------------------------- mining WRITE-PARITY (WP-1)
    # Argful equip / unequip / loadout writes that DRIVE the mutation the
    # imported bare-guard sweeps never reached (D-0069 class exit). Each
    # fixture_sql row is seeded BEFORE the before-snapshot, so it never appears
    # in db_delta — only the terminal's own audited write does. member persona
    # = 900000000000000102, guild = 700000000000000001. The success reply is
    # the shipped `<@u> ` mention + oracle copy (mining_workflow.equip/unequip/
    # loadout verbatim). These row-bearing captures retire the
    # depth.exemptions.mining guard-only-capture rows for mining_equipment
    # (equip add + unequip remove) and mining_loadout_presets (save add +
    # delete remove).
    GoldenCase(
        id="mining.equip_write",
        subsystem="mining",
        # own the gear so the equip success branch runs (inventory read is a
        # pre-req, not a write — seeded before the snapshot).
        fixture_sql=(
            "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
            "quantity) VALUES "
            "('900000000000000102', 700000000000000001, 'iron pickaxe', 1)",
        ),
        steps=(
            Step(kind="command", content="!equip iron pickaxe",
                 persona="member"),
        ),
        notes=(
            "argful !equip drives mining.equip → record_equip: upserts the "
            "mining_equipment tool-slot row (item_name='iron pickaxe') and "
            "replies `<@u> equipped **Iron Pickaxe** in the **tool** slot.` — "
            "the first row-bearing equip capture (retires the "
            "mining_equipment guard-only-capture exemption)"),
    ),
    GoldenCase(
        id="mining.unequip_write",
        subsystem="mining",
        # seed the equipped row so unequip yields a `removed` mining_equipment
        # delta (the delete face of the table).
        fixture_sql=(
            "INSERT INTO mining_equipment (user_id, guild_id, slot, "
            "item_name) VALUES "
            "('900000000000000102', 700000000000000001, 'tool', "
            "'iron pickaxe')",
        ),
        steps=(
            Step(kind="command", content="!unequip tool", persona="member"),
        ),
        notes=(
            "argful !unequip drives mining.unequip → record_unequip: deletes "
            "the mining_equipment tool-slot row and replies `<@u> cleared the "
            "**tool** slot.` — the remove face of mining_equipment"),
    ),
    GoldenCase(
        id="mining.loadout_save_write",
        subsystem="mining",
        # equipped gear is the save source (read pre-req); seeded before the
        # snapshot so only the loadout-preset row lands in db_delta.
        fixture_sql=(
            "INSERT INTO mining_equipment (user_id, guild_id, slot, "
            "item_name) VALUES "
            "('900000000000000102', 700000000000000001, 'tool', "
            "'iron pickaxe')",
        ),
        steps=(
            Step(kind="command", content="!loadout save mining",
                 persona="member"),
        ),
        notes=(
            "argful !loadout save drives mining.save_loadout → "
            "record_save_loadout: inserts the mining_loadout_presets row(s) "
            "for the equipped gear and replies `<@u> saved your current gear "
            "as the **mining** loadout (1 slot).` — the first row-bearing "
            "loadout capture (retires the mining_loadout_presets "
            "guard-only-capture exemption)"),
    ),
    GoldenCase(
        id="mining.loadout_apply_write",
        subsystem="mining",
        # a saved preset + owned gear: apply equips the preset item, writing a
        # mining_equipment row (the preset row is a read pre-req, unchanged).
        fixture_sql=(
            "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
            "quantity) VALUES "
            "('900000000000000102', 700000000000000001, 'sword', 1)",
            "INSERT INTO mining_loadout_presets (user_id, guild_id, name, "
            "slot, item_name) VALUES "
            "('900000000000000102', 700000000000000001, 'combat', 'weapon', "
            "'sword')",
        ),
        steps=(
            Step(kind="command", content="!loadout apply combat",
                 persona="member"),
        ),
        notes=(
            "argful !loadout apply drives mining.apply_loadout → "
            "record_apply_loadout: equips the preset's owned gear "
            "(mining_equipment weapon-slot row) and replies `<@u> equipped "
            "the **combat** loadout (1 slot).` — the loadout apply write face"),
    ),
    GoldenCase(
        id="mining.loadout_delete_write",
        subsystem="mining",
        # seed the preset so delete yields a `removed` mining_loadout_presets
        # delta (the delete face of the table).
        fixture_sql=(
            "INSERT INTO mining_loadout_presets (user_id, guild_id, name, "
            "slot, item_name) VALUES "
            "('900000000000000102', 700000000000000001, 'combat', 'weapon', "
            "'sword')",
        ),
        steps=(
            Step(kind="command", content="!loadout delete combat",
                 persona="member"),
        ),
        notes=(
            "argful !loadout delete drives mining.delete_loadout → "
            "record_delete_loadout: deletes the mining_loadout_presets "
            "row(s) named 'combat' and replies `<@u> deleted the **combat** "
            "loadout.` — the remove face of mining_loadout_presets"),
    ),
    # ---------------------------------------------- mining WRITE-PARITY (WP-2)
    # Argful vault writes (stash / unstash / stash-all / vaultupgrade) that
    # DRIVE the mutation the imported bare-guard sweeps never reached (D-0069
    # class exit). Same personas as WP-1: member = 900000000000000102, guild =
    # 700000000000000001. economy_balances keys user_id as BIGINT (no quotes);
    # the mining tables key user_id as TEXT (quoted). Each fixture_sql row is
    # seeded BEFORE the before-snapshot, so only the terminal's own audited
    # write lands in db_delta. Success copy is the shipped `<@u> ` mention +
    # oracle mining_workflow vault_deposit/withdraw/deposit_all/upgrade text,
    # verbatim. These row-bearing captures retire the depth.exemptions.mining
    # guard-only-capture rows for mining_vault (stash add + unstash remove) and
    # mining_player_state (vault_level, covered by the funded upgrade).
    GoldenCase(
        id="mining.stash_write",
        subsystem="mining",
        # own the ore so the deposit success branch runs (inventory read is a
        # pre-req, not a write — seeded before the snapshot).
        fixture_sql=(
            "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
            "quantity) VALUES "
            "('900000000000000102', 700000000000000001, 'diamond', 5)",
        ),
        steps=(
            Step(kind="command", content="!stash diamond 5",
                 persona="member"),
        ),
        notes=(
            "argful !stash drives mining.stash → record_stash: debits the "
            "mining_inventory pack row and credits the mining_vault row in one "
            "txn, and replies `<@u> Deposited **5× diamond** into your vault — "
            "safe and out of your pack.` — the first row-bearing deposit "
            "capture (retires the mining_vault guard-only-capture exemption)"),
    ),
    GoldenCase(
        id="mining.unstash_write",
        subsystem="mining",
        # seed the vault stack so the withdraw yields a `removed` mining_vault
        # delta (the withdraw face of the table).
        fixture_sql=(
            "INSERT INTO mining_vault (user_id, guild_id, item_name, "
            "quantity) VALUES "
            "('900000000000000102', 700000000000000001, 'diamond', 5)",
        ),
        steps=(
            Step(kind="command", content="!unstash diamond 5",
                 persona="member"),
        ),
        notes=(
            "argful !unstash drives mining.unstash → record_unstash: debits "
            "the mining_vault row and credits the mining_inventory pack row in "
            "one txn, and replies `<@u> Withdrew **5× diamond** from your vault "
            "back into your pack.` — the withdraw face of mining_vault"),
    ),
    GoldenCase(
        id="mining.stash_all_write",
        subsystem="mining",
        # seed a sellable resource in the pack; the 📦 Stash All Ore button
        # moves every sellable resource pack -> vault in one txn.
        fixture_sql=(
            "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
            "quantity) VALUES "
            "('900000000000000102', 700000000000000001, 'iron', 7)",
        ),
        steps=(
            # !vault mints the 🏦 Mining Vault panel (session-lifecycle child);
            # the 📦 Stash All Ore button is flattened component index 2
            # (deposit 0, withdraw 1, stash-all 2, upgrade 3, hub 4, nav 5/6 —
            # goldens/mining/sweep_vault pins the order). The session-minted
            # custom_id normalizes to <cid:N>; component_index reconstructs it.
            Step(kind="command", content="!vault", persona="member"),
            Step(kind="click", target_message=1, component_index=2,
                 persona="member"),
        ),
        notes=(
            "!vault then the 📦 Stash All Ore click drives mining.stash_all → "
            "record_stash_all: moves every sellable pack resource into the "
            "vault in one txn (mining_inventory debit + mining_vault credit) "
            "and replies `<@u> Stashed 7× iron into your vault.` — the "
            "convenience deposit face (mining_workflow "
            "vault_deposit_all_resources verbatim)"),
    ),
    GoldenCase(
        id="mining.vault_upgrade_write",
        subsystem="mining",
        # fund the balance so the audited debit-and-bump success branch runs
        # (the level read + insufficient-funds guard are pure reads gated out
        # before the leg). economy_balances user_id is BIGINT. cost(0)=2000 →
        # balance 2500 leaves 500 after the buy; capacity(1)=45.
        fixture_sql=(
            "INSERT INTO economy_balances (user_id, guild_id, coins) VALUES "
            "(900000000000000102, 700000000000000001, 2500)",
        ),
        steps=(
            Step(kind="command", content="!vaultupgrade", persona="member"),
        ),
        notes=(
            "argful !vaultupgrade (funded) drives mining.vault_upgrade → "
            "record_vault_upgrade: debits the 2000 🪙 cost via "
            "wager.debit_in_txn and bumps mining_player_state.vault_level 0->1 "
            "in one advisory-fenced txn, and replies `<@u> Vault upgraded to "
            "capacity **45** item types for **2000** 🪙. Balance: **500** 🪙.` "
            "— the funded-upgrade capture that covers the vault_level face of "
            "mining_player_state (retires its guard-only-capture exemption)"),
    ),
    # ------------------------------------------- mining ENERGY (slice 2)
    # Argful !use / !cook writes over the energy lane (docs/scoping/
    # energy-system-scope.md slice 2; oracle copy: disbot/services/
    # mining_workflow.py use_item/cook @ 87bbe1d). Same conventions as the
    # WP-1 block above: fixture rows seed BEFORE the before-snapshot;
    # member persona = 900000000000000102, guild = 700000000000000001;
    # success replies carry the shipped `<@u> ` mention, refusals are
    # PLAIN (the cog's ok=False ctx.send(result.message) branch). The
    # restore capture is the first golden whose db_delta carries a
    # mining_player_state row (retires that guard-only-capture exemption).
    GoldenCase(
        id="mining.use_ration_restore_write",
        subsystem="mining",
        # own a ration + hold a below-cap energy row. energy_updated_at is
        # pinned FUTURE-of-the-logical-clock (2100-01-01 epoch) so settle()
        # clamps elapsed to 0 and the pre-use bar is exactly 10 regardless
        # of the case's logical-time base — deterministic by construction
        # (the same math both bots run; a past stamp would regen to full).
        fixture_sql=(
            "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
            "quantity) VALUES "
            "('900000000000000102', 700000000000000001, 'ration', 1)",
            "INSERT INTO mining_player_state (user_id, guild_id, energy, "
            "energy_updated_at) VALUES "
            "('900000000000000102', 700000000000000001, 10, 4102444800)",
        ),
        steps=(
            Step(kind="command", content="!use ration", persona="member"),
        ),
        notes=(
            "argful !use ration drives mining.use → record_use_item: ONE "
            "txn debits the ration and raises settled energy 10→35 "
            "(RESTORE_VALUES['ration']=25), replying `<@u> You consume "
            "**ration** and recover energy (⚡ 35/60 [▰▰▰▰▰▰▱▱▱▱]).` — the "
            "first mining_player_state row-bearing golden (retires the "
            "guard-only-capture exemption)"),
    ),
    GoldenCase(
        id="mining.use_ration_full_refusal",
        subsystem="mining",
        # own a ration but NO energy row: the (0,0) missing-row default
        # settles to a FULL bar (huge elapsed clamps to MAX_ENERGY), so the
        # full-energy refusal fires and the txn aborts row-less — the
        # ration is NOT consumed (the oracle's pre-txn ok=False twin).
        fixture_sql=(
            "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
            "quantity) VALUES "
            "('900000000000000102', 700000000000000001, 'ration', 1)",
        ),
        steps=(
            Step(kind="command", content="!use ration", persona="member"),
        ),
        notes=(
            "!use ration at a full bar refuses PLAIN (`Your energy is "
            "already full — save it for later.`) with NO mining db_delta — "
            "the item survives (mining_workflow.use_item's pre-write "
            "refusal, ported as a txn-aborting ValidatorError)"),
    ),
    GoldenCase(
        id="mining.cook_campfire_write",
        subsystem="mining",
        # a built campfire (cooking_unlocked ⇔ level ≥ 1; mining_structures
        # user_id is BIGINT, unlike the TEXT inventory ids) + one raw fish.
        fixture_sql=(
            "INSERT INTO mining_structures (user_id, guild_id, structure, "
            "level) VALUES "
            "(900000000000000102, 700000000000000001, 'campfire', 1)",
            "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
            "quantity) VALUES "
            "('900000000000000102', 700000000000000001, 'minnow', 1)",
        ),
        steps=(
            Step(kind="command", content="!cook minnow", persona="member"),
        ),
        notes=(
            "argful !cook minnow behind a built campfire drives mining.cook "
            "→ record_cook: ONE txn debits the minnow and grants 1× cooked "
            "fish, replying `<@u> 🔥 You cook **1× minnow** into **1× "
            "cooked fish** (+30 ⚡ each when eaten — `!use cooked fish`).` — "
            "the fish→meal trade the campfire gate guards"),
    ),
    GoldenCase(
        id="mining.use_torch_flavour",
        subsystem="mining",
        # a non-food consumable: the flavour-only debit branch.
        fixture_sql=(
            "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
            "quantity) VALUES "
            "('900000000000000102', 700000000000000001, 'torch', 1)",
        ),
        steps=(
            Step(kind="command", content="!use torch", persona="member"),
        ),
        notes=(
            "argful !use torch drives the flavour branch: debits the torch "
            "and replies `<@u> You light a torch and peer into the "
            "darkness...` — no energy movement, no mining_player_state row"),
    ),
    # ------------------------------------------------ fishing cast-leg WRITES
    # The first goldens that ever CLICK Reel (the imported sweeps only pinned
    # the waiting panel — parity.yml's own fishing_catch_log exemption text
    # names this exact button-driving capture as its retirement). Each case
    # casts (`!fish` — the wired begin_cast rolls the catch on the runner-armed
    # private cast RNG, spends energy + a bait charge) then clicks the panel's
    # single Reel button by component_index; the click carries the pending
    # cast's identity token through the panel-args binding, and the audited
    # fishing.cast leg commits record_catch → pearl → coral → fish grant →
    # game XP in one txn (the seed-42 species → weight → bonus → pearl →
    # coral trajectory). fixture_sql rows are seeded BEFORE the
    # before-snapshot, so only the cast's own writes land in db_delta. member
    # persona = 900000000000000102, guild = 700000000000000001.
    GoldenCase(
        id="fishing.cast_reel_write",
        subsystem="fishing",
        steps=(
            Step(kind="command", content="!fish", persona="member"),
            Step(kind="click", target_message=1, component_index=0,
                 persona="member"),
        ),
        notes=(
            "fresh player, shore profile — every knob reads exactly neutral "
            "(no-row venue → shore, rod tier 0, no bait, unbuilt structures, "
            "fresh gear): `!fish` spends 2 energy off the fresh full bar "
            "(fishing_energy row 58) and the Reel click drives the audited "
            "fishing.cast leg — the FIRST row-bearing fishing_catch_log "
            "capture (dex row + the caught fish in mining_inventory + the "
            "fishing game-XP award) with the oracle result-card copy "
            "(retires the fishing_catch_log guard-only-capture exemption)"),
    ),
    GoldenCase(
        id="fishing.cast_deepwater_reel_write",
        subsystem="fishing",
        # the loaded profile: deepwater venue + a Silver rod + a Shimmer Lure
        # + built tide pool / dock / fishery — the full effective_pull /
        # effective_bite_speed compound (rod × bait × weather × gear ×
        # structures) plus the fishery-raised double_catch_chance and the
        # coral 0.06 DEEPWATER-ONLY branch (the shore cases never draw it);
        # all read pre-reqs seeded before the snapshot.
        fixture_sql=(
            "INSERT INTO fishing_venue (user_id, guild_id, venue) VALUES "
            "(900000000000000102, 700000000000000001, 'deepwater')",
            "INSERT INTO fishing_rod (user_id, guild_id, tier) VALUES "
            "(900000000000000102, 700000000000000001, 2)",
            "INSERT INTO fishing_bait (user_id, guild_id, bait_key, charges) "
            "VALUES (900000000000000102, 700000000000000001, 'lure', 10)",
            "INSERT INTO mining_structures (user_id, guild_id, structure, "
            "level) VALUES "
            "(900000000000000102, 700000000000000001, 'tide_pool', 2), "
            "(900000000000000102, 700000000000000001, 'dock', 1), "
            "(900000000000000102, 700000000000000001, 'fishery', 2)",
        ),
        steps=(
            Step(kind="command", content="!fish", persona="member"),
            Step(kind="click", target_message=1, component_index=0,
                 persona="member"),
        ),
        notes=(
            "deepwater reel at a loaded profile: the cast panel renders the "
            "boat where-line + the 🪱/🪸/⚓ footer notes, the roll draws from "
            "the DEEPWATER species pool under the compounded pull (Silver rod "
            "1.25 × lure 2.00 × weather × tide pool 1.08), commit rolls "
            "bonus → pearl → coral with the fishery-raised double-catch "
            "chance (0.10 + 0.10) and the deepwater-only 0.06 coral draw — "
            "the seeded trajectory is pinned wherever it lands; db_delta "
            "carries the catch-log row + the lure charge decrement (10→9) + "
            "the size `#N of 11 deepwater` result copy"),
    ),
    GoldenCase(
        id="fishing.cast_bait_spend_write",
        subsystem="fishing",
        # exactly ONE charge left: the cast's per-attempt spend crosses zero
        # and the pack CLEARS (the shipped clear_active_bait — bait_key '' /
        # charges 0), the delta face no other golden pins.
        fixture_sql=(
            "INSERT INTO fishing_bait (user_id, guild_id, bait_key, charges) "
            "VALUES (900000000000000102, 700000000000000001, 'worm', 1)",
        ),
        steps=(
            Step(kind="command", content="!fish", persona="member"),
            Step(kind="click", target_message=1, component_index=0,
                 persona="member"),
        ),
        notes=(
            "the last-charge spend: `!fish` consumes the worm pack's final "
            "charge — the shipped charge-per-attempt rule clears the loadout "
            "at 0, so db_delta pins the fishing_bait row modified to "
            "`('', 0)` (clear-at-0) beside the shore catch commit; the cast "
            "panel footer still shows the spent-from pack (`🪱 Worm Bait (0 "
            "left)`) exactly as the oracle CastStart carried it"),
    ),
    # ------------------------------------- fishing minigame timing (D-0043 s1)
    # The first goldens that drive the CLOCK grammar: each Reel click carries
    # ``advance_s`` (None = the fixed 30 s the whole corpus rides), so the
    # click lands at a chosen offset from the cast — before the rolled bite
    # (premature), or inside the reaction window (hook/fight). Seeds were
    # chosen so the runner-armed cast-RNG trajectory (species → weight →
    # bite → fake-out → [grace|escape…] → commit draws) takes the intended
    # branch; the capture-world weather is storm (CAPTURE_WORLD_WEATHER —
    # registered before the mint), whose 1.12 bite-speed / 1.30 rarity mults
    # are part of each pinned trajectory.
    GoldenCase(
        id="fishing.cast_premature_spook",
        subsystem="fishing",
        steps=(
            Step(kind="command", content="!fish", persona="member"),
            # 0.5 s after the cast — always before the bite (shore floor
            # 1.5 s), and the bare rod's grace 0 can never forgive (no
            # rng draw — roll_premature_grace short-circuits at ≤ 0).
            Step(kind="click", target_message=1, component_index=0,
                 persona="member", advance_s=0.5),
        ),
        notes=(
            "fresh player, bare rod: reeling 0.5 s after the cast is "
            "premature (seed-42 storm bite lands at ~4.28 s) and grace 0 "
            "spooks deterministically — the oracle 🌀 reeled-too-early "
            "terminal (verbatim; NO trophy clue — the oracle never wraps "
            "the premature spook in _got_away), the paid cast is gone, "
            "and db_delta pins the cast's own energy spend (60→58) plus "
            "the passive chat-XP row every command golden carries: no "
            "catch-log row, no fish grant, no game_xp"),
    ),
    GoldenCase(
        id="fishing.cast_premature_grace",
        subsystem="fishing",
        # a Diamond Rod (tier 4, premature_grace 0.60) — the forgive knob.
        fixture_sql=(
            "INSERT INTO fishing_rod (user_id, guild_id, tier) VALUES "
            "(900000000000000102, 700000000000000001, 4)",
        ),
        seed=4,
        steps=(
            Step(kind="command", content="!fish", persona="member"),
            Step(kind="click", target_message=1, component_index=0,
                 persona="member", advance_s=0.5),
        ),
        notes=(
            "the one forgiven slip: seed-4's grace draw (0.067 < 0.60) "
            "forgives the 0.5 s premature reel — the oracle 😅 'the "
            "Diamond Rod steadies it' edit rides the in-place panel "
            "refresh (the cast_prompt override), the cast STAYS parked "
            "(grace spent), and db_delta still pins only the energy "
            "spend — a forgiven slip neither lands nor loses the fish"),
    ),
    GoldenCase(
        id="fishing.cast_trophy_fight_land",
        subsystem="fishing",
        # deepwater at fishing level 2 (cap 6): the seed-2 catch is the
        # lancetfish (#6) — a trophy (threshold 4), a 3-tap fight.
        fixture_sql=(
            "INSERT INTO fishing_venue (user_id, guild_id, venue) VALUES "
            "(900000000000000102, 700000000000000001, 'deepwater')",
            "INSERT INTO game_xp (user_id, guild_id, game, xp) VALUES "
            "(900000000000000102, 700000000000000001, 'fishing', 100)",
        ),
        seed=2,
        steps=(
            Step(kind="command", content="!fish", persona="member"),
            # the hook: seed-2's storm bite lands at ~7.10 s; 8.0 s sits
            # inside the deepwater window (7.10 … 9.10 at window 2.0).
            Step(kind="click", target_message=1, component_index=0,
                 persona="member", advance_s=8.0),
            # three reel taps (rank 6 ⇒ 2 + round(12/21) = 3); every
            # seed-2 escape draw holds (0.835/0.736/0.670 ≥ 0.195).
            Step(kind="click", target_message=1, component_index=0,
                 persona="member", advance_s=1.0),
            Step(kind="click", target_message=1, component_index=0,
                 persona="member", advance_s=1.0),
            Step(kind="click", target_message=1, component_index=0,
                 persona="member", advance_s=1.0),
        ),
        notes=(
            "the trophy reel-fight, landed: the in-window hook flips the "
            "panel to the oracle 🎣 Hooked-a-big-one edit, taps 1-2 "
            "advance the ▰▱ tension bar in place, and tap 3 commits the "
            "audited fishing.cast leg — db_delta pins the lancetfish "
            "catch-log row + fish grant + the game_xp bump off the "
            "level-2 fixture row, with the 🏆 Trophy landed! result card"),
    ),
    GoldenCase(
        id="fishing.cast_trophy_fight_escape",
        subsystem="fishing",
        fixture_sql=(
            "INSERT INTO fishing_venue (user_id, guild_id, venue) VALUES "
            "(900000000000000102, 700000000000000001, 'deepwater')",
            "INSERT INTO game_xp (user_id, guild_id, game, xp) VALUES "
            "(900000000000000102, 700000000000000001, 'fishing', 100)",
        ),
        seed=15,
        steps=(
            Step(kind="command", content="!fish", persona="member"),
            # the hook: seed-15's bite lands at ~11.67 s; 12.5 s is
            # inside the window (11.67 … 13.67).
            Step(kind="click", target_message=1, component_index=0,
                 persona="member", advance_s=12.5),
            # tap 1 holds (0.986 ≥ 0.195)…
            Step(kind="click", target_message=1, component_index=0,
                 persona="member", advance_s=1.0),
            # …tap 2's escape draw fires (0.017 < 0.195) — snapped.
            Step(kind="click", target_message=1, component_index=0,
                 persona="member", advance_s=1.0),
        ),
        notes=(
            "the big one that got away: a lancetfish trophy hooks and "
            "holds one tap, then the per-tap deepwater escape roll fires "
            "— the oracle 💥 snapped-the-line terminal + the 💭 trophy "
            "clue (a fight IS a trophy), the paid cast is gone, and "
            "db_delta pins ONLY the energy spend — no catch-log row, no "
            "fish, no xp movement on the fixture row"),
    ),
    GoldenCase(
        id="fishing.howtofish_rules_card",
        subsystem="fishing",
        steps=(
            Step(kind="command", content="!fishing", persona="member"),
            # …the hub's 📖 How to fish button (row two, after Fishdex —
            # flattened index 6 over the 5+2 layout rows) opens the
            # static rules card as an ephemeral reply.
            Step(kind="click", target_message=1, component_index=6,
                 persona="member"),
        ),
        notes=(
            "the hub 📖 How-to-fish affordance: the shipped rules_btn sent "
            "_rules_embed as an ephemeral component reply (views/fishing/"
            "menu.py) — a fully static purple quick-reference card with no "
            "fields, footer or components and an EMPTY db_delta (a pure "
            "read; the creature rules-card posture). Pins the "
            "oracle-verbatim loop/get-better-catches copy the "
            "fishing.howtofish_pending terminal answered with a stub "
            "until 2026-07-13"),
    ),
    # ------------------------------------------- cleanup anti-evasion WRITE
    # The first golden that CLICKS the words manager's 🛡️ Anti-evasion
    # button (the 2026-07-13 residue port armed it — the imported sweep only
    # pinned the panel open): `!wordmenu` renders the session view (empty DB
    # → the shipped empty-state description + the default-off anti-evasion
    # field), then the component_index click drives the audited
    # cleanup.wordfilter_strict_op — the FIRST row-bearing wordfilter_config
    # capture (migration 0053) with the in-place re-render flipping the
    # field to the shipped 🟢 On literal. admin persona (the words manager
    # is an Administrator surface).
    GoldenCase(
        id="cleanup.anti_evasion_toggle_write",
        subsystem="cleanup",
        steps=(
            Step(kind="command", content="!wordmenu", persona="admin"),
            Step(kind="click", target_message=1, component_index=4,
                 persona="admin"),
        ),
        notes=(
            "the anti-evasion opt-in: the 🛡️ click writes strict=true "
            "through the audited cleanup.wordfilter_strict_op (db_delta "
            "pins the wordfilter_config upsert + the audit row) and the "
            "session view re-renders in place — the anti-evasion field "
            "flips to the shipped 🟢 On copy while the empty word list "
            "keeps the shipped no-words description"),
    ),
    # ------------------------------------------- cleanup policies open
    # The hub's 🧹 Cleanup Policies button (the LAST cleanup pending,
    # retired 2026-07-13 by the cleanup-policy slice): `!cleanup` renders
    # the hub, then the component_index click (row 0: words/logging/
    # settings/POLICIES → flattened 3) opens the ported cleanup.policies
    # diagnostics view — empty DB → the oracle empty state. admin persona
    # (the hub is an Administrator surface).
    GoldenCase(
        id="cleanup.policies_open",
        subsystem="cleanup",
        steps=(
            Step(kind="command", content="!cleanup", persona="admin"),
            Step(kind="click", target_message=1, component_index=3,
                 persona="admin"),
        ),
        notes=(
            "the 🧹 Cleanup Policies open: the shipped btn_policies EDITED "
            "the hub message into the diagnostics panel "
            "(views/cleanup/policy_panel.py diagnostics_embed_from) — the "
            "red embed with the resolution-walk description, the empty "
            "'Configured policies' state, the ℹ️ Command Access tip and "
            "the 'Use “Set a policy” to add one.' footer over the "
            "persistent cleanup_policy:build/remove/refresh trio — a pure "
            "read (no cleanup_policies db_delta)"),
    ),
)
