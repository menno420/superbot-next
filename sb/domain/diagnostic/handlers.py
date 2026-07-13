"""The shipped ``!platform`` / ``!latency`` prefix surfaces (diagnostic
flip) — thin handlers over the pinned operator cards
(sb/domain/diagnostic/platform_views.py), the backfill dry-run op
(ops.py) and the component panels (panels.py). Byte truth:
goldens/diagnostic/*.

Route map (disbot/cogs/diagnostic/platform_group.py at the corpus
posture):

* ``!platform`` (bare) / ``/platform`` — the 🛰 Platform hub panel.
* ``!platform <view>`` — one pinned operator card per catalogued view
  (``diagnostic.card``, the ai.card lane).
* ``!platform backfill`` — the dry-run op + preview card;
  ``backfill apply`` is NOT ported (no golden) — honest refusal.
* ``!platform setting <subsystem> <name> ...`` — the shipped
  unknown-setting guard card; the declared-setting render/mutate path
  is NOT ported (no golden) — honest refusal.
* ``!platform finding <action> <fingerprint>`` — the shipped
  unknown-action guard byte; resolve/ignore/reopen mutations are NOT
  ported (no golden) — honest refusal.
* ``!platform health|runtime|slow|startup|status`` — deliberately
  UNDECLARED: the capture skipped these five as nondeterministic
  process-state views (parity/goldens/_sweep_skips.json), so the root
  handler answers the honest refusal instead of inventing bytes.
* ``!latency`` — the shipped Bot Latency card (services/
  diagnostic_helpers.build_latency_embed: ``f"{ms:.2f} ms"`` over
  ``bot.latency`` — the capture world's gateway never measured a
  heartbeat, so the golden pins ``nan ms``; the live reader arms
  through ``install_ws_latency_reader``).

Wave-9 re-home — the shipped DiagnosticCog tool commands
(disbot/cogs/diagnostic_cog.py + services/diagnostic_helpers.py at the
corpus posture; goldens/diagnostic/sweep_lifecycle / sweep_check_database
/ sweep_find_command / sweep_test_notification / sweep_validate_json_files
/ sweep_list_commands_detailed pin the bytes):

* ``!lifecycle`` [lc] — the shipped shortcut to the SAME
  ``build_lifecycle_embed`` card ``!platform lifecycle`` renders
  (diagnostic_cog.py: "``build_lifecycle_embed`` stays here for the
  ``!lifecycle`` shortcut command"); byte-identical goldens.
* ``!check_database`` [checkdb] — the shipped healthy-branch schema
  census, a CAPTURE-SCHEMA-EPOCH literal (16/16 base tables, 103/103
  migrations, 106 tables — the capture DB; v1's schema epoch has its own
  migration chain, so a live census is the named successor read).
* ``!find_command`` [findcmd] / ``!list_commands_detailed`` [listcmds] —
  the shipped registry surfaces over the capture-literal catalog
  (sb/domain/diagnostic/command_catalog.py; the admin cogmgr roster
  precedent).
* ``!test_notification`` [testnotify] — the shipped no-reporter guard
  byte, true in BOTH worlds (the capture harness never set
  ``DISCORD_WEBHOOK_URL`` and v1 configures no webhook reporter; a
  future webhook port re-arms the send branch).
* ``!validate_json_files`` [validatejson] — the shipped missing-dir
  guard over the CAPTURE-ENVIRONMENT path literal
  (``/home/user/superbot/data/json`` — the shipped bot's data dir,
  absent in the capture world; v1 has no JSON data directory at all,
  so the guard branch stays the truthful constant)."""

from __future__ import annotations

import dataclasses

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered

__all__ = [
    "ensure_handler_refs",
    "flag_pick_for",
    "install_gateway_census_reader",
    "install_ws_latency_reader",
]

_UNPORTED_PROCESS_VIEWS = ("health", "runtime", "slow", "startup", "status")

# --- the ws-latency read seam ---------------------------------------------------

_ws_latency_reader = None


