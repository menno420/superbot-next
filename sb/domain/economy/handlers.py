"""Economy read/command handlers (band 3) — thin HandlerRef routes.

Reads render from the K3 seam; the ONE pointer write (`!setlogchannel`)
routes through the band-1 settings ops (§4.1 one-write-path — economy never
touches the bindings table itself). `!work <job>` runs the K7 op; bare
`!work` lists eligible jobs (the shipped dropdown becomes the panel-action
slice, successor work).
"""

from __future__ import annotations

from dataclasses import dataclass

from sb.spec.outcomes import BLOCKED, SUCCESS

__all__ = ["Reply", "ensure_handler_refs"]


@dataclass(frozen=True)
class Reply:
    outcome: str
    user_message: str


def _ctx_from_req(req, params: dict):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=req.actor, guild_id=int(req.guild_id or 0),
        request_id=req.request_id, confirmed=req.confirmed, params=params)


def _target_id(req) -> int:
    """Optional member arg (mention) else the invoker — shipped !balance."""
    argv = tuple(req.args.get("argv", ()) or ())
    for token in argv:
        stripped = str(token).strip("<@!>")
        if stripped.isdigit():
            return int(stripped)
    return int(getattr(req.actor, "user_id", 0) or 0)


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("economy.balance_view")):
        return

    @handler("economy.balance_view")
    async def balance_view(req) -> Reply:
        from sb.domain.economy import store

        target = _target_id(req)
        coins = await store.get_coins(target, int(req.guild_id or 0))
        return Reply(SUCCESS,
                     f"💰 <@{target}>'s wallet: **{coins:,}** 🪙")

    @handler("economy.joblist_view")
    async def joblist_view(req) -> Reply:
        from sb.domain.economy import catalogue, service, store

        uid, gid = int(getattr(req.actor, "user_id", 0) or 0), int(req.guild_id or 0)
        level = await service.active_level_reader()(uid, gid)
        inv = await store.get_inventory(uid, gid)
        tiers: dict[int, list[str]] = {}
        for name, data in catalogue.JOBS.items():
            tiers.setdefault(data["tier"], []).append(name)
        lines = ["📋 **All Jobs**"]
        for tier_num in sorted(tiers):
            lines.append(f"__Tier {tier_num}__")
            for name in tiers[tier_num]:
                data = catalogue.JOBS[name]
                times = await store.get_job_times(uid, gid, name)
                pay = catalogue.job_pay(name, times)
                unlocked = (level >= data["level"]
                            and all(item in inv and inv[item] > 0
                                    for item in data["items"]))
                lock = "✅" if unlocked else "🔒"
                req_parts = []
                if data["level"]:
                    req_parts.append(f"Lv{data['level']}")
                if data["items"]:
                    req_parts.append(", ".join(data["items"]))
                req_str = f" *(req: {', '.join(req_parts)})*" if req_parts else ""
                mastery = f" | mastery {times}/100" if times else ""
                lines.append(
                    f"{lock} {data['emoji']} "
                    f"**{name.replace('_', ' ').title()}** — {pay} 🪙 / "
                    f"work{req_str}{mastery}")
        lines.append(f"Your level: {level}  |  Pay shown includes mastery bonus.")
        return Reply(SUCCESS, "\n".join(lines))

    @handler("economy.work_view")
    async def work_view(req) -> Reply:
        from sb.domain.economy import catalogue, service
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        uid, gid = int(getattr(req.actor, "user_id", 0) or 0), int(req.guild_id or 0)
        argv = tuple(req.args.get("argv", ()) or ())
        if argv:                        # `!work <job>` — run the audited op
            result = await engine.run(
                WorkflowRef("economy.work"),
                _ctx_from_req(req, {"argv": argv}))
            if result.outcome != SUCCESS:
                return Reply(result.outcome,
                             result.user_message or "Could not work that job.")
            after = (result.after or {})
            job = str(after.get("work", {}).get("job", "")
                      if isinstance(after.get("work"), dict) else "") or "job"
            return Reply(SUCCESS, f"💼 Work complete — **{job}**. "
                                  f"{result.user_message or ''}".strip())
        available = await service.available_jobs(uid, gid)
        if not available:
            return Reply(BLOCKED,
                         "❌ No jobs available yet. Earn XP to unlock "
                         "higher-tier jobs or buy required items from `!shop`.")
        jobs = ", ".join(f"{catalogue.JOBS[j]['emoji']} `{j}`"
                         for j in available)
        return Reply(SUCCESS,
                     "💼 **Job Center** — pick a job with `!work <job>`.\n"
                     f"Available: {jobs}\n"
                     "Pay increases +1% each time you work the same job "
                     "(max +100%).")

    @handler("economy.shop_view")
    async def shop_view(req) -> Reply:
        from sb.domain.economy import catalogue

        lines = ["🛒 **Item Shop** — buy items to unlock higher-tier jobs."]
        for name, data in catalogue.SHOP_ITEMS.items():
            lines.append(f"{data['emoji']} "
                         f"**{name.replace('_', ' ').title()}** — "
                         f"{data['price']:,} 🪙 · {data['desc']}")
        lines.append("Purchases run through the shop panel "
                     "(the economy hub).")
        return Reply(SUCCESS, "\n".join(lines))

    @handler("economy.setlogchannel")
    async def setlogchannel(req) -> Reply:
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        argv = tuple(req.args.get("argv", ()) or ())
        if not argv:
            return Reply(BLOCKED, "Usage: `!setlogchannel #channel`")
        token = str(argv[0]).lstrip("<#").rstrip(">")
        if not token.isdigit():
            return Reply(BLOCKED, "That doesn't look like a channel mention.")
        result = await engine.run(
            WorkflowRef("settings.bind"),
            _ctx_from_req(req, {"subsystem": "economy", "name": "log_channel",
                                "kind": "channel", "resource_id": int(token)}))
        if result.outcome != SUCCESS:
            return Reply(result.outcome,
                         result.user_message or "Could not bind the channel.")
        return Reply(SUCCESS,
                     f"✅ Economy log channel set to <#{int(token)}>.")


_register()


def ensure_handler_refs() -> None:
    _register()
