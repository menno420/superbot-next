"""BTD6 handlers (band 7) — typed routes over the dataset, the strategy
lanes, and the reference views (shipped ``btd6ref`` / ``btd6strat`` /
``btd6events`` / ``btd6ops`` surfaces).

Live-ingestion-backed subcommands (events live/event/leaderboard/sources
/source-health/latest-data/refresh-source; ops readiness/runs/source
toggles/seed-data) are PENDING TERMINALS — the btd6 ingestion subsystem
(source registry + snapshots + supervisor + patch notes, oracle
migrations 040/048/054) is a named successor port (D-0046). The Ask
button/NL mention path is the K10 message shell (band-7 slice 3)."""

from __future__ import annotations

from dataclasses import dataclass

from sb.spec.outcomes import SUCCESS

__all__ = ["Reply", "ensure_handler_refs"]


@dataclass(frozen=True)
class Reply:
    outcome: str
    user_message: str


def _ok(text: str) -> Reply:
    return Reply(SUCCESS, text)


def _argv(req) -> list[str]:
    return [str(a) for a in tuple(req.args.get("argv", ()) or ())]


def _query(req) -> str:
    return " ".join(_argv(req)).strip() or str(req.args.get("name") or "").strip()


def _ctx_from_req(req, params: dict):
    from sb.kernel.workflow.context import WorkflowContext

    return WorkflowContext(
        actor=req.actor, guild_id=int(req.guild_id or 0),
        request_id=req.request_id, confirmed=req.confirmed, params=params)


# --- reference views (dataset-backed) ----------------------------------------------


async def ref_usage_view(req) -> Reply:
    return _ok(
        "**!btd6ref** — deterministic BTD6 reference.\n"
        "`tower <name>` · `hero <name>` · `round <n> [abr]` · "
        "`income <from> <to>` · `rbe <n> [abr]` · `relic <name>` · `ct`")


async def ref_tower_view(req) -> Reply:
    from sb.domain.btd6 import context, resolver

    query = _query(req)
    if not query:
        return _ok("Usage: `!btd6ref tower <name>` — e.g. `!btd6ref tower dart monkey`.")
    intent = resolver.resolve(query)
    if not intent.towers:
        return _ok(f"❓ No BTD6 tower matches **{query}**.")
    tower = intent.towers[0]
    facts = context._render_tower(tower)  # noqa: SLF001 — same-domain view reuse
    return _ok("\n".join(facts[:12]))


async def ref_hero_view(req) -> Reply:
    from sb.domain.btd6 import context, resolver

    query = _query(req)
    if not query:
        return _ok("Usage: `!btd6ref hero <name>` — e.g. `!btd6ref hero quincy`.")
    intent = resolver.resolve(query)
    if not intent.heroes:
        return _ok(f"❓ No BTD6 hero matches **{query}**.")
    facts = context._render_hero(intent.heroes[0])  # noqa: SLF001
    return _ok("\n".join(facts[:12]))


def _round_row(number: int, *, abr: bool) -> dict | None:
    from sb.domain.btd6 import dataset

    raw = dataset.read_blob("abr_rounds.json" if abr else "rounds.json") or {}
    for row in raw.get("rounds", ()):
        if int(row.get("round", -1)) == number:
            return row
    return None


def _round_args(req) -> tuple[int | None, bool]:
    argv = _argv(req)
    abr = any(a.lower() == "abr" for a in argv)
    for a in argv:
        if a.isdigit():
            return int(a), abr
    return None, abr


async def ref_round_view(req) -> Reply:
    number, abr = _round_args(req)
    if number is None:
        return _ok("Usage: `!btd6ref round <n> [abr]`.")
    row = _round_row(number, abr=abr)
    if row is None:
        return _ok(f"❓ No {'ABR ' if abr else ''}round {number} in the dataset.")
    label = "ABR " if abr else ""
    lines = [f"**{label}Round {number}** — {row.get('summary', '')}"]
    if row.get("danger"):
        lines.append(f"Danger: {row['danger']}")
    if row.get("rbe") is not None:
        lines.append(f"RBE: {row['rbe']:,}")
    if row.get("cash") is not None:
        lines.append(f"Round cash: ${row['cash']:,}")
    return _ok("\n".join(lines))


async def ref_income_view(req) -> Reply:
    argv = [a for a in _argv(req) if a.isdigit()]
    if len(argv) < 2:
        return _ok("Usage: `!btd6ref income <from> <to>` (inclusive).")
    start, end = int(argv[0]), int(argv[1])
    if not (1 <= start <= end <= 200):
        return _ok("Rounds must satisfy 1 ≤ from ≤ to ≤ 200.")
    total = 0
    missing: list[int] = []
    for n in range(start, end + 1):
        row = _round_row(n, abr=False)
        if row is None or row.get("cash") is None:
            missing.append(n)
        else:
            total += int(row["cash"])
    if missing:
        return _ok(
            f"❓ Rounds {missing[:5]} have no cash entry in the dataset — "
            "cannot total this range.")
    return _ok(
        f"**Round cash r{start}–r{end}** (inclusive, standard set): "
        f"${total:,} from pops/end-of-round (dataset round-cash column).")


