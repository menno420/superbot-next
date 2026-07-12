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
* ``COMMAND_LIST_PAGE1_*`` — page 1 of the shipped 14-page paginator
  (``cogs_per_page = 4``; per-command lines
  ``**`!{name}`** — {help[:80]}\n  CD: {cd} | Aliases: {aliases}``, field
  values capped at the 1024-byte embed limit — the AdminCog/RoleCog tails
  cut mid-word exactly as the capture recorded them). Pages 2-14 land with
  a successor slice (the admin cogmgr page-window precedent).
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

#: the shipped paginator page-1 title (14 pages at capture: the
#: 50+-cog registry in 4-cog chunks).
COMMAND_LIST_PAGE1_TITLE = 'Command List — Page 1/14'

#: page-1 fields, one per cog, verbatim capture bytes (values carry the
#: shipped 1024-byte truncation exactly as recorded).
COMMAND_LIST_PAGE1_FIELDS: tuple[tuple[str, str], ...] = (
    ('AdminCog',
     "**`!adminmenu`** — Open the interactive admin control panel.\n  CD: 2x per 10s | Aliases: —\n**`!serverstats`** — Display server statistics.\n  CD: No cooldown | Aliases: —\n**`!cog`** — Load, unload, or reload a cog by name (underscores and _cog suffix optional).\n\nT\n  CD: No cooldown | Aliases: —\n**`!loadall`** — Load all unloaded cogs, skipping already-loaded ones.\n  CD: No cooldown | Aliases: —\n**`!unloadall`** — Unload all loaded cogs except this one.\n  CD: No cooldown | Aliases: —\n**`!coglist`** — Open the interactive cog manager — the panel's 📋 Cog List button.\n\nMirrors ``_Ad\n  CD: 2x per 10s | Aliases: cogs, listcogs, cogslist\n**`!syncslash`** — Sync the app-command tree for slash commands (owner only).\n\nPR E' — operator too\n  CD: No cooldown | Aliases: syncs\n**`!slashes`** — List currently-registered slash commands (admin only).\n\nPR E' — read-only deploy\n  CD: No cooldown | Aliases: slashlist\n**`!restart`** — Request a graceful restart through the lifecycle service.\n\nLP-3: the cog no long\n  CD: No cooldow"),
    ('HelpCog',
     '**`!help`** — Shows available commands. Pass a category name for details.\n  CD: 3x per 10s | Aliases: hilfe'),
    ('RoleCog',
     "**`!roles`** — Open the role management hub.\n  CD: No cooldown | Aliases: —\n**`!rolesettings`** — Open the role management hub (alias for !roles).\n  CD: No cooldown | Aliases: —\n**`!roleinfo`** — Show a role's details. Usage: !roleinfo <@role|name|id>\n  CD: No cooldown | Aliases: ri\n**`!rolemenu`** — Open the role hub (use !roles instead).\n  CD: No cooldown | Aliases: —\n**`!rolecreator`** — Open the role hub (use !roles instead).\n  CD: No cooldown | Aliases: —\n**`!assignroles`** — Manually run time-based role assignment for all members.\n  CD: No cooldown | Aliases: —\n**`!createrole`** — Create a role (use !roles → Create instead).\n  CD: No cooldown | Aliases: —\n**`!deleterole`** — Delete a role by name or mention.\n  CD: No cooldown | Aliases: —\n**`!setrole`** — Add or update a time-based role threshold.\n  CD: No cooldown | Aliases: —\n**`!unsetrole`** — Remove a role from time-based assignment.\n  CD: No cooldown | Aliases: —\n**`!debugroles`** — Print all role names for verification.\n  CD: No cooldown | Aliases"),
    ('RoleGrantsCog',
     '**`!temprole`** — Give a member a role for a limited time. Usage: !temprole @member 2h @role\n  CD: No cooldown | Aliases: —\n**`!temproles`** — List active temporary roles. Usage: !temproles (yours) or !temproles @member (st\n  CD: No cooldown | Aliases: —'),
)
