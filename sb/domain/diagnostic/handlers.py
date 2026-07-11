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
  through ``install_ws_latency_reader``)."""

from __future__ import annotations

import dataclasses

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.spec.refs import HandlerRef, PanelRef, handler, is_registered

__all__ = ["ensure_handler_refs", "install_ws_latency_reader"]

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

    @handler("diagnostic.flag_pending")
    async def flag_pending(req):
        """Flag-manager mutations (enable/disable) and refresh — the
        rollout pipeline is unported; honest pending copy."""
        return Reply(BLOCKED,
                     "ℹ️ The flag rollout pipeline is not ported yet.")

    @handler("diagnostic.automation_pending")
    async def automation_pending(req):
        """Automation-rule mutations — the scheduler is unported."""
        return Reply(BLOCKED,
                     "ℹ️ The automation scheduler is not ported yet.")

    @handler("diagnostic.diag_pending")
    async def diag_pending(req):
        """Diagnostics-hub tools that are still process-state under-ports
        (Bot Status / System Info / Database / JSON / Commands / Errors /
        Notify)."""
        return Reply(BLOCKED,
                     "ℹ️ This diagnostic tool is not ported yet.")

    @handler("diagnostic.diag_latency")
    async def diag_latency(req) -> None:
        """The 📡 Latency hub button — the same card as ``!latency``."""
        await latency_view(req)


_register()


def ensure_handler_refs() -> None:
    _register()