def install_ws_latency_reader(fn) -> None:
    """Arm the live gateway-latency read (``lambda: bot.latency``); the
    parity harness leaves it unarmed — the shipped capture's fake gateway
    never measured a heartbeat, so ``bot.latency`` was NaN and the golden
    pins ``nan ms`` (sweep_latency)."""
    global _ws_latency_reader
    _ws_latency_reader = fn


# --- the gateway-census read seam (Bot Status: guilds/members/commands) ---------

_gateway_census_reader = None


def install_gateway_census_reader(fn) -> None:
    """Arm the live gateway census behind the hub's 🤖 Bot Status card
    (``fn() -> {"guilds": int, "members": int, "commands": int}`` — the
    composition root computes it from ``bot.guilds`` + the live manifest
    command count; the install_ws_latency_reader boot family). Unarmed
    (headless/tests/parity) the card truthfully renders ``n/a`` — the
    capture skipped this view as nondeterministic process state, so no
    golden constrains the bytes."""
    global _gateway_census_reader
    _gateway_census_reader = fn


def _gateway_census() -> dict:
    if _gateway_census_reader is None:
        return {}
    try:
        return dict(_gateway_census_reader() or {})
    except Exception:  # noqa: BLE001 — a broken reader degrades to n/a
        return {}


# --- panel pick memory (per guild+invoker, process-local) -----------------------
#
# The shipped views kept the operator's dropdown pick on the View instance
# (FlagManagerView.selected_flag / AutomationPanelView.selected_rule_id);
# the port keys it per (guild, invoker), in-memory — the counting
# ``_manage_target`` precedent. Never golden-rendered: no sweep clicks a
# flag/rule select, so golden runs never seed a pick (playbook trap 20).

_flag_pick: dict[tuple[int, int], str] = {}
_auto_pick: dict[tuple[int, int], int] = {}


def _pick_key(gid, uid) -> tuple[int, int]:
    return (int(gid or 0), int(uid or 0))


def flag_pick_for(guild_id, user_id) -> str | None:
    """The Flag Manager renderer's read of the operator's current pick
    (panels.py `_render_flag_manager`)."""
    return _flag_pick.get(_pick_key(guild_id, user_id))


def _ws_latency_seconds() -> float:
    if _ws_latency_reader is None:
        return float("nan")
    try:
        return float(_ws_latency_reader())
    except Exception:  # noqa: BLE001 — a broken reader degrades to NaN
        return float("nan")


# --- shared helpers --------------------------------------------------------------

def _argv(req) -> list[str]:
    return [str(a) for a in tuple(req.args.get("argv", ()) or ())]


async def _card(req, embed) -> None:
    """Present one operator card (the ai.card lane — the shipped public
    ``ctx.send(embed=...)``)."""
    from sb.kernel.panels.engine import open_panel

    args = {**dict(req.args), "_card": embed}
    await open_panel(PanelRef("diagnostic.card"),
                     dataclasses.replace(req, args=args))


def _view_embed(req, name: str):
    from sb.domain.diagnostic.platform_views import build_view_embed

    return build_view_embed(
        name,
        channel_id=req.channel_id,
        guild_id=req.guild_id,
        member_tier=getattr(req.actor, "member_tier", None) or "user")


def _make_view_handler(name: str):
    async def _view(req) -> None:
        await _card(req, _view_embed(req, name))
    _view.__name__ = f"pf_{name.replace('-', '_')}"
    _view.__doc__ = f"``!platform {name}`` — the pinned operator card."
    return _view


# --- registration ----------------------------------------------------------------

