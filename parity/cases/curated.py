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
            "pair + battle-win game-xp (creature.record_battle_result)"
        ),
    ),
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
)
