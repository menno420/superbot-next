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
)