async def ref_rbe_view(req) -> Reply:
    number, abr = _round_args(req)
    if number is None:
        return _ok("Usage: `!btd6ref rbe <n> [abr]`.")
    row = _round_row(number, abr=abr)
    if row is None or row.get("rbe") is None:
        return _ok(f"❓ No {'ABR ' if abr else ''}RBE for round {number}.")
    return _ok(
        f"**{'ABR ' if abr else ''}Round {number} RBE:** {row['rbe']:,} "
        f"— {row.get('summary', '')}")


async def ref_relic_view(req) -> Reply:
    from sb.domain.btd6 import dataset

    query = _query(req).lower()
    if not query:
        return _ok("Usage: `!btd6ref relic <name>`.")
    raw = dataset.read_blob("ct_relics.json") or {}
    for relic in raw.get("relics", ()):
        surfaces = {str(relic.get("canonical", "")).lower(),
                    str(relic.get("abbrev", "")).lower(),
                    *(str(a).lower() for a in relic.get("aliases", ()))}
        if query in surfaces:
            return _ok(
                f"**{relic.get('canonical')}** ({relic.get('category')} relic)"
                f" — {relic.get('effect', 'no effect text on record')}")
    return _ok(f"❓ No CT relic matches **{query}**.")


async def ref_ct_pending(req) -> Reply:
    return _ok(
        "🗺️ Live Contested Territory data (active map, tiles, team score) "
        "rides the BTD6 live-ingestion port — not armed yet. Static relic "
        "effects: `!btd6ref relic <name>`.")


# --- strategy views + routes --------------------------------------------------------


async def strat_usage_view(req) -> Reply:
    return _ok(
        "**!btd6strat** — strategy memory.\n"
        "`submit <title> | <summary>` · `mine` · `browse` · `pending` · "
        "`strategies` (published) · `strategy <id>` · `strategy-audit <id>` · "
        "`why-no-response`")


def _fmt_row(row: dict) -> str:
    status = row.get("approval_status", "?")
    extras = " · ".join(
        str(row[k]) for k in ("map", "mode", "hero") if row.get(k))
    return (f"**#{row['id']}** {row.get('title', '')} [{status}]"
            + (f" ({extras})" if extras else ""))


async def _strat_list(req, **filters) -> Reply:
    from sb.domain.btd6 import store

    rows = await store.list_strategies(**filters)
    if not rows:
        return _ok("No strategies on record for that filter yet — "
                    "`!btd6strat submit <title> | <summary>` adds one.")
    return _ok("\n".join(_fmt_row(r) for r in rows))


async def strat_browse_view(req) -> Reply:
    return await _strat_list(req, guild_id=int(req.guild_id or 0), limit=10)


async def strat_mine_view(req) -> Reply:
    return await _strat_list(
        req, guild_id=int(req.guild_id or 0),
        submitted_by=int(getattr(req.actor, "user_id", 0) or 0), limit=10)


async def strat_pending_view(req) -> Reply:
    return await _strat_list(
        req, guild_id=int(req.guild_id or 0),
        approval_status="pending", limit=5)


async def strat_published_view(req) -> Reply:
    return await _strat_list(req, visibility="published", limit=10)


async def strat_detail_view(req) -> Reply:
    from sb.domain.btd6 import store

    argv = [a for a in _argv(req) if a.isdigit()]
    if not argv:
        return _ok("Usage: `!btd6strat strategy <id>`.")
    row = await store.get_strategy(int(argv[0]))
    if not row:
        return _ok(f"❓ No strategy #{argv[0]} on record.")
    lines = [_fmt_row(row), row.get("summary", "")]
    if row.get("approved_by"):
        lines.append(f"Approved by: {row['approved_by']}")
    return _ok("\n".join(str(line) for line in lines if line))


async def strat_audit_view(req) -> Reply:
    argv = [a for a in _argv(req) if a.isdigit()]
    if not argv:
        return _ok("Usage: `!btd6strat strategy-audit <id>`.")
    return _ok(
        f"Audit for strategy #{argv[0]} rides the K7 central audit lane — "
        "every submit/review transition is an audited op row "
        "(verbs btd6_strategy_submitted / btd6_strategy_reviewed).")


async def strat_why_view(req) -> Reply:
    from sb.kernel.ai import decision_audit

    try:
        recent = await decision_audit.query(int(req.guild_id or 0), limit=25)
        rows = [r for r in recent
                if str((dict(r) if not isinstance(r, dict) else r)
                       .get("task", "")) == "btd6.answer"][:3]
    except Exception:  # noqa: BLE001 — diagnostics never crash the view
        rows = []
    if not rows:
        return _ok(
            "No recent `btd6.answer` decisions on record for this server — "
            "either nothing routed BTD6 yet, or the NL mention shell isn't "
            "armed (it rides the composition root).")
    lines = ["Recent `btd6.answer` decisions (newest first):"]
    for row in rows:
        r = dict(row) if not isinstance(row, dict) else row
        lines.append(
            f"- {r.get('decision', '?')} ({r.get('reason_code', '?')})")
    return _ok("\n".join(lines))