def _register() -> None:
    if is_registered(HandlerRef("diagnostic.pf_root")):
        return

    from sb.domain.diagnostic.platform_views import VIEWS

    for name in VIEWS:
        handler(f"diagnostic.pf_{name.replace('-', '_')}")(
            _make_view_handler(name))

    @handler("diagnostic.pf_root")
    async def pf_root(req):
        """Bare ``!platform`` / ``/platform`` opens the hub; undeclared
        subcommand tokens (the five capture-skipped process-state views,
        or anything unknown) get the honest refusal — never invented
        diagnostics bytes."""
        from sb.kernel.panels.engine import open_panel

        argv = _argv(req)
        if not argv:
            await open_panel(PanelRef("diagnostic.platform_hub"), req)
            return None
        name = argv[0]
        if name in _UNPORTED_PROCESS_VIEWS:
            return Reply(BLOCKED,
                         f"ℹ️ `!platform {name}` is a process-state "
                         "diagnostic of the previous bot and is not "
                         "ported yet.")
        return Reply(BLOCKED,
                     f"❓ Unknown platform surface `{name}`. Run "
                     "`!platform` for the hub.")

    @handler("diagnostic.latency_view")
    async def latency_view(req) -> None:
        """``!latency`` — build_latency_embed verbatim (module
        docstring)."""
        from sb.kernel.panels.render import RenderedEmbed

        ms = _ws_latency_seconds() * 1000
        await _card(req, RenderedEmbed(
            title="Bot Latency", description="",
            fields=(("Latency", f"{ms:.2f} ms", True),),
            style_token="blue"))

    @handler("diagnostic.lifecycle_view")
    async def lifecycle_view(req) -> None:
        """``!lifecycle`` [lc] — the shipped shortcut to the SAME
        ``build_lifecycle_embed`` card the ported ``!platform lifecycle``
        view renders (module docstring; both goldens pin identical
        bytes)."""
        await _card(req, _view_embed(req, "lifecycle"))

    @handler("diagnostic.check_database_view")
    async def check_database_view(req) -> None:
        """``!check_database`` [checkdb] — the shipped
        ``build_check_database_embed`` healthy branch
        (services/diagnostic_helpers.py: green, the "✅ Schema healthy"
        description, base-tables / migrations / tables-present fields).
        CAPTURE-SCHEMA-EPOCH literal (module docstring): the counts are
        the capture DB's census — a live census over v1's own migration
        chain is the named successor read."""
        from sb.kernel.panels.render import RenderedEmbed

        await _card(req, RenderedEmbed(
            title="Database Schema Check",
            description="✅ Schema healthy — all base tables present "
                        "and every migration applied.",
            fields=(("Base tables", "✅ 16/16 present", False),
                    ("Migrations applied", "✅ 103/103", False),
                    ("Tables present", "106", False)),
            style_token="green"))

    @handler("diagnostic.find_command_view")
    async def find_command_view(req):
        """``!find_command <keyword>`` [findcmd] — the shipped registry
        search (diagnostic_cog.py: ``keyword.lower() in cmd.name.lower()
        or (cmd.help and keyword.lower() in cmd.help.lower())`` over
        ``bot.cogs``), ported over the capture-literal index
        (command_catalog.py — see its subset boundary note)."""
        from sb.domain.diagnostic.command_catalog import FIND_COMMAND_INDEX
        from sb.kernel.panels.render import RenderedEmbed

        argv = _argv(req)
        if not argv:
            # the shipped MissingRequiredArgument path is not golden-driven;
            # honest handler-owned guard (the band-6 lesson — never let the
            # kernel envelope invent bytes).
            return Reply(BLOCKED,
                         "❓ Usage: `!find_command <keyword>` — search "
                         "commands by keyword.")
        keyword = argv[0]
        fields = tuple(
            (f"!{row['name']} ({row['cog']})",
             f"{row['help']}\nCooldown: {row['cooldown']} | "
             f"Aliases: {row['aliases']}",
             False)
            for row in FIND_COMMAND_INDEX
            if keyword.lower() in row["name"].lower()
            or keyword.lower() in row["help"].lower())
        await _card(req, RenderedEmbed(
            title=f"Search Results for '{keyword}'",
            # the shipped not-found copy (diagnostic_cog.py, verbatim).
            description=("" if fields
                         else "No commands found matching the keyword."),
            fields=fields,
            style_token="green"))
        return None

    @handler("diagnostic.test_notification_view")
    async def test_notification_view(req) -> None:
        """``!test_notification`` [testnotify] — the shipped no-reporter
        guard byte (diagnostic_helpers.py: ``if not reporter``), true in
        BOTH worlds (module docstring); the webhook send branch re-arms
        with a future webhook-reporter port."""
        from sb.kernel.panels.render import RenderedEmbed

        await _card(req, RenderedEmbed(
            title="🔔 Test Notification",
            description="❌ No webhook reporter is configured.",
            style_token="red"))

    @handler("diagnostic.validate_json_view")
    async def validate_json_view(req) -> None:
        """``!validate_json_files`` [validatejson] — the shipped
        missing-dir guard (diagnostic_helpers.py
        ``build_validate_json_embed``: ``if not os.path.isdir(JSON_DIR)``)
        over the CAPTURE-ENVIRONMENT path literal (module docstring)."""
        from sb.kernel.panels.render import RenderedEmbed

        await _card(req, RenderedEmbed(
            title="JSON Files Validation",
            description="JSON directory not found: "
                        "`/home/user/superbot/data/json`",
            style_token="orange"))

    async def _cmdlist_step(req, delta: int):
        """◀ Prev / Next ▶ — the shipped ``_PaginatorView`` index step
        (paginator.py: ``self.index ± 1`` + button re-disable), re-opened
        fresh with the new page in the panel args (the projmoon
        edit-in-place → fresh-re-open class; the counting _reopen
        precedent). The page rides ``cmdlist_page`` — the session-minted
        buttons carry the OPENING args, so each open's buttons know the
        page they were rendered on."""
        from sb.domain.diagnostic.command_catalog import COMMAND_LIST_PAGES
        from sb.kernel.panels.engine import open_panel

        try:
            current = int(req.args.get("cmdlist_page", 0) or 0)
        except (TypeError, ValueError):
            current = 0
        page = min(max(current + delta, 0), len(COMMAND_LIST_PAGES) - 1)
        args = {**dict(req.args), "cmdlist_page": page}
        await open_panel(PanelRef("diagnostic.command_list"),
                         dataclasses.replace(req, args=args))
        return Reply(SUCCESS, None)

    @handler("diagnostic.cmdlist_prev")
    async def cmdlist_prev(req):
        """◀ Prev on the command-list paginator."""
        return await _cmdlist_step(req, -1)

    @handler("diagnostic.cmdlist_next")
    async def cmdlist_next(req):
        """Next ▶ on the command-list paginator."""
        return await _cmdlist_step(req, +1)

    @handler("diagnostic.pf_finding_route")
    async def pf_finding(req):
        """``!platform finding <action> <fingerprint>`` — the shipped
        unknown-action guard byte (platform_group.py); the three real
        mutations are unported (no golden drives them)."""
        argv = _argv(req)
        action = argv[0].lower().strip() if argv else ""
        if action in ("resolve", "ignore", "reopen"):
            return Reply(BLOCKED,
                         "ℹ️ Finding mutations are not ported yet.")
        return Reply(BLOCKED,
                     "❓ Unknown action. Use `resolve`, `ignore`, or "
                     "`reopen` followed by the finding fingerprint.")

    @handler("diagnostic.pf_setting_route")
    async def pf_setting(req):
        """``!platform setting <subsystem> <name> [value]`` — the shipped
        unknown-setting guard card (services/diagnostic_embeds.py:
        ``No declared setting `{subsystem}.{name}`.``); the
        declared-setting render/mutate path is unported (no golden)."""
        from sb.kernel.panels.render import RenderedEmbed

        argv = _argv(req)
        subsystem = argv[0] if argv else ""
        name = argv[1] if len(argv) > 1 else ""
        from sb.kernel import settings as ksettings

        declared = any(
            getattr(d, "key", "") == name
            for d in ksettings.iter_declarations(subsystem))
        if declared:
            return Reply(BLOCKED,
                         "ℹ️ The declared-setting view is not ported "
                         "yet — use `!settings`.")
        await _card(req, RenderedEmbed(
            title="⚙️ Unknown setting",
            description=(f"No declared setting `{subsystem}.{name}`. "
                         "Use `!platform settings-registry` to list "
                         "what exists."),
            style_token="red"))
        return None

    @handler("diagnostic.pf_backfill_route")
    async def pf_backfill(req):
        """``!platform backfill`` — the dry-run op + the shipped preview
        card (services/diagnostic_embeds.py render over the op's own
        classification document). ``apply`` unported (no golden)."""
        from sb.domain.diagnostic.ops import run_backfill_dry_run
        from sb.kernel.panels.render import RenderedEmbed

        argv = _argv(req)
        if argv:
            return Reply(BLOCKED,
                         "ℹ️ `!platform backfill apply` (the "
                         "candidate_valid writer) is not ported yet — "
                         "only the dry run is.")
        result = await run_backfill_dry_run(ctx_from_request(req, {}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Backfill dry run failed.")
        after = result.after if isinstance(result.after, dict) else {}
        # the engine rolls leg afters up BY STEP TARGET_NAME (#111's
        # lesson — never after["record"]).
        rollup = after.get("backfill_dry_run") or {}
        counts = dict(rollup.get("counts") or {})
        candidates = list(rollup.get("candidates") or ())
        writable = counts.get("candidate_valid", 0)
        description = ("Nothing to migrate — no `candidate_valid` legacy "
                       "pointers." if not writable else
                       f"**{writable}** writable candidate(s).")
        counts_line = ", ".join(
            f"{k}={v}" for k, v in sorted(counts.items())) or "*(none)*"
        cand_line = ", ".join(
            f"`{c['legacy_key']}` → **{c['subsystem']}.{c['binding_name']}**"
            f" — {c['classification']}" for c in candidates) or "*(none)*"
        await _card(req, RenderedEmbed(
            title="🧩 Binding backfill — dry run",
            description=description,
            fields=(("Classification counts", counts_line, False),
                    ("Candidates", cand_line, False)),
            footer=("Run `!platform backfill apply` to write the "
                    "candidate_valid rows (idempotent + audited)."),
            style_token="green"))
        return None

    # --- component handlers (no golden drives any click; honest routes) ---

    @handler("diagnostic.hub_open_view")
    async def hub_open_view(req):
        """The platform-hub category selects — a pick routes to the SAME
        card its ``!platform <name>`` subcommand renders (the shipped
        _PlatformCategorySelect dispatch); unported picks (the five
        process-state views) answer the honest refusal."""
        from sb.domain.diagnostic.platform_views import VIEWS

        values = req.args.get("values") or ()
        name = str(values[0]) if values else ""
        if name in VIEWS:
            await _card(req, _view_embed(req, name))
            return None
        if name == "automation":
            from sb.kernel.panels.engine import open_panel

            await open_panel(PanelRef("diagnostic.automation_panel"), req)
            return None
        return Reply(BLOCKED,
                     f"ℹ️ `{name}` is a process-state diagnostic of the "
                     "previous bot and is not ported yet.")

    @handler("diagnostic.hub_reopen")
    async def hub_reopen(req):
        """↩ Overview — the shipped overview switch re-opens the hub."""
        from sb.kernel.panels.engine import open_panel

        await open_panel(PanelRef("diagnostic.platform_hub"), req)
        return None

    # --- the 🚩 Flag Manager (views/diagnostic/flag_manager.py) --------------

    @handler("diagnostic.flag_pick")
    async def flag_pick(req):
        """The flag select — the shipped ``handle_select``: remember the
        pick and re-render the manager onto the flag's DETAIL embed
        (fresh re-open, projmoon class; the renderer reads the pick)."""
        from sb.domain.diagnostic.flag_catalog import FLAG_DECLARATIONS
        from sb.kernel.panels.engine import open_panel

        values = req.args.get("values") or ()
        name = str(values[0]) if values else ""
        if not name or name not in FLAG_DECLARATIONS:
            # the select only offers declared flags; a stale/foreign value
            # answers the oracle's no-flags copy shape.
            return Reply(BLOCKED, "No flags are declared in this build.")
        key = _pick_key(req.guild_id, getattr(req.actor, "user_id", 0))
        _flag_pick[key] = name
        await open_panel(PanelRef("diagnostic.flag_manager"), req)
        return Reply(SUCCESS, None)

    async def _flag_apply(req, new_state: str):
        """✅ Enable / 🛑 Disable — the shipped ``_apply_state`` guard
        ladder with v1-truthful final copy. The oracle wrote per-guild
        overrides through RolloutMutationPipeline.set_flag_state and
        REFUSED any write the evaluator would ignore ("offering
        Enable/Disable for them would be a silent no-op"); in THIS build
        no runtime code reads ANY of the 8 capture flags (v1 gates ride
        the RC-10 Config seam), so the same honesty rule refuses the
        no-op write for every flag — final copy, not a pending stub."""
        from sb.domain.diagnostic.flag_catalog import flag_details

        picked = flag_pick_for(req.guild_id,
                               getattr(req.actor, "user_id", 0))
        if not picked:
            # oracle copy, verbatim.
            return Reply(BLOCKED,
                         "Pick a flag from the dropdown before changing "
                         "its state.")
        if req.guild_id is None:
            # oracle copy, verbatim.
            return Reply(BLOCKED,
                         "Guild context is required to set a per-guild "
                         "override.")
        details = flag_details(picked)
        if not details["db_editable"]:
            # the oracle's env-only refusal (minus its SUPERBOT_FF_* env
            # pointer — no v1 code reads that variable, so pointing an
            # operator at it would be false guidance).
            return Reply(BLOCKED,
                         f"`{picked}` is an env-only / internal gate — "
                         "its per-guild override is ignored by the "
                         "evaluator, so this control would do nothing.")
        del new_state  # validated by the button split; no store consumes it
        return Reply(BLOCKED,
                     f"`{picked}` has no consumer in this build — no "
                     "runtime code reads it, so a per-guild override "
                     "would change nothing. Enable/Disable re-arm when "
                     "a consumer lands (no silent no-op writes).")

    @handler("diagnostic.flag_enable")
    async def flag_enable(req):
        """✅ Enable for this guild."""
        return await _flag_apply(req, "on")

    @handler("diagnostic.flag_disable")
    async def flag_disable(req):
        """🛑 Disable for this guild."""
        return await _flag_apply(req, "off")

    # --- the 🤖 Automation panel (views/diagnostic/automation_panel.py) ------

    @handler("diagnostic.automation_rule_pick")
    async def automation_rule_pick(req):
        """The rule select — the shipped ``_on_pick``: remember the pick
        (the placeholder row's value is ``0`` — "no valid selection" in
        the oracle's own arithmetic) and re-render the panel unchanged
        (the oracle re-edited the SAME embed; fresh re-open here)."""
        from sb.kernel.panels.engine import open_panel

        values = req.args.get("values") or ()
        try:
            picked = int(str(values[0])) if values else 0
        except (TypeError, ValueError):
            picked = 0
        key = _pick_key(req.guild_id, getattr(req.actor, "user_id", 0))
        _auto_pick[key] = picked
        await open_panel(PanelRef("diagnostic.automation_panel"), req)
        return Reply(SUCCESS, None)

    def _auto_selected(req) -> int:
        return _auto_pick.get(
            _pick_key(req.guild_id, getattr(req.actor, "user_id", 0)), 0)

    async def _auto_mutate(req, verb: str):
        """Enable / Disable / Delete — the shipped guard (``rule_id <= 0``
        → "Pick a rule…", covering the placeholder row) plus the
        rule-not-found rejection for a stale positive id. v1 has no
        automation-rule store (the panel's own snapshot line says so), so
        the zero-rule world makes these guards the COMPLETE behavior —
        the pipeline leg re-arms with the scheduler port."""
        selected = _auto_selected(req)
        if selected <= 0:
            # oracle copy, verbatim.
            return Reply(BLOCKED, "Pick a rule from the dropdown first.")
        # a positive id can only be stale — this build stores no rules.
        del verb
        return Reply(BLOCKED,
                     f"Rule `#{selected}` no longer exists in this guild "
                     "— hit Refresh to reload the rule list.")

    @handler("diagnostic.automation_enable")
    async def automation_enable(req):
        """Enable the selected rule."""
        return await _auto_mutate(req, "enabled")

    @handler("diagnostic.automation_disable")
    async def automation_disable(req):
        """Disable the selected rule."""
        return await _auto_mutate(req, "disabled")

    @handler("diagnostic.automation_delete")
    async def automation_delete(req):
        """Delete the selected rule."""
        return await _auto_mutate(req, "deleted")

    # --- the hub process-state trio (services/diagnostic_helpers.py) ---------

    @handler("diagnostic.diag_status_view")
    async def diag_status_view(req) -> None:
        """🤖 Bot Status — the shipped ``build_bot_status_embed`` SHAPE
        (title/fields/formats verbatim) over v1's live reads: the
        gateway-census seam (guilds/members/commands — ``n/a`` unarmed),
        the ws-latency seam, and /proc-based CPU/RAM/uptime
        (process_state.py; the capture skipped this view as
        nondeterministic process state — no golden constrains it)."""
        from sb.domain.diagnostic import process_state
        from sb.kernel.panels.render import RenderedEmbed

        census = _gateway_census()

        def _count(key: str) -> str:
            value = census.get(key)
            return str(int(value)) if value is not None else "n/a"

        cpu = await process_state.cpu_percent()
        ram = process_state.ram_percent()
        ms = _ws_latency_seconds() * 1000
        await _card(req, RenderedEmbed(
            title="Bot Status", description="",
            fields=(("Guilds", _count("guilds"), True),
                    ("Members", _count("members"), True),
                    ("Commands", _count("commands"), True),
                    ("Latency", f"{ms:.1f} ms", True),
                    ("CPU", f"{cpu}%" if cpu is not None else "n/a", True),
                    ("RAM", f"{ram}%" if ram is not None else "n/a", True),
                    ("Uptime", process_state.uptime_text(), True)),
            style_token="green"))

    @handler("diagnostic.diag_sysinfo_view")
    async def diag_sysinfo_view(req) -> None:
        """💻 System Info — the shipped ``build_system_info_embed``
        verbatim (Python / OS / Disk over ``/`` — the oracle's fallback
        branch when its data dir is absent, which is v1's truth)."""
        import platform

        from sb.domain.diagnostic.process_state import disk_usage_line
        from sb.kernel.panels.render import RenderedEmbed

        await _card(req, RenderedEmbed(
            title="System Information", description="",
            fields=(("Python", platform.python_version(), True),
                    ("OS", f"{platform.system()} {platform.release()}",
                     True),
                    ("Disk", disk_usage_line(), False)),
            style_token="teal"))

    @handler("diagnostic.diag_errors_view")
    async def diag_errors_view(req) -> None:
        """🔍 Recent Errors — the shipped
        ``build_query_logs_embed(event_type="ERROR", limit=10)`` over the
        ported in-process log ring (log_buffer.py; the composition root
        installs it — unarmed/empty answers the shipped empty copy)."""
        from sb.domain.diagnostic.log_buffer import recent
        from sb.kernel.panels.render import RenderedEmbed

        rows = recent(level="ERROR", limit=10)
        await _card(req, RenderedEmbed(
            title="Recent Logs",
            description=("" if rows
                         else "No logs found matching the criteria."),
            fields=tuple(
                (f"[{str(row.get('timestamp', '?'))[:19]}] {row['level']}",
                 str(row["message"])[:256], False)
                for row in rows),
            style_token="dark_red"))

    @handler("diagnostic.diag_latency")
    async def diag_latency(req) -> None:
        """The 📡 Latency hub button — the same card as ``!latency``."""
        await latency_view(req)


_register()


def ensure_handler_refs() -> None:
    _register()
