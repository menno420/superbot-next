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
    # ----------------------------------------- settings group edit page (S0)
    GoldenCase(
        id="settings.group_edit_open",
        subsystem="settings",
        # option A: the hub group select opens the ported per-group scalar
        # EDIT page for a NON-HUB group (role). The click defers + posts the
        # group_edit followup — the read embed (resolved scalar values +
        # tier/key header), the windowed Edit / Reset selects and the
        # Open-Panel / Back-to-Hub nav are the golden.
        steps=(
            Step(kind="command", content="!settings", persona="admin"),
            Step(kind="click", target_message=1,
                 custom_id="settings_hub.subsystem_select",
                 component_type=3, values=("role",), persona="admin"),
        ),
        notes=(
            "settings epic S0: the non-hub group select (role) opens "
            "settings.group_edit (option A) — the read embed + windowed "
            "edit/reset selects + nav are the golden"
        ),
    ),
    GoldenCase(
        id="settings.group_edit_bool_write",
        subsystem="settings",
        # the S1 bool toggle: open the role edit page, then pick the bool
        # `time_roles_stack` in the Edit select — it flips on through the K7
        # settings.set_scalar lane (guild `settings` row write + the audited
        # spine), the page refreshes in place, and the ephemeral followup
        # confirms. The `settings` db_delta + the refreshed embed are pinned.
        steps=(
            Step(kind="command", content="!settings", persona="admin"),
            Step(kind="click", target_message=1,
                 custom_id="settings_hub.subsystem_select",
                 component_type=3, values=("role",), persona="admin"),
            Step(kind="click", target_message=2, component_index=0,
                 component_type=3, values=("time_roles_stack",),
                 persona="admin"),
        ),
        notes=(
            "settings epic S0 / S1 bool toggle: picking the bool "
            "time_roles_stack flips it on through settings.set_scalar "
            "(the guild settings write + in-place refresh + confirm)"
        ),
    ),
    GoldenCase(
        id="settings.group_edit_enum_write",
        subsystem="settings",
        # settings epic S2 / enum select: open the moderation edit page, pick
        # the enum `warn_escalation_action` in the Edit select — it opens the
        # windowed enum picker (settings.group_edit_enum) of the declared
        # allowed_values; picking `kick` commits the chosen member through the
        # K7 settings.set_scalar lane (the guild `settings` row write + the
        # audited spine), the picker refreshes in place, and the ephemeral
        # followup confirms. The `settings` db_delta + the enum picker's
        # render are pinned.
        steps=(
            Step(kind="command", content="!settings", persona="admin"),
            Step(kind="click", target_message=1,
                 custom_id="settings_hub.subsystem_select",
                 component_type=3, values=("moderation",), persona="admin"),
            Step(kind="click", target_message=2, component_index=0,
                 component_type=3, values=("warn_escalation_action",),
                 persona="admin"),
            Step(kind="click", target_message=3, component_index=0,
                 component_type=3, values=("kick",), persona="admin"),
        ),
        notes=(
            "settings epic S2 enum select: picking the enum "
            "warn_escalation_action opens the windowed choice picker, and "
            "picking `kick` commits it through settings.set_scalar "
            "(the guild settings write + in-place refresh + confirm)"
        ),
    ),
    GoldenCase(
        id="settings.group_edit_number_write",
        subsystem="settings",
        # settings epic S3 / number modal: open the moderation edit page, pick
        # the int `warn_threshold` in the Edit select — it opens the
        # number-modal widget (settings.group_edit_number); tapping its
        # "Enter a number…" button ISSUES the G-10 numeric modal (stashing the
        # (group, setting) session args), and submitting `5` coerces +
        # range-validates then commits it through the K7 settings.set_scalar
        # lane (the guild `settings` row write + the audited spine), the widget
        # refreshes in place, and the ephemeral followup confirms. The
        # `settings` db_delta + the number widget's render are pinned.
        steps=(
            Step(kind="command", content="!settings", persona="admin"),
            Step(kind="click", target_message=1,
                 custom_id="settings_hub.subsystem_select",
                 component_type=3, values=("moderation",), persona="admin"),
            Step(kind="click", target_message=2, component_index=0,
                 component_type=3, values=("warn_threshold",),
                 persona="admin"),
            # tap the "Enter a number…" button — issues the modal + stashes
            # the (group, setting) args for the submit re-entry.
            Step(kind="click", target_message=3, component_index=0,
                 component_type=2, persona="admin"),
            # submit the numeric modal: `warn_threshold` = 5 (in bounds 1-50).
            Step(kind="modal", target_message=3,
                 custom_id="settings.group_edit_number_form",
                 fields=(("number_value", "5"),), persona="admin"),
        ),
        notes=(
            "settings epic S3 number modal: picking the int warn_threshold "
            "opens the number-modal widget; tapping Enter a number… issues "
            "the numeric modal and submitting `5` commits it through "
            "settings.set_scalar (the guild settings write + in-place refresh "
            "+ confirm)"
        ),
    ),
    GoldenCase(
        id="settings.group_edit_text_write",
        subsystem="settings",
        # settings epic S4 / free-text modal: open the karma edit page, pick the
        # free-text str `reaction_emoji` in the Edit select — it opens the
        # free-text-modal widget (settings.group_edit_text); tapping its
        # "Enter text…" button ISSUES the G-10 free-text modal (stashing the
        # (group, setting) session args), and submitting `⭐` validates
        # (non-empty + the declared 64-char max-length) then commits it through
        # the K7 settings.set_scalar lane (the guild `settings` row write + the
        # audited spine), the widget refreshes in place, and the ephemeral
        # followup confirms. The `settings` db_delta + the text widget's render
        # are pinned.
        steps=(
            Step(kind="command", content="!settings", persona="admin"),
            Step(kind="click", target_message=1,
                 custom_id="settings_hub.subsystem_select",
                 component_type=3, values=("karma",), persona="admin"),
            Step(kind="click", target_message=2, component_index=0,
                 component_type=3, values=("reaction_emoji",),
                 persona="admin"),
            # tap the "Enter text…" button — issues the modal + stashes the
            # (group, setting) args for the submit re-entry.
            Step(kind="click", target_message=3, component_index=0,
                 component_type=2, persona="admin"),
            # submit the free-text modal: `reaction_emoji` = ⭐ (non-empty, well
            # under the 64-char bound).
            Step(kind="modal", target_message=3,
                 custom_id="settings.group_edit_text_form",
                 fields=(("text_value", "⭐"),), persona="admin"),
        ),
        notes=(
            "settings epic S4 free-text modal: picking the free-text str "
            "reaction_emoji opens the text-modal widget; tapping Enter text… "
            "issues the free-text modal and submitting `⭐` commits it through "
            "settings.set_scalar (the guild settings write + in-place refresh "
            "+ confirm)"
        ),
    ),
    # -------------------------------------------------------------- help
    GoldenCase(
        id="help.panel_open",
        subsystem="help",
        steps=(Step(kind="command", content="!help", persona="member"),),
        notes="the help panel projection + nav components",
    ),
    # ------------------------------------------- help Home-message builder (Q-0059)
    GoldenCase(
        id="help.home_message_save",
        subsystem="help",
        # the shipped Q-0059 stage → mandatory-preview → save chain
        # (disbot/views/help/home_builder.py). Entry is the server-management
        # hub's ✏️ Help editor button (help.editor_home) → 🏠 Home message
        # (help.editor_home_message), then the title modal, the mandatory
        # preview (Save is disabled until previewed), and 💾 Save — one
        # audited set_home_message write to help_overlay (home_* columns).
        steps=(
            Step(kind="command", content="!servermanagement", persona="admin"),
            Step(kind="click", target_message=1,
                 custom_id="server_management:help_editor", persona="admin"),
            Step(kind="click", target_message=1,
                 custom_id="help.editor_home.eh_home_msg", persona="admin"),
            Step(kind="modal", target_message=1,
                 custom_id="help.home_title_form",
                 fields=(("title", "Welcome to our server!"),),
                 persona="admin"),
            Step(kind="click", target_message=1,
                 custom_id="help.editor_home_message.hb_preview",
                 persona="admin"),
            Step(kind="click", target_message=1,
                 custom_id="help.editor_home_message.hb_save",
                 persona="admin"),
        ),
        notes=(
            "the Q-0059 Home-message builder: stage a custom title, the "
            "mandatory preview unlocks Save, then Save writes the home_* "
            "overlay row (builder embed bytes + the audited DB write)"
        ),
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
    # title-equip write slice: the 🏆 Titles panel's earned-title select is
    # the ONLY equip ingress (no command form — oracle mining_cog.titles_cmd
    # opens the panel only; title_service.equip is called solely from
    # views/mining/titles_panel.py::MiningTitlesView @ bbc524e). Earned
    # titles are DERIVED (max_depth=1 ⇒ 🪨 the Spelunker), so the fixture
    # seeds only progression — the equip write is the case's own db_delta
    # (mining_player_state.equipped_title, a table already covered by the
    # energy-slice ration golden; no exemption/ratchet change).
    GoldenCase(
        id="mining.title_equip_write",
        subsystem="mining",
        # reached-the-Cavern progression (read pre-req, seeded before the
        # snapshot): earns exactly one title, so the panel renders the
        # 1+1-option select ((none) + 🪨 the Spelunker).
        fixture_sql=(
            "INSERT INTO mining_player_state (user_id, guild_id, "
            "max_depth) VALUES "
            "('900000000000000102', 700000000000000001, 1)",
        ),
        steps=(
            Step(kind="command", content="!titles", persona="member"),
            # the earned-title select (component 0, wire type 3, session
            # <cid:N> id — resolved by index, the blackjack precedent):
            # pick the Spelunker.
            Step(kind="click", target_message=1, component_index=0,
                 component_type=3, persona="member",
                 values=("spelunker",)),
        ),
        notes=(
            "the titles-panel select drives mining.titles_pick → the "
            "audited mining.equip_title op (record_equip_title: live "
            "earn-check + the one equipped_title upsert), then the panel "
            "re-renders in place with `✅ Title set to 🪨 the Spelunker.` "
            "and the SUCCESS green frame — the first equipped_title "
            "write-bearing golden (title_service.equip verbatim)"),
    ),
    GoldenCase(
        id="mining.title_equip_unearned_refusal",
        subsystem="mining",
        # same one-earned-title progression; the click FORGES an unearned
        # value (legend needs game level 25) — the leg's earn-check must
        # refuse row-less with the oracle copy.
        fixture_sql=(
            "INSERT INTO mining_player_state (user_id, guild_id, "
            "max_depth) VALUES "
            "('900000000000000102', 700000000000000001, 1)",
        ),
        steps=(
            Step(kind="command", content="!titles", persona="member"),
            Step(kind="click", target_message=1, component_index=0,
                 component_type=3, persona="member",
                 values=("legend",)),
        ),
        notes=(
            "a forged un-earned pick refuses through the leg's live "
            "earn-check (txn-aborting ValidatorError — NO equipped_title "
            "write): the panel re-renders with `❌ You haven't earned "
            "**the Legend** yet — Reach game level 25.` and the ERROR red "
            "frame (title_service.equip's is_earned refusal verbatim)"),
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
    # backlog B2 — the 🌳 Skill Tree panel's per-branch spend button (⛏️ Mining):
    # the D-0043 pending terminal (skill_spend_pending) flips to the live
    # mining.skill_spend_route -> mining.skill -> record_skill (the ported
    # skill_service.allocate with the panel's default n=1). Drives the SAME op the
    # command-lane mining.skill_write pins, but from the session-panel button, so
    # this freezes the ported button's wire bytes (interaction defer + the
    # RESULT_CARD followup — the mining.respec_write / stash_all_write click
    # precedent). Seed is byte-identical to mining.skill_write: 300 game XP ->
    # level 2 -> min(2,20)-0 = 2 available points; the click spends 1 into mining.
    GoldenCase(
        id="mining.skill_spend_write",
        subsystem="mining",
        # !skills mints the 🌳 Skill Tree session panel; the ⛏️ Mining branch
        # button is flattened component index 0 (mining 0, combat 1, fortune 2,
        # crafting 3, respec 4, titles 5, hub 6 — the mining.respec_write order).
        # The session-minted custom_id normalizes to <cid:N>; component_index
        # reconstructs it (the respec_write / forge-build precedent).
        fixture_sql=(
            "INSERT INTO game_xp (user_id, guild_id, game, xp) VALUES "
            "(900000000000000102, 700000000000000001, 'mining', 300)",
        ),
        steps=(
            Step(kind="command", content="!skills", persona="member"),
            Step(kind="click", target_message=1, component_index=0,
                 persona="member"),
        ),
        notes=(
            "!skills then the ⛏️ Mining branch click (300 game-XP level-2 fixture "
            "→ 2 available points) drives mining.skill_spend_route → mining.skill "
            "→ record_skill (the ported skill_service.allocate with the panel's "
            "default n=1): advisory-fenced (lock_skill_slot), it validates the "
            "branch + the per-branch cap + the available-points budget, then "
            "upserts the player_skills row (mining → 1) in one txn, then replies "
            "`<@u> Spent **1** point into **mining** (now 1/10). **1** point "
            "left.` as a RESULT_CARD (the accepted sb divergence from the oracle "
            "MiningSkillsView._spend in-place panel re-render — the "
            "mining.respec_write button-click precedent; skill_service.allocate "
            "copy verbatim). Same op the command-lane mining.skill_write pins, "
            "driven from the session button — this freezes the ported skill-spend "
            "button wire bytes"),
    ),
    # backlog B3 — the 🔧 Workshop panel's gear-craft SELECT: the D-0043 pending
    # terminal (workshop_craft_pending) flips to the live mining.workshop_craft_pick
    # -> mining.craft -> record_craft (the ported mining_workflow.craft with the
    # picked recipe). Drives the SAME op the command-lane mining.craft_write pins,
    # but from the session-panel select — a SELECT (wire type 3, values-bearing),
    # so unlike the skill-spend BUTTON this re-renders the panel IN PLACE with the
    # oracle's ✅/❌ note + SUCCESS/ERROR frame (the mining.title_equip_write select
    # precedent — the FAITHFUL reproduction of the oracle _CraftSelect._rerender,
    # NOT the RESULT_CARD divergence). This freezes the ported select's in-place
    # re-render wire bytes. mining_inventory is already covered (mine/sell/craft),
    # so NO exemption retires. Persona member = 900000000000000102, guild =
    # 700000000000000001; mining_inventory keys user_id as TEXT (quoted).
    GoldenCase(
        id="mining.workshop_craft_write",
        subsystem="mining",
        # Own exactly the bronze-boots recipe materials (bronze 2 -> 0 after the
        # 2× consume, + 1 bronze boots). bronze boots is forge-free gear
        # ({bronze: 2}), so the click crafts cleanly with no structures read.
        fixture_sql=(
            "INSERT INTO mining_inventory (user_id, guild_id, item_name, "
            "quantity) VALUES "
            "('900000000000000102', 700000000000000001, 'bronze', 2)",
        ),
        steps=(
            # !workshop mints the 🔧 Workshop session panel; the gear-craft
            # select is flattened component index 0 (craft 0, quickcraft 1,
            # back 2, help 3, games 4 — goldens/mining/sweep_workshop pins the
            # order). The session-minted custom_id normalizes to <cid:N>;
            # component_index reconstructs it (the title_equip select precedent).
            Step(kind="command", content="!workshop", persona="member"),
            Step(kind="click", target_message=1, component_index=0,
                 component_type=3, persona="member",
                 values=("bronze boots",)),
        ),
        notes=(
            "!workshop then the gear-craft select pick (bronze 2 fixture) drives "
            "mining.workshop_craft_pick -> mining.craft -> record_craft (the "
            "ported mining_workflow.craft): advisory-fenced (lock_workshop_slot), "
            "it consumes 2× bronze, adds +1 bronze boots to mining_inventory, and "
            "awards crafting game-XP in one txn, then the panel re-renders IN "
            "PLACE with `✅ Crafted **bronze boots**!` and the SUCCESS green frame "
            "(the oracle _CraftSelect._rerender, mining_workflow.craft copy "
            "verbatim). Same op the command-lane mining.craft_write pins, driven "
            "from the session select — this freezes the ported workshop-craft "
            "select wire bytes"),
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
    # ------------------------------------------- mining ENERGY (slice 3)
    # The fastmine dig energy-spend (docs/scoping/energy-system-scope.md
    # slice 3, Option A; oracle copy: disbot/services/mining_workflow.py
    # dig() @ 87bbe1d — the energy bracket grafted onto the fastmine
    # lane). The spend itself is pinned by the RE-MINTED sweep_fastmine
    # (fresh player settles full → digs → energy 60→59 joins its
    # db_delta); this case pins the out-of-energy REFUSAL, a route-level
    # pure read replying PLAIN (the slice-2 ValidatorError-envelope
    # trap: an in-leg raise would wrap as the kernel envelope).
    GoldenCase(
        id="mining.fastmine_out_of_energy_refusal",
        subsystem="mining",
        # An EMPTY bar that stays empty: energy=0 stamped 5s before the
        # case's logical clock (the harness pins time.time to the
        # case-id-derived logical timeline, so the stamp is a pure
        # function of the case id — computed by probe capture). settle()
        # gains 0 units over 5s (<REGEN_SECONDS), the gate refuses, and
        # seconds_until lands the hint at exactly ~5s. Any harness
        # clock-pacing change re-lands here loudly (the xp.last_xp
        # absolute-stamp class).
        fixture_sql=(
            "INSERT INTO mining_player_state (user_id, guild_id, energy, "
            "energy_updated_at) VALUES "
            "('900000000000000102', 700000000000000001, 0, 1877604670)",
        ),
        steps=(
            Step(kind="command", content="!fastmine", persona="member"),
        ),
        notes=(
            "!fastmine on an empty bar refuses PLAIN with the oracle dig() "
            "hint (`⚡ You're out of energy — rest a moment (~{wait}s until "
            "your next dig) or eat a **ration** / **energy drink** (`!use "
            "ration`).`) — a pre-txn pure read: no loot, no energy write, "
            "no game XP, no mining db_delta"),
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
            # in-window since the slice-2 late-enforcement flip: the
            # seed-42 storm bite lands at ~4.28 s, window 2.5 — 5.0 s
            # sits inside [4.28 … 6.78] (the pre-flip default 30 s click
            # would now be too-slow).
            Step(kind="click", target_message=1, component_index=0,
                 persona="member", advance_s=5.0),
        ),
        notes=(
            "fresh player, shore profile — every knob reads exactly neutral "
            "(no-row venue → shore, rod tier 0, no bait, unbuilt structures, "
            "fresh gear): `!fish` spends 2 energy off the fresh full bar "
            "(fishing_energy row 58) and the in-window Reel click drives "
            "the audited fishing.cast leg — the FIRST row-bearing "
            "fishing_catch_log capture (dex row + the caught fish in "
            "mining_inventory + the fishing game-XP award) with the oracle "
            "result-card copy "
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
            # in-window (slice-2 late enforcement): the seed-42 storm
            # deepwater bite at the loaded compound lands at ~7.09 s,
            # window 2.8 (deep 2.0 + Silver rod 0.8) — 8.0 s sits inside
            # [7.09 … 9.89].
            Step(kind="click", target_message=1, component_index=0,
                 persona="member", advance_s=8.0),
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
            # in-window (slice-2 late enforcement): the seed-42 storm
            # bite on the worm loadout lands at ~4.28 s, window 2.5 —
            # 5.0 s sits inside [4.28 … 6.78].
            Step(kind="click", target_message=1, component_index=0,
                 persona="member", advance_s=5.0),
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
    # --------------------------------------- fishing Cast-again continuation
    # The first golden that clicks THROUGH a cast terminal: the committed
    # catch opens the fishing.cast_result card (the oracle _FishingDoneView
    # @bbc524e — green 🎣 Cast again, never pre-disabled) and clicking it
    # re-runs the FULL cast path with fresh randomness — a second energy
    # spend, a second catch roll on the continuing seed-42 stream, and a
    # brand-new waiting-for-a-bite panel.
    GoldenCase(
        id="fishing.cast_again_continuation",
        subsystem="fishing",
        steps=(
            Step(kind="command", content="!fish", persona="member"),
            # in-window reel (the cast_reel_write timing: seed-42 storm
            # bite ~4.28 s, window 2.5 — 5.0 s sits inside
            # [4.28 … 6.78]) — the catch commits and the result card
            # (message 2) opens with the Cast again button.
            Step(kind="click", target_message=1, component_index=0,
                 persona="member", advance_s=5.0),
            # …the continuation: Cast again on the result card re-runs
            # cast_open — the second cast spends 2 more energy (58→56)
            # and opens a fresh cast panel (message 3).
            Step(kind="click", target_message=2, component_index=0,
                 persona="member", advance_s=2.0),
        ),
        notes=(
            "the Cast-again continuation (review-doc gap 3): the committed "
            "catch answers the fishing.cast_result card — the oracle "
            "result copy split title/description onto a SUCCESS-green "
            "embed over the single 🎣 Cast again button "
            "(_FishingDoneView @bbc524e) — and clicking it re-runs the "
            "full cast path: db_delta pins the first catch's commit "
            "(catch-log row + fish grant + game XP) AND the second "
            "cast's energy spend (60→58→56), with a brand-new waiting "
            "panel as the final message"),
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
    # -------------------------------------- rps quickplay bet settle (row 72)
    # Curation backlog row 72 (docs/review/curation-report-2026-07-13.md:1177
    # — "the coin-bet click path has no golden; sweep_rps.json is the bare
    # open"): the FIRST golden that ever clicks a quickplay move button and
    # the first row-bearing rps_players capture (retires that time-driven
    # exemption's ground). The bot's move draws from the module-private
    # solo-play RNG (sb/domain/rps/ops._rng), RE-ARMED at every case head by
    # the runner (random.Random(case.seed) — the fishing cast-RNG posture),
    # so the seed-42 first draw is scissors and the Rock click wins
    # deterministically. member persona = 900000000000000102, guild =
    # 700000000000000001; economy_balances keys user_id as BIGINT.
    GoldenCase(
        id="rps_tournament.quickplay_bet_settle_write",
        subsystem="rps_tournament",
        # fund the bet: `!rps 10` balance-gates BEFORE the view opens
        # (rps.play's shipped pre-check refusal face).
        fixture_sql=(
            "INSERT INTO economy_balances (user_id, guild_id, coins) VALUES "
            "(900000000000000102, 700000000000000001, 40)",
        ),
        steps=(
            Step(kind="command", content="!rps 10", persona="member"),
            Step(kind="click", target_message=1, component_index=0,
                 persona="member"),
        ),
        notes=(
            "the coin-bet quickplay settle (item 2 — solo result view "
            "edit-in-place): `!rps 10` opens the shipped solo-play view with "
            "the bet line (`Bet: **10** 🪙`) and the invoker's 🪨 Rock click "
            "drives the audited rps.solo_play op — seed-42's armed bot draw "
            "is scissors, so the win branch credits the bet (`🎉 You win! "
            "+10 🪙`, reason rps:solo_win, balance 40→50) and the shipped "
            "update_player_stats site writes the FIRST row-bearing "
            "rps_players capture (1 win, display name captured at game "
            "time). The click EDITS the picker message IN PLACE into the "
            "result embed (interaction_response type 6 + edit_followup, move "
            "buttons disabled) via refresh_session_view — the shipped "
            "views/rps/solo_play._RpsView edit loop "
            "(sb/domain/rps/handlers.py::rps.solo_click, the blackjack solo "
            "table_click precedent)"),
    ),
    # ------------------------------------------------- farm money paths
    # The curation report's farm-goldens backlog line (docs/review/
    # curation-report-2026-07-13.md § "(c) Backlog"): click-golden batch for
    # the three K7 money lanes behind the hub's run-minted buttons —
    # the first row-bearing chicken_farm captures (the parity.yml
    # `table:chicken_farm` exemption's own promised retirement: "the first
    # row-bearing golden lands with a button-driving capture"). Copy is the
    # shipped disbot/views/farm/menu.py + farm_workflow semantics verbatim
    # (sb/domain/farm/ops.py module contract). member persona =
    # 900000000000000102, guild = 700000000000000001; chicken_farm and
    # economy_balances key user_id as BIGINT. Hub flatten order (pinned by
    # goldens/farm/sweep_farm.json): 0=Collect · 1=Shop · 2=Refresh ·
    # 3=nav:help · 4=nav:hub:games; the Shop click opens the shop panel as
    # a FRESH send (message 2), whose order is 0=Buy hen · 1=Upgrade coop ·
    # 2=Back · 3/4=nav.
    GoldenCase(
        id="farm.collect_write",
        subsystem="farm",
        # a FULL coop (eggs == coop_capacity(0) == 20): settle
        # short-circuits at the cap regardless of elapsed time, so the
        # pinned bytes are clock-independent by construction (the hub
        # renders the `**full!**` fill line, no duration math) —
        # eggs_updated_at 0 is the uninitialized epoch the store defaults.
        fixture_sql=(
            "INSERT INTO chicken_farm (user_id, guild_id, chickens, eggs, "
            "eggs_updated_at, coop_level) VALUES "
            "(900000000000000102, 700000000000000001, 1, 20, 0, 0)",
        ),
        steps=(
            Step(kind="command", content="!farm", persona="member"),
            Step(kind="click", target_message=1, component_index=0,
                 persona="member"),
        ),
        notes=(
            "the Collect payout: `!farm` renders the hub at a full coop "
            "(`🥚 20/20`, `Worth **40** 🪙 · **full!**`) and the 🥚 Collect "
            "click drives the audited farm.collect op — ONE txn credits "
            "collect_value(20)=40 🪙 (reason farm:collect), zeroes the "
            "eggs on the chicken_farm row and awards the farm game-XP "
            "(`🥚 Collected **20** egg(s) for **40** 🪙! Balance: **40** "
            "🪙.` — the shipped farm_workflow collect copy verbatim); the "
            "FIRST row-bearing chicken_farm capture"),
    ),
    GoldenCase(
        id="farm.buy_hen_write",
        subsystem="farm",
        # a funded fresh farmer: no chicken_farm row (starter defaults —
        # 1 hen, 0 eggs) + 100 🪙; chicken_price(1) = 40.
        fixture_sql=(
            "INSERT INTO economy_balances (user_id, guild_id, coins) VALUES "
            "(900000000000000102, 700000000000000001, 100)",
        ),
        steps=(
            Step(kind="command", content="!farm", persona="member"),
            Step(kind="click", target_message=1, component_index=1,
                 persona="member"),
            Step(kind="click", target_message=2, component_index=0,
                 persona="member"),
        ),
        notes=(
            "the Buy-hen debit: `!farm` → 🛒 Shop (a fresh send — the "
            "shipped `🐔 Next hen — **40** 🪙 (own 1)` price field over "
            "the funded `Balance: 100 🪙` footer) → the 🐔 Buy hen click "
            "drives the audited farm.buy_chicken op — ONE txn debits 40 🪙 "
            "(reason farm:buy_chicken, balance 100→60) and upserts the "
            "flock to 2 (`🐔 Bought a hen for **40** 🪙! Your flock is "
            "now **2** strong. Balance: **60** 🪙.` — the shipped "
            "farm_workflow buy copy verbatim; buying settles at the OLD "
            "flock size first, the shipped no-retroactive-rate subtlety)"),
    ),
    GoldenCase(
        id="farm.upgrade_coop_write",
        subsystem="farm",
        # a funded fresh farmer: coop_upgrade_price(0) = 100.
        fixture_sql=(
            "INSERT INTO economy_balances (user_id, guild_id, coins) VALUES "
            "(900000000000000102, 700000000000000001, 250)",
        ),
        steps=(
            Step(kind="command", content="!farm", persona="member"),
            Step(kind="click", target_message=1, component_index=1,
                 persona="member"),
            Step(kind="click", target_message=2, component_index=1,
                 persona="member"),
        ),
        notes=(
            "the Upgrade-coop debit: `!farm` → 🛒 Shop (the shipped `🏠 "
            "Coop upgrade — **100** 🪙 → holds 35` price field) → the 🏠 "
            "Upgrade coop click drives the audited farm.upgrade_coop op — "
            "ONE txn debits 100 🪙 (reason farm:upgrade_coop, balance "
            "250→150) and raises the coop to level 1 (`🏠 Upgraded your "
            "coop to level **1** for **100** 🪙 — it now holds **35** "
            "eggs! Balance: **150** 🪙.` — the shipped farm_workflow "
            "upgrade copy verbatim, the dropped holds-clause restored "
            "for this mint)"),
    ),
)