def _run_op(ref: str, params_fn):
    async def route(req) -> Reply:
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        result = await engine.run(WorkflowRef(ref), _ctx_from_req(req, params_fn(req)))
        message = (result.after or {}).get("message") if result.ok else None
        return Reply(SUCCESS if result.ok else result.outcome,
                     message or result.user_message or "Done.")
    return route


def _submit_params(req) -> dict:
    argv_text = " ".join(_argv(req)).strip()
    if not argv_text:
        argv_text = str(req.args.get("title") or "")
        summary = str(req.args.get("summary") or "")
        if summary:
            argv_text = f"{argv_text} | {summary}"
    title, _, summary = argv_text.partition("|")
    return {"title": title.strip(), "summary": summary.strip(),
            "map": req.args.get("map"), "mode": req.args.get("mode"),
            "hero": req.args.get("hero"),
            "_display_name": req.args.get("_display_name")}


def _review_params(req) -> dict:
    argv = _argv(req)
    strategy_id = next((int(a) for a in argv if a.isdigit()), 0)
    verdict = next(
        (a.lower() for a in argv
         if a.lower() in ("approved", "rejected", "unpublished")),
        str(req.args.get("approval_status") or ""))
    return {"strategy_id": strategy_id or req.args.get("strategy_id"),
            "approval_status": verdict, "approved_by": "staff",
            "notes": req.args.get("notes") or ""}


strat_submit_route = _run_op("btd6.submit_strategy", _submit_params)
strat_review_route = _run_op("btd6.review_strategy", _review_params)


# --- events / ops pending terminals -------------------------------------------------

_INGESTION_PENDING = (
    "📡 Live BTD6 event data (bosses, races, CT, odyssey, source health) "
    "comes from the Ninja Kiwi ingestion subsystem — a named successor "
    "port not armed in this build. The committed dataset (towers, heroes, "
    "bloons, rounds, bosses' static tables) answers through `!btd6ref` "
    "and the grounded NL path.")


async def events_pending(req) -> Reply:
    return _ok(_INGESTION_PENDING)


async def events_usage_view(req) -> Reply:
    return _ok(
        "**!btd6events** — live-event views (ingestion successor port): "
        "`live` · `event` · `leaderboard` · `sources` · `source-health` · "
        "`latest-data` · `refresh-source` — plus `grounding <question>` "
        "(works now: shows what the retrieval grounds).")


async def events_grounding_view(req) -> Reply:
    from sb.domain.btd6 import context

    question = _query(req)
    if not question:
        return _ok("Usage: `!btd6events grounding <question>`.")
    ctx = await context.build(question)
    if not ctx.facts:
        return _ok(
            f"No facts ground for that question (confidence "
            f"{ctx.confidence:.2f}) — the NL path would serve the "
            "version-stamped refusal.")
    shown = "\n".join(ctx.facts[:8])
    more = len(ctx.facts) - 8
    tail = f"\n… +{more} more fact(s)" if more > 0 else ""
    return _ok(
        f"**Grounded facts** (confidence {ctx.confidence:.2f}, source: "
        f"{ctx.source_summary}):\n{shown}{tail}")


async def ops_usage_view(req) -> Reply:
    return _ok(
        "**!btd6ops** — ingestion operations (successor port): "
        "`readiness` · `runs` · `source_enable` · `source_disable` · "
        "`seed-data`. " + _INGESTION_PENDING)


async def ops_pending(req) -> Reply:
    return _ok(_INGESTION_PENDING)


# --- ref table ----------------------------------------------------------------------

_HANDLERS = (
    ("btd6.ref_usage_view", ref_usage_view),
    ("btd6.ref_tower_view", ref_tower_view),
    ("btd6.ref_hero_view", ref_hero_view),
    ("btd6.ref_round_view", ref_round_view),
    ("btd6.ref_income_view", ref_income_view),
    ("btd6.ref_rbe_view", ref_rbe_view),
    ("btd6.ref_relic_view", ref_relic_view),
    ("btd6.ref_ct_pending", ref_ct_pending),
    ("btd6.strat_usage_view", strat_usage_view),
    ("btd6.strat_browse_view", strat_browse_view),
    ("btd6.strat_mine_view", strat_mine_view),
    ("btd6.strat_pending_view", strat_pending_view),
    ("btd6.strat_published_view", strat_published_view),
    ("btd6.strat_detail_view", strat_detail_view),
    ("btd6.strat_audit_view", strat_audit_view),
    ("btd6.strat_why_view", strat_why_view),
    ("btd6.strat_submit_route", strat_submit_route),
    ("btd6.strat_review_route", strat_review_route),
    ("btd6.events_usage_view", events_usage_view),
    ("btd6.events_pending", events_pending),
    ("btd6.events_grounding_view", events_grounding_view),
    ("btd6.ops_usage_view", ops_usage_view),
    ("btd6.ops_pending", ops_pending),
)


def ensure_handler_refs() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    for name, fn in _HANDLERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)
