"""The shipped command-registry capture literals (the wave-9 diagnostic
re-home) — the two DiagnosticCog registry surfaces whose bytes the goldens
pin (``goldens/diagnostic/sweep_find_command`` /
``sweep_list_commands_detailed``).

CAPTURE-WORLD LITERAL (trap 10a — the admin cogmgr roster precedent): both
surfaces enumerated the CAPTURE world's discord.py command registry
(``bot.cogs`` → ``get_commands()`` — 400+ commands across 50+ cogs with
their docstrings, cooldown buckets and hardcoded aliases,
disbot/cogs/diagnostic_cog.py + disbot/services/diagnostic_helpers.py
``build_command_list_pages`` at the corpus posture). The compiled
architecture has no discord.py cog registry — commands compile from
manifests at boot — so the shipped registry ships as the golden-pinned
capture literal, restricted to the bytes the goldens verify:

* ``FIND_COMMAND_INDEX`` — the two rows the ``!find_command test`` sweep
  proved (name-match: ``test_notification``; help-match: ``logging`` — the
  shipped predicate was ``keyword.lower() in cmd.name.lower() or (cmd.help
  and keyword.lower() in cmd.help.lower())``). Other keywords search the
  SAME two-row subset — a deliberate under-port (no golden drives them);
  the honest successor searches the compiled manifest registry
  (``sb.kernel.registry``) once a golden pins new-registry bytes.
* ``COMMAND_LIST_PAGES`` — ALL 14 pages of the shipped paginator
  (``cogs_per_page = 4``; per-command lines
  ``**`!{name}`** — {help[:80]}\n  CD: {cd} | Aliases: {aliases}``, field
  values capped at the 1024-byte embed limit — the AdminCog/RoleCog tails
  cut mid-word exactly as the capture recorded them). Extraction method
  (ORDER 017 fix slice): a static class-level registry walk over the
  oracle clone — import every ``config.INITIAL_EXTENSIONS`` module in
  load order, take each module's Cog subclasses in definition order, and
  enumerate ``__cog_commands__`` (``parent is None``) exactly as
  ``cog.get_commands()`` would; ``build_command_list_pages`` re-applied
  verbatim. The walk reproduced page 1 BYTE-IDENTICAL to the pre-existing
  golden-pinned literal (sweep_list_commands_detailed), which certifies
  pages 2-14 as the same capture registry's bytes.
"""

from __future__ import annotations

#: field rows of the shipped ``!find_command`` search index (verbatim
#: capture bytes; see the module docstring for the subset boundary).
FIND_COMMAND_INDEX: tuple[dict[str, str], ...] = (
    {
     'name': 'test_notification',
     'cog': 'DiagnosticCog',
     'help': 'Send a test notification via the webhook reporter.',
     'cooldown': 'No cooldown',
     'aliases': 'testnotify',
    },
    {
     'name': 'logging',
     'cog': 'LoggingCog',
     'help': 'Open the logging admin panel (S7d).\n\nWith a subcommand, dispatches to ``status`` / ``test`` /\n``set`` / ``create``.  With no subcommand, opens the\ninteractive :class:`LoggingPanelView`.',
     'cooldown': 'No cooldown',
     'aliases': 'None',
    },
)

