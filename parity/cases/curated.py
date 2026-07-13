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
    # ---------------------------------------------- mining WRITE-PARITY (WP-3)
    # Argful depth / world / workshop writes (descend / ascend / mineworld reseed
    # / repair / quickcraft) that DRIVE the mutation the imported bare-guard
    # sweeps never reached (D-0069 class exit). Same personas as WP-1/2: member =
    # 900000000000000102, admin (guild operator) = 900000000000000101, guild =
    # 700000000000000001. economy_balances keys user_id as BIGINT (no quotes);
    # the mining tables key user_id as TEXT (quoted). Each fixture_sql row is
    # seeded BEFORE the before-snapshot, so only the terminal's own audited write
    # lands in db_delta. Success copy is byte-identical to the oracle
    # (mining_cog.py descend/ascend/mineworld, services/mining_workflow.py
    # repair/quick_craft). These row-bearing captures retire the
    # depth.exemptions.mining guard-only-capture rows for mining_world (reseed)
    # and mining_gear_wear (repair's clear_gear_wear remove face — the ported
    # mine leg has NO wear tick, so the reseed/repair captures are the only write
    # ingress that touches these tables; the WP-4 workshop repair/quickcraft
    # terminals fold in here per the spec's "may fold into WP-3").
    GoldenCase(
        id="mining.descend_write",
        subsystem="mining",
        # Equip a torch (depth_access 1) so the geared descend clears the
        # gearless refusal, and pre-seed max_depth=1 so the descent is NOT
        # record-setting (record_depth's `WHERE max_depth < depth` fails → no
        # game-XP tail). The ported handler defers the XP/wear tail to the
        # D-0043 port (service.py:29), so a non-record descend is the face that
        # is byte-identical to the oracle mining_cog.py descend copy.
        fixture_sql=(
            "INSERT INTO mining_equipment (user_id, guild_id, slot, item_name) "
            "VALUES ('900000000000000102', 700000000000000001, 'light', "
            "'torch')",
            "INSERT INTO mining_player_state (user_id, guild_id, depth, "
            "max_depth) VALUES ('900000000000000102', 700000000000000001, 0, "
            "1)",
        ),
        steps=(
            Step(kind="command", content="!descend", persona="member"),
        ),
        notes=(
            "geared !descend (torch equipped, max_depth pre-seeded so it is not "
            "record-setting) drives mining.descend -> record_descend: set_depth "
            "0->1, no game-XP tail, and replies `<@u> descended to the Cavern "
            "band` — the depth-write face of mining_player_state (mining_cog.py "
            "descend copy verbatim)"),
    ),
    GoldenCase(
        id="mining.ascend_write",
        subsystem="mining",
        # Seed the player below the surface (depth 1, max_depth 1) so the climb
        # writes the surface band back.
        fixture_sql=(
            "INSERT INTO mining_player_state (user_id, guild_id, depth, "
            "max_depth) VALUES ('900000000000000102', 700000000000000001, 1, "
            "1)",
        ),
        steps=(
            Step(kind="command", content="!ascend", persona="member"),
        ),
        notes=(
            "!ascend (depth 1 seeded) drives mining.ascend -> record_ascend: "
            "set_depth 1->0 and replies `<@u> climbed up to the Surface band` — "
            "the ascend depth-write face of mining_player_state (mining_cog.py "
            "ascend copy verbatim)"),
    ),
    GoldenCase(
        id="mining.reseed_world_write",
        subsystem="mining",
        # No fixture: a fresh guild reads seed = guild_id; the admin persona is
        # the guild operator (manage_guild), so the argful reseed runs the
        # audited op and mints the first mining_world row.
        steps=(
            Step(kind="command", content="!mineworld 12345", persona="admin"),
        ),
        notes=(
            "admin (guild operator) !mineworld 12345 drives mining.reseed_world "
            "-> record_reseed_world: set_world_seed upserts the mining_world row "
            "(seed 12345) and replies with the shipped reseed copy — the first "
            "row-bearing reseed capture (retires the mining_world "
            "guard-only-capture exemption; mining_cog.py mineworld copy "
            "verbatim)"),
    ),
    GoldenCase(
        id="mining.repair_write",
        subsystem="mining",
        # Own the pickaxe (repair's ownership read), seed a worn wear row
        # (durability 30 of 60 max -> cost = ceil(ceil(25*0.5)*30/60) = 7), and
        # fund the balance (500 -> 493 after the debit). The wear row is a
        # seeded pre-req; repair's clear_gear_wear removes it -> the `removed`
        # face of mining_gear_wear.
        fixture_sql=(
            "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
            "quantity) VALUES "
            "('900000000000000102', 700000000000000001, 'pickaxe', 1)",
            "INSERT INTO mining_gear_wear (user_id, guild_id, item_name, "
            "durability) VALUES "
            "('900000000000000102', 700000000000000001, 'pickaxe', 30)",
            "INSERT INTO economy_balances (user_id, guild_id, coins) VALUES "
            "(900000000000000102, 700000000000000001, 500)",
        ),
        steps=(
            Step(kind="command", content="!repair pickaxe", persona="member"),
        ),
        notes=(
            "argful !repair (owned + worn + funded) drives mining.repair -> "
            "record_repair: debits the 7-coin cost via wager.debit_in_txn and "
            "clears the mining_gear_wear row in one advisory-fenced txn, and "
            "replies with the shipped repair copy (cost 7, balance 493) — the "
            "remove face of mining_gear_wear (retires its guard-only-capture "
            "exemption; mining_workflow repair copy verbatim)"),
    ),
    GoldenCase(
        id="mining.quick_craft_write",
        subsystem="mining",
        # Seed a broken item (last_broken_item = torch) + its recipe materials
        # (torch = {wood: 2}); the light slot is free so quick_craft auto-equips
        # the re-crafted torch.
        fixture_sql=(
            "INSERT INTO mining_player_state (user_id, guild_id, "
            "last_broken_item) VALUES "
            "('900000000000000102', 700000000000000001, 'torch')",
            "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
            "quantity) VALUES "
            "('900000000000000102', 700000000000000001, 'wood', 2)",
        ),
        steps=(
            Step(kind="command", content="!quickcraft", persona="member"),
        ),
        notes=(
            "!quickcraft (last_broken=torch seeded, wood materials owned) drives "
            "mining.quick_craft -> record_quick_craft: consumes the 2x wood, "
            "adds the crafted torch to mining_inventory, auto-equips it in the "
            "free light slot, and clears last_broken — all in one "
            "advisory-fenced txn — and replies with the shipped quick_craft "
            "auto-equip copy (mining_workflow quick_craft verbatim). The "
            "material-consume + craft + auto-equip write faces of "
            "mining_inventory / mining_equipment"),
    ),
    # ---------------------------------------------- mining WRITE-PARITY (WP-5)
    # The skill-spend PORT: the argful `!skill <branch>` point-spend was a live
    # D-0043 pending terminal (skill_route returned the BLOCKED successor copy,
    # NO write leg). WP-5 ports the oracle services/skill_service.py::allocate
    # onto the audited one-leg one-txn seam (mining.skill -> record_skill), flips
    # skill_route to run it (mention-prefixed on both faces, the shipped
    # ctx.send(f"{mention} {result.message}") lane), and drives it here. Same
    # personas as WP-1..3: member = 900000000000000102, guild =
    # 700000000000000001. player_skills keys user_id as BIGINT (no quotes); the
    # game_xp fixture (also BIGINT) seeds the level the available-points budget
    # derives from (min(level, SOFT_TOTAL_CAP=20) − total_spent). The fixture row
    # is seeded BEFORE the before-snapshot, so only the terminal's own write lands
    # in db_delta. Success/refusal copy is byte-identical to the oracle
    # (skill_service.allocate / mining_cog.py skill_cmd). The success capture is
    # row-bearing on player_skills → retires its guard-only-capture exemption.
    GoldenCase(
        id="mining.skill_write",
        subsystem="mining",
        # Seed 300 game XP → level_progress(300) = level 2, so the available
        # pool is min(2, 20) − 0 = 2 points; spending 1 into mining leaves 1.
        # (game_xp.updated_at defaults now(); day is nullable — migration 0036.)
        fixture_sql=(
            "INSERT INTO game_xp (user_id, guild_id, game, xp) VALUES "
            "(900000000000000102, 700000000000000001, 'mining', 300)",
        ),
        steps=(
            Step(kind="command", content="!skill mining", persona="member"),
        ),
        notes=(
            "argful !skill mining (game-XP fixture seeds level 2 → 2 available "
            "points) drives mining.skill -> record_skill (the ported "
            "skill_service.allocate): advisory-fenced (lock_skill_slot), it "
            "validates the branch + the per-branch cap + the available-points "
            "budget, then upserts the player_skills row (mining -> 1) in one txn, "
            "and replies `<@u> Spent **1** point into **mining** (now 1/10). "
            "**1** point left.` — the first row-bearing skill-spend capture "
            "(retires the player_skills guard-only-capture exemption; "
            "skill_service.allocate copy verbatim)"),
    ),
    GoldenCase(
        id="mining.skill_bad_branch",
        subsystem="mining",
        # No fixture: the bad-branch refusal is rejected inside the allocate leg
        # (the oracle validates the branch first) BEFORE the budget read/write,
        # so no player_skills row is touched — the audited seam records the
        # denial (a normalized audit_log row), never a skill mutation.
        steps=(
            Step(kind="command", content="!skill cooking", persona="member"),
        ),
        notes=(
            "argful !skill cooking (not a real branch) drives mining.skill -> "
            "record_skill and is refused inside the ported allocate before any "
            "player_skills write: replies `<@u> **cooking** isn't a skill "
            "branch — pick one of: mining, combat, fortune, crafting.` — the "
            "bad-branch error face (skill_service.allocate copy verbatim); the "
            "denial records a normalized audit_log row, NO player_skills "
            "db_delta"),
    ),
    # ---------------------------------------------- mining WRITE-PARITY (WP-6)
    # The structure-build PORT (the FINAL slice): the forge/home 🔥 Build panel
    # terminals were live D-0043 pendings (no write leg). WP-6 ports the oracle
    # services/mining_workflow.py::build_structure onto the audited one-leg
    # one-txn seam (mining.build -> record_build), flips the forge/home Build
    # terminals to live handlers (forge_build_route / home_build_route), and
    # drives the forge build here. The oracle `!build`/`!craft` COMMAND routes to
    # mining_workflow.craft (mining_inventory product, already covered), NOT to
    # build_structure — the mining_structures write is panel-button-driven per the
    # oracle (forge/home 🔥 Build), so the golden drives the 🔥 Build click on the
    # session forge panel (the stash_all component_index precedent). Same personas
    # as WP-1..5: member = 900000000000000102, guild = 700000000000000001.
    # economy_balances keys user_id as BIGINT (no quotes); mining_inventory keys
    # user_id as TEXT (quoted). Each fixture row is seeded BEFORE the
    # before-snapshot, so only the build's own audited write lands in db_delta.
    # Success copy is byte-identical to the oracle (build_structure). The success
    # capture is row-bearing on mining_structures -> retires its
    # guard-only-capture exemption (the LAST mining exemption — lane complete).
    GoldenCase(
        id="mining.build_forge_write",
        subsystem="mining",
        # Fund the balance (3500 -> 500 after the 3000 debit) and own the forge-I
        # materials (iron 30 -> 5, stone 20 -> 5 after the 25/15 consume). The
        # level read + affordability guards are pure reads gated out before the
        # leg; only a funded+stocked build runs the audited debit+consume+bump.
        fixture_sql=(
            "INSERT INTO economy_balances (user_id, guild_id, coins) VALUES "
            "(900000000000000102, 700000000000000001, 3500)",
            "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
            "quantity) VALUES "
            "('900000000000000102', 700000000000000001, 'iron', 30), "
            "('900000000000000102', 700000000000000001, 'stone', 20)",
        ),
        steps=(
            # !forge mints the 🔥 Forge session panel; the 🔥 Build button is
            # flattened component index 0 (build 0, workshop 1, help 2, games 3 —
            # goldens/mining/sweep_forge pins the order). The session-minted
            # custom_id normalizes to <cid:N>; component_index reconstructs it.
            Step(kind="command", content="!forge", persona="member"),
            Step(kind="click", target_message=1, component_index=0,
                 persona="member"),
        ),
        notes=(
            "!forge then the 🔥 Build click (funded 3500 🪙 + iron 30 / stone 20 "
            "fixture) drives mining.build -> record_build (the ported "
            "mining_workflow.build_structure): advisory-fenced "
            "(lock_structure_slot), it debits the 3000 🪙 cost via "
            "wager.debit_in_txn, consumes 25× iron + 15× stone, and raises the "
            "mining_structures forge level 0->1 in one txn, and replies "
            "`<@u> Forge built to **Forge I** for 25× iron, 15× stone + 3000 🪙. "
            "Now crafts **gold-tier** gear. Balance: **500** 🪙.` — the first "
            "row-bearing structure-build capture (retires the LAST mining "
            "guard-only-capture exemption, mining_structures; build_structure "
            "copy verbatim)"),
    ),
    GoldenCase(
        id="mining.build_forge_insufficient",
        subsystem="mining",
        # No fixture: a fresh player has no materials, so the 🔥 Build click hits
        # the short-on-materials refusal (a PURE READ in forge_build_route,
        # BEFORE the op runs) — no coin ledger / mining_structures write.
        steps=(
            Step(kind="command", content="!forge", persona="member"),
            Step(kind="click", target_message=1, component_index=0,
                 persona="member"),
        ),
        notes=(
            "!forge then the 🔥 Build click with an empty pack drives "
            "forge_build_route, which refuses as a PURE READ before the "
            "mining.build op runs: replies `<@u> Building the Forge needs 25× "
            "iron, 15× stone plus 3000 🪙 — you're short on materials.` — the "
            "short-on-materials error face (build_structure copy verbatim); NO "
            "mining_structures db_delta (the failed click writes no audit/ledger "
            "row, exactly as the oracle's pre-txn material check returns)"),
    ),
    # ---------------------------------------------- mining WRITE-PARITY (WP-7)
    # The residual non-energy pending legs the lane left honest-pending. WP-7
    # ports two of them onto the audited one-leg one-txn seam and drives them
    # here; title-equip is DROPPED (kept honest-pending — no command form,
    # select-driven, and the target titles panel renders no earned-title Select).
    # (a) craft: the argful !craft <item> / !build <item> was a live D-0043
    # pending terminal (no leg). WP-7 ports the oracle
    # services/mining_workflow.py::craft onto mining.craft -> record_craft and
    # flips build_route's argful branch to run it. (b) respec: the skills-panel
    # ♻ Respec button was a live D-0043 pending. WP-7 ports the oracle
    # services/skill_service.py::respec onto mining.respec -> record_respec and
    # flips the sk_respec button to a live route driven by the session-panel
    # click (the WP-6 forge 🔥 Build component_index precedent). Same personas as
    # WP-1..6: member = 900000000000000102, guild = 700000000000000001.
    # mining_inventory keys user_id as TEXT (quoted); player_skills / game_xp /
    # economy_balances key user_id as BIGINT (no quotes). Each fixture row is
    # seeded BEFORE the before-snapshot, so only the terminal's own write lands in
    # db_delta. Copy is byte-identical to the oracle (mining_workflow.craft /
    # skill_service.respec). Neither table is newly covered — mining_inventory
    # (mine/sell), player_skills (WP-5) and economy_balances (WP-2..6) are already
    # golden-covered — so WP-7 retires NO exemption; these captures freeze the
    # ported handlers as their own contract.
    GoldenCase(
        id="mining.craft_write",
        subsystem="mining",
        # Own 5× wood; crafting a torch (recipe {wood: 2}, forge-free) consumes
        # 2 wood (-> 3) and adds 1 torch. The recipe resolve + forge gate +
        # material check are the leg's own reads; only a stocked craft runs the
        # consume + product-add + crafting game-XP award in one advisory-fenced
        # (lock_workshop_slot) txn.
        fixture_sql=(
            "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
            "quantity) VALUES "
            "('900000000000000102', 700000000000000001, 'wood', 5)",
        ),
        steps=(
            Step(kind="command", content="!craft torch", persona="member"),
        ),
        notes=(
            "argful !craft torch (5× wood fixture) drives build_route -> "
            "mining.craft -> record_craft (the ported mining_workflow.craft): "
            "advisory-fenced (lock_workshop_slot), it resolves the recipe "
            "({wood: 2}), passes the forge gate (torch is forge-free) and the "
            "material check, consumes 2× wood (5 -> 3), adds 1× torch to "
            "mining_inventory, and awards crafting game-XP — all in one txn — "
            "then replies `<@u> Crafted **torch**!` (mining_workflow.craft copy "
            "verbatim; mining_inventory already covered, so no exemption is "
            "retired — the capture freezes the ported craft handler)"),
    ),
    GoldenCase(
        id="mining.craft_no_recipe",
        subsystem="mining",
        # No fixture: `dragon` is neither a recipe nor a GEAR_SHOP item, so the
        # no-recipe refusal is raised inside record_craft BEFORE any DB read (the
        # oracle _resolve_recipe ordering) — no mining_inventory write; the
        # audited seam records the denial (a normalized audit_log row).
        steps=(
            Step(kind="command", content="!craft dragon", persona="member"),
        ),
        notes=(
            "argful !craft dragon (not a recipe, not a shop item) drives "
            "mining.craft -> record_craft and is refused inside the ported craft "
            "before any inventory write: replies `<@u> No recipe for **dragon**. "
            "Use `!buildlist` to see available recipes.` — the no-recipe error "
            "face (mining_workflow.craft copy verbatim; the buildlist hint, since "
            "dragon has no GEAR_SHOP buy price); the denial records a normalized "
            "audit_log row, NO mining_inventory db_delta"),
    ),
    GoldenCase(
        id="mining.respec_write",
        subsystem="mining",
        # Allocate 2 points into mining, seed 300 game XP (level_progress(300) =
        # level 2 -> respec_cost = 200 + 50*2 = 300 🪙), fund 500 🪙 (-> 200 after
        # the debit). The ♻ Respec click runs mining.respec -> record_respec:
        # debit 300 🪙 via wager.debit_in_txn, then zero the mining branch row —
        # both in one advisory-fenced (lock_skill_slot) txn.
        fixture_sql=(
            "INSERT INTO player_skills (user_id, guild_id, branch, points) "
            "VALUES (900000000000000102, 700000000000000001, 'mining', 2)",
            "INSERT INTO game_xp (user_id, guild_id, game, xp) VALUES "
            "(900000000000000102, 700000000000000001, 'mining', 300)",
            "INSERT INTO economy_balances (user_id, guild_id, coins) VALUES "
            "(900000000000000102, 700000000000000001, 500)",
        ),
        steps=(
            # !skills mints the 🌳 Skill Tree session panel; the ♻ Respec button
            # is flattened component index 4 (mining 0, combat 1, fortune 2,
            # crafting 3, respec 4, titles 5, hub 6 — goldens/mining/sweep_skills
            # pins the order). The session-minted custom_id normalizes to
            # <cid:N>; component_index reconstructs it (the WP-6 forge precedent).
            Step(kind="command", content="!skills", persona="member"),
            Step(kind="click", target_message=1, component_index=4,
                 persona="member"),
        ),
        notes=(
            "!skills then the ♻ Respec click (mining=2 allocation + 300 game-XP "
            "level-2 fixture + funded 500 🪙) drives mining.respec -> "
            "record_respec (the ported skill_service.respec): advisory-fenced "
            "(lock_skill_slot), it debits the level-scaled 300 🪙 respec fee via "
            "wager.debit_in_txn and zeroes the player_skills mining branch (2 -> "
            "0) in one txn, then replies `<@u> Respec complete — all points "
            "refunded for **300** 🪙. Balance: **200** 🪙.` (skill_service.respec "
            "copy verbatim; player_skills already covered by WP-5, so no "
            "exemption is retired — the capture freezes the ported respec "
            "handler)"),
    ),
    GoldenCase(
        id="mining.respec_insufficient",
        subsystem="mining",
        # Allocate 2 points but seed NO coins (and no game XP -> level 0 ->
        # respec_cost = 200 🪙). The ♻ Respec click runs record_respec: the
        # alloc read passes (non-empty), but wager.debit_in_txn raises
        # InsufficientFundsError, so the whole txn rolls back — no coin ledger /
        # player_skills write.
        fixture_sql=(
            "INSERT INTO player_skills (user_id, guild_id, branch, points) "
            "VALUES (900000000000000102, 700000000000000001, 'mining', 2)",
        ),
        steps=(
            Step(kind="command", content="!skills", persona="member"),
            Step(kind="click", target_message=1, component_index=4,
                 persona="member"),
        ),
        notes=(
            "!skills then the ♻ Respec click (mining=2 allocation, NO coins, "
            "level 0 -> 200 🪙 fee) drives mining.respec -> record_respec and is "
            "refused inside the leg when wager.debit_in_txn raises "
            "InsufficientFundsError: replies `<@u> Respec costs **200** 🪙 — you "
            "only have **0** 🪙.` — the insufficient-funds error face "
            "(skill_service.respec copy verbatim); the txn rolls back so there is "
            "NO player_skills / economy_balances db_delta (only the normalized "
            "denial audit_log row)"),
    ),
)