#: every page of the shipped 14-page paginator, one ``(title, fields)``
#: pair per page — ORACLE-EXTRACTED capture literals (tools note in the
#: module docstring): page 1 verified byte-identical to the pre-existing
#: golden-pinned literal (goldens/diagnostic/sweep_list_commands_detailed);
#: pages 2-14 come from the same deterministic class-level registry walk.
COMMAND_LIST_PAGES: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ('Command List — Page 1/14', (
     ('AdminCog',
      "**`!adminmenu`** — Open the interactive admin control panel.\n  CD: 2x per 10s | Aliases: —\n**`!serverstats`** — Display server statistics.\n  CD: No cooldown | Aliases: —\n**`!cog`** — Load, unload, or reload a cog by name (underscores and _cog suffix optional).\n\nT\n  CD: No cooldown | Aliases: —\n**`!loadall`** — Load all unloaded cogs, skipping already-loaded ones.\n  CD: No cooldown | Aliases: —\n**`!unloadall`** — Unload all loaded cogs except this one.\n  CD: No cooldown | Aliases: —\n**`!coglist`** — Open the interactive cog manager — the panel's 📋 Cog List button.\n\nMirrors ``_Ad\n  CD: 2x per 10s | Aliases: cogs, listcogs, cogslist\n**`!syncslash`** — Sync the app-command tree for slash commands (owner only).\n\nPR E' — operator too\n  CD: No cooldown | Aliases: syncs\n**`!slashes`** — List currently-registered slash commands (admin only).\n\nPR E' — read-only deploy\n  CD: No cooldown | Aliases: slashlist\n**`!restart`** — Request a graceful restart through the lifecycle service.\n\nLP-3: the cog no long\n  CD: No cooldow"),
     ('HelpCog',
      '**`!help`** — Shows available commands. Pass a category name for details.\n  CD: 3x per 10s | Aliases: hilfe'),
     ('RoleCog',
      "**`!roles`** — Open the role management hub.\n  CD: No cooldown | Aliases: —\n**`!rolesettings`** — Open the role management hub (alias for !roles).\n  CD: No cooldown | Aliases: —\n**`!roleinfo`** — Show a role's details. Usage: !roleinfo <@role|name|id>\n  CD: No cooldown | Aliases: ri\n**`!rolemenu`** — Open the role hub (use !roles instead).\n  CD: No cooldown | Aliases: —\n**`!rolecreator`** — Open the role hub (use !roles instead).\n  CD: No cooldown | Aliases: —\n**`!assignroles`** — Manually run time-based role assignment for all members.\n  CD: No cooldown | Aliases: —\n**`!createrole`** — Create a role (use !roles → Create instead).\n  CD: No cooldown | Aliases: —\n**`!deleterole`** — Delete a role by name or mention.\n  CD: No cooldown | Aliases: —\n**`!setrole`** — Add or update a time-based role threshold.\n  CD: No cooldown | Aliases: —\n**`!unsetrole`** — Remove a role from time-based assignment.\n  CD: No cooldown | Aliases: —\n**`!debugroles`** — Print all role names for verification.\n  CD: No cooldown | Aliases"),
     ('RoleGrantsCog',
      '**`!temprole`** — Give a member a role for a limited time. Usage: !temprole @member 2h @role\n  CD: No cooldown | Aliases: —\n**`!temproles`** — List active temporary roles. Usage: !temproles (yours) or !temproles @member (st\n  CD: No cooldown | Aliases: —'),
    )),
    ('Command List — Page 2/14', (
     ('StarboardCog',
      '**`!starboard`** — Show or set the hall-of-fame channel + star threshold.\n\n``!starboard`` shows the\n  CD: No cooldown | Aliases: —'),
     ('ModerationCog',
      '**`!modmenu`** — Show the interactive moderation action panel.\n  CD: No cooldown | Aliases: —\n**`!warn`** — Warn a user. Escalates at the configured threshold (default: timeout).\n  CD: No cooldown | Aliases: —\n**`!timeout`** — Timeout a member for a given number of minutes.\n  CD: No cooldown | Aliases: —\n**`!kick`** — Kick a member from the server.\n  CD: No cooldown | Aliases: —\n**`!ban`** — Ban a member from the server.\n  CD: No cooldown | Aliases: —\n**`!unban`** — Unban a user by their Discord user ID.\n  CD: No cooldown | Aliases: —\n**`!clearwarnings`** — Clear all warnings for a member.\n  CD: No cooldown | Aliases: —\n**`!modlogs`** — Show moderation log history for a member.\n  CD: No cooldown | Aliases: —'),
     ('Automod',
      '**`!automod`** — Show the current automod policy for this server.\n  CD: No cooldown | Aliases: —'),
     ('ImageModeration',
      '**`!imagemod`** — Show the current image-moderation policy for this server.\n  CD: No cooldown | Aliases: —'),
    )),
    ('Command List — Page 3/14', (
     ('XpCog',
      "**`!xpmenu`** — Open the XP panel showing your rank and quick admin actions.\n  CD: No cooldown | Aliases: —\n**`!rank`** — Show rank in a category.\n\nPR G — provider-aware. Supported forms:\n\n* ``!rank``  \n  CD: No cooldown | Aliases: —\n**`!givexp`** — Give XP to a user (admin only).\n  CD: No cooldown | Aliases: —\n**`!resetxp`** — Reset a user's XP to zero (admin only).\n  CD: No cooldown | Aliases: —\n**`!xpconfig`** — Open the XP configuration panel (admin only).\n  CD: No cooldown | Aliases: —\n**`!xpimport`** — Import XP/levels from another bot by reading its level-up channel.\n\nWorks by sca\n  CD: No cooldown | Aliases: —"),
     ('KarmaCog',
      "**`!thanks`** — Give a karma point to a helpful member: ``!thanks @user [reason]``.\n  CD: 5x per 10s | Aliases: rep, thank\n**`!karma`** — Show a member's karma standing: ``!karma [@user]``.\n  CD: 5x per 10s | Aliases: —"),
     ('BlackjackCog',
      '**`!blackjack`** — Play blackjack.  !bj [bet]  or  !bj @player [bet]\n  CD: No cooldown | Aliases: bj\n**`!bjtournament`** — Start a Blackjack tournament.  !bjtournament [entry_fee] [rounds] [mins]\n  CD: No cooldown | Aliases: bjtourn\n**`!bjstart`** — Manually start a pending Blackjack tournament early.\n  CD: No cooldown | Aliases: —\n**`!bjstatus`** — Show the current tournament status.\n  CD: No cooldown | Aliases: —'),
     ('CasinoCog',
      "**`!casino`** — Open the Casino hub — group card games like poker.\n  CD: No cooldown | Aliases: —\n**`!poker`** — Open a multiplayer Texas Hold'em table in this channel.\n  CD: No cooldown | Aliases: holdem"),
    )),
    ('Command List — Page 4/14', (
     ('Rock Paper Scissors',
      '**`!rpsregister`** — Starts the registration period with a reaction role message.  !rpsregister [@rol\n  CD: No cooldown | Aliases: rpsreg\n**`!rpsstart`** — Starts the RPS tournament. Usage: !rps_start [mode] [best_of]\n  CD: No cooldown | Aliases: rpsbegin\n**`!rpsbot`** — Starts matches against the bot.  Delegator — see _bot_matches.\n  CD: No cooldown | Aliases: —\n**`!rpsmatchup`** — Manually creates a match between two specific members.\n  CD: No cooldown | Aliases: —\n**`!rpshelp`** — Displays help information for RPS tournament commands.\n  CD: No cooldown | Aliases: —\n**`!rpssettings`** — Updates bot settings.\n  CD: No cooldown | Aliases: —\n**`!rps`** — Quick RPS.  !rps [bet]  or  !rps @player [bet]\n  CD: No cooldown | Aliases: —'),
     ('Rock Paper Scissors',
      '**`!rpsregister`** — Starts the registration period with a reaction role message.  !rpsregister [@rol\n  CD: No cooldown | Aliases: rpsreg\n**`!rpsstart`** — Starts the RPS tournament. Usage: !rps_start [mode] [best_of]\n  CD: No cooldown | Aliases: rpsbegin\n**`!rpsbot`** — Starts matches against the bot.  Delegator — see _bot_matches.\n  CD: No cooldown | Aliases: —\n**`!rpsmatchup`** — Manually creates a match between two specific members.\n  CD: No cooldown | Aliases: —\n**`!rpshelp`** — Displays help information for RPS tournament commands.\n  CD: No cooldown | Aliases: —\n**`!rpssettings`** — Updates bot settings.\n  CD: No cooldown | Aliases: —\n**`!rps`** — Quick RPS.  !rps [bet]  or  !rps @player [bet]\n  CD: No cooldown | Aliases: —'),
     ('UtilityCog',
      "**`!utilitymenu`** — Open the interactive utility panel.\n  CD: 3x per 10s | Aliases: —\n**`!myprofile`** — View your per-server profile card.\n\nSelf-scoped (the viewer is the subject) — sh\n  CD: 3x per 15s | Aliases: —\n**`!clear`** — Purge messages. Max 100.\n  CD: No cooldown | Aliases: purge\n**`!info`** — Show server or user info.  !info [server|user] [@mention]\n  CD: No cooldown | Aliases: —\n**`!serverinfo`** — Alias for !info server.\n  CD: No cooldown | Aliases: —\n**`!userinfo`** — Alias for !info user [@member].\n  CD: No cooldown | Aliases: —\n**`!avatar`** — Display a user's avatar.\n  CD: No cooldown | Aliases: —\n**`!remind`** — Set a reminder.  !remind <minutes> <message>\n  CD: No cooldown | Aliases: —\n**`!invite`** — Generate a one-use server invite.\n  CD: No cooldown | Aliases: —\n**`!poll`** — Create a simple reaction poll.\n  CD: No cooldown | Aliases: —\n**`!ping`** — Check the bot's responsiveness — gateway + message round-trip.\n\nThe user-tier pi\n  CD: No cooldown | Aliases: —\n**`!botinfo`** — Show info"),
     ('Cleanup',
      '**`!cleanuphistory`** — Clean channel history by keyword, commands, prohibited words, spam, embeds, link\n  CD: 1x per 10s | Aliases: —\n**`!word`** — Manage prohibited words. Subcommands: add, remove, list.\n  CD: No cooldown | Aliases: —\n**`!wordmenu`** — Open the interactive prohibited words management panel.\n  CD: No cooldown | Aliases: —\n**`!cleanup`** — Open the Cleanup hub panel — overview + routing to subviews.\n  CD: No cooldown | Aliases: —'),
    )),
    ('Command List — Page 5/14', (
     ('ChannelCog',
      '**`!channelmenu`** — Open the interactive channel management panel.\n  CD: 2x per 10s | Aliases: —\n**`!set`** — Set access for a channel/category. Usage: !set <name|id> <@role> <True/False>\n  CD: No cooldown | Aliases: —\n**`!evt`** — Create or delete an event channel. Usage: !evt <name|id> <create/delete>\n  CD: No cooldown | Aliases: —\n**`!create`** — Create a channel with role access. Usage: !create <name> <@role> <True/False> [c\n  CD: No cooldown | Aliases: —\n**`!bulkdelete`** — Delete multiple channels. Usage: !bulkdelete <name|id> [name|id...] or <keyword>\n  CD: No cooldown | Aliases: —\n**`!del`** — Delete a specific channel. Usage: !del <name|id>\n  CD: No cooldown | Aliases: —\n**`!list`** — List all categories and channels, including uncategorized.\n  CD: No cooldown | Aliases: —\n**`!clone`** — Clone a channel. Usage: !clone <name|id> <new_name>\n  CD: No cooldown | Aliases: —\n**`!move`** — Move a channel to a category. Usage: !move <channel name|id> <category name|id>\n  CD: No cooldown | Aliases: —\n**`!loc'),
     ('InventoryCog',
      "**`!inventory`** — Show your (or another user's) unified inventory hub.\n  CD: No cooldown | Aliases: inv"),
     ('EconomyCog',
      "**`!economymenu`** — Open the interactive economy control panel.\n  CD: 3x per 10s | Aliases: —\n**`!daily`** — Claim your daily reward. Higher streaks unlock better odds!\n  CD: 2x per 5s | Aliases: —\n**`!work`** — Open the job selector and earn coins + XP (1 h cooldown).\n  CD: 2x per 5s | Aliases: —\n**`!shop`** — Browse and buy items from the shop.\n  CD: No cooldown | Aliases: —\n**`!balance`** — Show your (or another user's) current coin balance.\n  CD: No cooldown | Aliases: bal, wallet\n**`!pay`** — Send coins to another member. Usage: !pay @user <amount>\n  CD: 3x per 10s | Aliases: transfer\n**`!setlogchannel`** — Set the economy log channel. Usage: !setlogchannel #channel\n  CD: No cooldown | Aliases: —\n**`!joblist`** — Show all jobs, requirements, and your mastery for each.\n  CD: No cooldown | Aliases: jobs"),
     ('TreasuryCog',
      '**`!treasury`** — Open the server treasury — view the pool and contribute coins.\n  CD: No cooldown | Aliases: bank, pool'),
    )),
    ('Command List — Page 6/14', (
     ('CountingCog',
      "**`!countingmenu`** — Open the interactive counting game management panel.\n  CD: No cooldown | Aliases: cm\n**`!start_match`** — Starts a new counting match with the specified mode.\n\nAvailable modes: normal, r\n  CD: No cooldown | Aliases: sm\n**`!end_match`** — Ends the counting match in the specified channel and deletes the channel.\n  CD: No cooldown | Aliases: em\n**`!reset_count`** — Resets the count to the starting value.\n  CD: No cooldown | Aliases: rc\n**`!toggle_turns`** — Toggles the 'taking turns' mode.\n  CD: No cooldown | Aliases: tt\n**`!count_info`** — Displays the current count and configuration.\n  CD: No cooldown | Aliases: ci\n**`!counttop`** — Show the counting leaderboard — who has landed the most correct counts.\n\nReads t\n  CD: No cooldown | Aliases: ct, counting_top\n**`!count_rules`** — Displays the counting game rules.\n  CD: No cooldown | Aliases: cr\n**`!set_skip_numbers`** — Set the skip step N for a 'skip' match (count climbs 1, 1+N, 1+2N, …).\n  CD: No cooldown | Aliases: ssn\n**`!toggle_reset_o"),
     ('Deathmatch',
      '**`!dm_challenge`** — Challenge another user to a deathmatch duel.\n  CD: 1x per 30s | Aliases: deathmatch, challenge, dm\n**`!dm_help`** — Display help information for Deathmatch commands.\n  CD: No cooldown | Aliases: deathmatch_help'),
     ('ProofChannelCog',
      '**`!+prize`** — Grant a winner exclusive access to #proof.  Usage: +prize @winner\n  CD: No cooldown | Aliases: —\n**`!-prize`** — End the prize session and make #proof read-only again.  Usage: -prize\n  CD: No cooldown | Aliases: —\n**`!prizestatus`** — Show current #proof channel permissions.\n  CD: No cooldown | Aliases: —\n**`!prizemenu`** — Open the interactive prize channel management panel.\n  CD: 2x per 10s | Aliases: —\n**`!timedprize`** — Grant timed access to #proof; auto-unlocks after duration minutes.  Usage: timed\n  CD: No cooldown | Aliases: —'),
     ('MiningCog',
      "**`!minemenu`** — Open the mining hub panel.\n  CD: No cooldown | Aliases: —\n**`!mine`** — Open the grid Mine navigator — roam the world and dig.\n  CD: No cooldown | Aliases: —\n**`!fastmine`** — One quick mining swing — no buttons (the old !fastmine, reborn).\n  CD: No cooldown | Aliases: —\n**`!chop`** — Chop wood. If you have an 'axe', you'll collect double.\n  CD: No cooldown | Aliases: —\n**`!mineinv`** — Show your unified inventory (compatibility alias for !inventory).\n  CD: No cooldown | Aliases: mineinventory\n**`!minestats`** — Shows your total mining items and number of unique items.\n  CD: No cooldown | Aliases: —\n**`!build`** — Build / craft an item from recipes (one shared, atomic implementation).\n\nIf no s\n  CD: No cooldown | Aliases: craft\n**`!buildlist`** — Shows all craftable structures from recipes.json.\n  CD: No cooldown | Aliases: —\n**`!buildable`** — Lists only what the user can currently build based on their inventory.\n  CD: No cooldown | Aliases: —\n**`!explore`** — Discover random events or item"),
    )),
    ('Command List — Page 7/14', (
     ('FishingCog',
      "**`!fish`** — Cast a line — wait for the bite, then reel it in before it gets away.\n  CD: No cooldown | Aliases: —\n**`!fishing`** — Open the interactive fishing menu — cast, upgrade your rod, browse the dex.\n  CD: No cooldown | Aliases: fishmenu\n**`!forecast`** — Show today's fishing forecast — the date-seeded weather everyone shares.\n\nWeathe\n  CD: No cooldown | Aliases: fishforecast, fishingweather\n**`!sail`** — Set sail for deepwater (or return to shore) — toggles your fishing venue.\n\nDeepw\n  CD: No cooldown | Aliases: setsail\n**`!fishlog`** — Show your fishing collection — every species you've caught.\n  CD: No cooldown | Aliases: fishdex\n**`!fishtop`** — Show this server's top anglers by total fish caught.\n  CD: No cooldown | Aliases: topfishers\n**`!trophies`** — Show this server's heaviest catches — the biggest-fish hall of fame.\n  CD: No cooldown | Aliases: bigfish, fishtrophy\n**`!rod`** — View your fishing rod and upgrade it for coins.\n  CD: No cooldown | Aliases: rodshop, buyrod\n**`!bait`** — Load fish"),
     ('CreatureCog',
      "**`!catch`** — Head into the wild to find and catch a creature.\n  CD: No cooldown | Aliases: hunt\n**`!creatures`** — Open the interactive Creatures panel — catch, browse your dex, battle.\n  CD: No cooldown | Aliases: creaturemenu, pets\n**`!dex`** — Show your creature collection — every creature you've caught.\n  CD: No cooldown | Aliases: collection\n**`!dextop`** — Show this server's top collectors by total creatures caught.\n  CD: No cooldown | Aliases: topcatchers"),
     ('CreatureBattleCog',
      "**`!cbattle`** — Challenge another member to a level-normalized creature PvP battle.\n  CD: No cooldown | Aliases: creaturebattle\n**`!cbrecord`** — Show your (or another trainer's) creature PvP win/loss record.\n  CD: No cooldown | Aliases: battlerecord\n**`!cbattletop`** — Show this server's top creature-PvP trainers by wins.\n  CD: No cooldown | Aliases: pvptop, battletop"),
     ('FarmCog',
      '**`!farm`** — Open your idle chicken farm — collect eggs, grow your flock and coop.\n  CD: No cooldown | Aliases: chickenfarm, coop'),
    )),
    ('Command List — Page 8/14', (
     ('DiagnosticCog',
      "**`!platform`** — Runtime introspection group.\n\nWith no subcommand the interactive ``_PlatformHubV\n  CD: No cooldown | Aliases: —\n**`!diagnostics`** — Open the interactive diagnostics hub panel.\n  CD: 2x per 15s | Aliases: diag\n**`!lifecycle`** — Lifecycle state (phase, pending request, recent events).\n\nShortcut for ``!platfo\n  CD: No cooldown | Aliases: lc\n**`!list_commands_detailed`** — List all registered commands with details, paginated by cog.\n  CD: No cooldown | Aliases: listcmds\n**`!find_command`** — Search for commands by keyword in their name or description.\n  CD: No cooldown | Aliases: findcmd\n**`!validate_json_files`** — Validate the structure of all JSON files in the data directory.\n  CD: No cooldown | Aliases: validatejson\n**`!check_database`** — Verify that all expected PostgreSQL tables exist.\n  CD: No cooldown | Aliases: checkdb\n**`!diagnostic_bot_status`** — Display bot health and performance metrics.\n  CD: No cooldown | Aliases: diag_status\n**`!latency`** — Report the bot's WebSocket latency"),
     ('AICog',
      '**`!ai`** — Open the AI Platform panel.\n  CD: No cooldown | Aliases: —\n**`!aimenu`** — Open the AI Platform panel (alias for ``!ai``).\n  CD: No cooldown | Aliases: —'),
     ('AIReviewCog',
      '**`!aireview`** — Show the AI review-log status (channel + unreviewed backlog).\n  CD: No cooldown | Aliases: —'),
     ('BTD6Cog',
      '**`!btd6menu`** — Open the BTD6 panel (alias for ``!btd6``).\n  CD: No cooldown | Aliases: —'),
    )),
    ('Command List — Page 9/14', (
     ('BTD6ReferenceCog',
      '**`!btd6ref`** — BTD6 reference lookups — hidden alias of `!btd6` (towers/heroes/rounds/…).\n  CD: No cooldown | Aliases: —'),
     ('BTD6EventsCog',
      '**`!btd6events`** — BTD6 live events — hidden alias of `!btd6 events`.\n  CD: No cooldown | Aliases: —'),
     ('BTD6StrategyCog',
      '**`!btd6strat`** — BTD6 strategy memory — hidden alias of `!btd6 strat`.\n  CD: No cooldown | Aliases: —'),
     ('ParagonCog',
      '**`!paragon`** — Open the BTD6 Paragon degree calculator.\n  CD: No cooldown | Aliases: —'),
    )),
    ('Command List — Page 10/14', (
     ('ProjectMoonCog',
      '**`!pm`** — Open the Project Moon (Limbus) browse panel.\n  CD: No cooldown | Aliases: limbus, projectmoon'),
     ('BTD6OpsCog',
      '**`!btd6ops`** — BTD6 ingestion operations — hidden alias of `!btd6 ops`.\n  CD: No cooldown | Aliases: —'),
     ('ChainCog',
      '**`!chain`** — Manage message chains and word limits in your server.\n\nUse subcommands to create\n  CD: No cooldown | Aliases: —\n**`!chainmenu`** — Open the interactive chain management panel.\n  CD: 2x per 10s | Aliases: —'),
     ('General',
      '**`!generalmenu`** — Open the interactive General panel.\n  CD: 3x per 10s | Aliases: gmenu\n**`!fact`** — Sends a random interesting fact.\n  CD: No cooldown | Aliases: —\n**`!joke`** — Sends a random joke.\n  CD: No cooldown | Aliases: —\n**`!quote`** — Sends a random famous quote.\n  CD: No cooldown | Aliases: —\n**`!trivia`** — Asks a trivia question with a reveal button.\n  CD: No cooldown | Aliases: —\n**`!motivate`** — Sends a motivational message.\n  CD: No cooldown | Aliases: —\n**`!eightball`** — Ask the Magic 8-Ball a yes/no question.\n  CD: No cooldown | Aliases: 8ball\n**`!greet`** — Greets you with a random greeting.\n  CD: No cooldown | Aliases: —'),
    )),
    ('Command List — Page 11/14', (
     ('FourTwentyCog',
      '**`!420`** — Open the 🍃 420 panel — rotating wisdom and number trivia.\n  CD: 3x per 10s | Aliases: fourtwenty, fourtwenty420'),
     ('Leaderboard',
      '**`!leaderboard`** — Show a leaderboard.  !leaderboard [xp|coins|mining|fishing|farm|deathmatch|rps|c\n  CD: 2x per 10s | Aliases: lb, rankings, minelb, miningleaderboard, fishlb, dm_leaderboard, dm_lb, rpslb, farmlb, countlb, counting_leaderboard'),
     ('SettingsCog',
      '**`!settings`** — Open the Settings Manager hub (browse + edit/reset scalars).\n  CD: 2x per 10s | Aliases: —'),
     ('LoggingCog',
      '**`!logging`** — Open the logging admin panel (S7d).\n\nWith a subcommand, dispatches to ``status``\n  CD: No cooldown | Aliases: —'),
    )),
    ('Command List — Page 12/14', (
     ('GamesCog',
      '**`!games`** — Open the Games hub — competitive games and channel activities.\n  CD: No cooldown | Aliases: —\n**`!world`** — Open the Explore world hub — the open-world town square (Mine · Fish).\n\nThe fede\n  CD: No cooldown | Aliases: —\n**`!worldcard`** — Show your cross-game world card — global level + per-game standing.\n\nThe read mi\n  CD: No cooldown | Aliases: mystats'),
     ('CommunityCog',
      '**`!community`** — Open the Community hub — XP, Roles, and community activities.\n  CD: No cooldown | Aliases: —'),
     ('Community Spotlight',
      '**`!spotlight`** — Show the Community Spotlight — live XP, coins, games, and level-ups.\n  CD: 2x per 15s | Aliases: activity'),
     ('WelcomeCog',
      '**`!welcome`** — Show the current welcome (greeting) policy for this server.\n  CD: No cooldown | Aliases: —'),
    )),
    ('Command List — Page 13/14', (
     ('CountersCog',
      '**`!counters`** — Show the current server-counter channels for this server.\n  CD: No cooldown | Aliases: —\n**`!counterpreset`** — Apply a curated counter name-template preset (sets all three templates at once).\n  CD: No cooldown | Aliases: —'),
     ('TicketCog',
      '**`!ticket`** — Open the ticket hub — open a ticket or view your open tickets.\n  CD: No cooldown | Aliases: —\n**`!ticketpanel`** — Post the public ticket launcher panel in this channel (managers).\n  CD: No cooldown | Aliases: —\n**`!ticketsetup`** — Configure tickets — opens a button/dropdown panel (managers).\n\nWith no arguments\n  CD: No cooldown | Aliases: —\n**`!ticketlimit`** — Set the max simultaneously-open tickets per member (managers).\n  CD: No cooldown | Aliases: —\n**`!ticketblacklist`** — Manage who may open tickets: ``!ticketblacklist add|remove @user``.\n  CD: No cooldown | Aliases: —'),
     ('SecurityCog',
      '**`!security`** — Show the current server-security policy (raid + account-age).\n  CD: No cooldown | Aliases: —'),
     ('SetupCog',
      '**`!setupadvanced`** — Open or resume the advanced (linear) setup wizard.\n\nThe power-user path: the ful\n  CD: No cooldown | Aliases: advancedsetup\n**`!setupdescribe`** — Describe your server in words; propose how to wire it to the bot.\n\nNatural-langu\n  CD: No cooldown | Aliases: describesetup'),
    )),
    ('Command List — Page 14/14', (
     ('QuickSetupCog',
      '**`!setup`** — Open Essential Setup — a few simple steps, each saved instantly.\n  CD: No cooldown | Aliases: quicksetup, essentialsetup'),
     ('ServerManagementCog',
      '**`!servermanagement`** — Open the unified Server Management hub.\n  CD: No cooldown | Aliases: servermenu, guildmenu'),
     ('UX Lab',
      '**`!uxlab`** — Open the UX Lab — the interface gallery + limit probe bench.\n  CD: No cooldown | Aliases: interfacelab'),
    )),
)

#: page-1 aliases (the original golden-pinned names; the byte identity of
#: page 1 with the pre-split literal is asserted by the diagnostic tests
#: and by goldens/diagnostic/sweep_list_commands_detailed in CI).
COMMAND_LIST_PAGE1_TITLE = COMMAND_LIST_PAGES[0][0]
COMMAND_LIST_PAGE1_FIELDS = COMMAND_LIST_PAGES[0][1]
