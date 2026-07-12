"""The ai POLICY SCOPE PICKERS (band 7, the policy-mutation slice) — the
shipped views/ai/policy/* write/read flows (@7f7628e1) on this engine:

* channel/category/role — the shipped two-step pick → modal flow
  (channel_view.py / category_view.py / role_view.py): the picker page's
  select swaps the anchor to the scope's EDIT page (a native
  ChannelSelect/RoleSelect pick cannot open a modal on this engine — a
  selector pick is AUTO-deferred before its handler runs, so the Edit…
  button intermediates, the D-0054/D-0066 posture), the Edit… button
  ISSUES the shipped ChannelPolicyModal/RolePolicyModal twin (G-10), and
  the submit writes ONE audited ``ai.set_*_policy`` op (K7: scoped upsert
  + the shipped bump_generation in one transaction, central audit,
  advisory ``ai.policy.*_changed`` after commit) — the shipped acks and
  guard bytes verbatim.
* preview — the shipped preview_view.py channel pick → the dual dry-run
  effective-policy embed (title "AI policy preview", no Context field —
  the chooser path never built the snapshot).
* list — the shipped list_view.py paged override list over the three
  typed tables (Prev/Next, 10 per page, the shipped empty-state copy).

The pickers' option rosters ride an installable guild-scope port (the
ai_operator_ports precedent): the live root installs a discord-backed
reader; uninstalled (replay/DB-free) the selects degrade to their
empty_state — never a crash. The CHANNEL pickers ride the
Discord-NATIVE channel select (wire type 8 — the #167 lane; the shipped
ChannelSelect shape exactly); the category/role rosters render as engine
string selects capped at 25 options (native category/role selects have
no engine twin yet — ledgered in D-0070).

Registered at MODULE IMPORT (the BUG A rule)."""

from __future__ import annotations

import dataclasses
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sb.kernel.interaction.handler_kit import Reply, ctx_from_request
from sb.spec.outcomes import SUCCESS

logger = logging.getLogger("sb.domain.ai.policy_widgets")

__all__ = [
    "GuildScopeRoster",
    "PolicyEntry",
    "build_list_fields",
    "collect_entries",
    "ensure_policy_widget_refs",
    "install_guild_scope_roster",
]

#: the shipped roster tuples (chooser copy + modal validation agree).
_VALID_MODES = ("inherit", "always_reply", "mention_only", "disabled")
_VALID_DECISIONS = ("allow", "deny", "inherit")

_TRUE_TOKENS = frozenset({"yes", "y", "true", "1", "on"})
_FALSE_TOKENS = frozenset({"no", "n", "false", "0", "off", ""})

#: shipped guard bytes (chooser.py / preview_view.py / the scope modals).
_NEEDS_GUILD_EDIT = "❌ Edit requires a guild context."
_NEEDS_GUILD_PREVIEW = "❌ Preview requires a guild context."
_NEEDS_GUILD_LIST = "❌ Listing overrides requires a guild context."

_PER_PAGE = 10


# --- the guild scope roster port (channel/category/role enumeration) ----------------


@dataclass(frozen=True)
class GuildScopeRoster:
    """One guild's pickable scopes: ``text_channels`` are
    ``(id, name, category_id)`` triples, ``categories`` / ``roles`` are
    ``(id, name)`` pairs."""

    text_channels: tuple[tuple[int, str, int | None], ...] = ()
    categories: tuple[tuple[int, str], ...] = ()
    roles: tuple[tuple[int, str], ...] = ()


GuildScopeRosterReader = Callable[[int], Awaitable[GuildScopeRoster | None]]

_roster_reader: GuildScopeRosterReader | None = None


def install_guild_scope_roster(reader: GuildScopeRosterReader) -> None:
    global _roster_reader
    _roster_reader = reader


async def _roster(guild_id: int) -> GuildScopeRoster:
    if _roster_reader is None:
        return GuildScopeRoster()
    try:
        return (await _roster_reader(int(guild_id))) or GuildScopeRoster()
    except Exception:  # noqa: BLE001 — a roster miss degrades to empty_state
        logger.debug("guild scope roster read failed", exc_info=True)
        return GuildScopeRoster()


# --- the picker option providers -----------------------------------------------------


async def policy_category_options(ctx):
    roster = await _roster(int(ctx.guild_id or 0))
    return tuple({"label": str(name)[:100], "value": str(cid)}
                 for cid, name in roster.categories)


async def policy_role_options(ctx):
    roster = await _roster(int(ctx.guild_id or 0))
    return tuple({"label": f"@{name}"[:100], "value": str(rid)}
                 for rid, name in roster.roles)


# --- shipped validators (channel_view._parse_optional_int / role_view._parse_bool) ---


def _parse_optional_int(raw: str, *, field: str, minimum: int = 0) -> int | None:
    """Blank = None (clear the override); non-int / below-minimum raise the
    shipped typed sentences."""
    cleaned = (raw or "").strip()
    if not cleaned:
        return None
    try:
        value = int(cleaned)
    except ValueError as exc:
        raise ValueError(
            f"{field}: must be an integer (got {cleaned!r})") from exc
    if value < minimum:
        raise ValueError(f"{field}: must be >= {minimum} (got {value})")
    return value


def _parse_bool(raw: str, *, field: str) -> bool:
    cleaned = (raw or "").strip().lower()
    if cleaned in _TRUE_TOKENS:
        return True
    if cleaned in _FALSE_TOKENS:
        return False
    raise ValueError(f"{field}: expected yes/no (got {cleaned!r})")


# --- shared handler plumbing ----------------------------------------------------------


def _picked(req) -> str:
    values = tuple(req.args.get("values", ()) or ())
    return str(values[0]) if values else ""


async def _open_page(req, panel_id: str, extra: dict) -> None:
    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    args = {**dict(req.args or {}), **extra}
    await open_panel(PanelRef(panel_id), dataclasses.replace(req, args=args))


async def _run_policy_op(req, op_key: str, params: dict):
    from sb.kernel.workflow import engine
    from sb.spec.refs import WorkflowRef

    # the shipped mutation seam minted a uuid per write and carried it on
    # the advisory event (ai_policy_mutation mutation_id).
    params = {**params, "mutation_id": uuid.uuid4().hex}
    return await engine.run(WorkflowRef(op_key),
                            ctx_from_request(req, params))


def _generation(result) -> int:
    after = (result.after or {}).get("policy_write") or {}
    try:
        return int(after.get("generation") or 0)
    except (TypeError, ValueError):
        return 0


async def _label_for(guild_id: int, scope: str, target_id: int) -> str:
    """The pick's display label: channel/role mentions render from the id;
    a category needs its NAME (shipped `**{category.name}**`) — roster
    lookup, raw id fallback."""
    if scope == "channel":
        return f"<#{target_id}>"
    if scope == "role":
        return f"<@&{target_id}>"
    roster = await _roster(guild_id)
    for cid, name in roster.categories:
        if int(cid) == int(target_id):
            return str(name)
    return str(target_id)


# --- the scope picks (select → edit page) ----------------------------------------------


async def policy_channel_pick(req) -> None:
    target = _picked(req)
    await _open_page(req, "ai.policy_scope_edit", {
        "policy_scope": "channel", "policy_target": target,
        "policy_target_label": f"<#{target}>"})
    return None


async def policy_category_pick(req) -> None:
    target = _picked(req)
    label = await _label_for(int(req.guild_id or 0), "category",
                             int(target or 0))
    await _open_page(req, "ai.policy_scope_edit", {
        "policy_scope": "category", "policy_target": target,
        "policy_target_label": label})
    return None


async def policy_role_pick(req) -> None:
    target = _picked(req)
    await _open_page(req, "ai.policy_role_edit", {
        "policy_target": target,
        "policy_target_label": f"<@&{target}>"})
    return None


async def policy_preview_pick(req) -> Reply | None:
    """The shipped preview pick — the dual dry-run embed for the PICKED
    channel (preview_view._PreviewChannelSelect.callback: title
    'AI policy preview', no Context field on the chooser path)."""
    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_PREVIEW)
    from sb.domain.ai import operator_cards as cards

    target = int(_picked(req) or 0)
    roster = await _roster(int(req.guild_id))
    category_id = next((cat for cid, _name, cat in roster.text_channels
                        if int(cid) == target), None)
    embed = await cards.build_policy_embed(
        guild_id=int(req.guild_id), channel_id=target,
        user_id=int(getattr(req.actor, "user_id", 0) or 0),
        user_role_ids=tuple(getattr(req.actor, "role_ids", ()) or ()),
        title="AI policy preview", category_id=category_id,
        include_context=False)
    from sb.domain.ai.service import card_panel_id

    # the preview pick is COMPONENT ingress -> the card carries the
    # family "AI home" back-route (VERDICT 009 AIP-02 consumption).
    await _open_page(req, card_panel_id(req), {"_card": embed})
    return None


# --- the list page ----------------------------------------------------------------------


@dataclass(frozen=True)
class PolicyEntry:
    """One row in the unified override list (shipped list_view.PolicyEntry)."""

    scope: str          # "channel" / "category" / "role"
    target_id: int
    summary: str


def _channel_entry_summary(row: dict) -> str:
    parts = [f"mode=`{row.get('mode')}`"]
    if row.get("min_level") is not None:
        parts.append(f"min_level=`{row['min_level']}`")
    if row.get("cooldown_seconds") is not None:
        parts.append(f"cooldown=`{row['cooldown_seconds']}s`")
    return " · ".join(parts)


def _role_entry_summary(row: dict) -> str:
    parts = [f"decision=`{row.get('decision')}`"]
    if row.get("min_level_override") is not None:
        parts.append(f"min_level_override=`{row['min_level_override']}`")
    if row.get("bypass_cooldown"):
        parts.append("bypass_cooldown=`yes`")
    return " · ".join(parts)


async def collect_entries(guild_id: int) -> list[PolicyEntry]:
    """The shipped collect_entries: channel → category → role, PK order
    within a scope (fail-safe empty on a store read miss — replay/DB-free
    posture; the live drive proves the row-bearing reads)."""
    from sb.domain.ai import policy_store as store

    entries: list[PolicyEntry] = []
    try:
        for row in await store.list_channel_policies(guild_id):
            entries.append(PolicyEntry("channel", int(row["channel_id"]),
                                       _channel_entry_summary(row)))
        for row in await store.list_category_policies(guild_id):
            entries.append(PolicyEntry("category", int(row["category_id"]),
                                       _channel_entry_summary(row)))
        for row in await store.list_role_policies(guild_id):
            entries.append(PolicyEntry("role", int(row["role_id"]),
                                       _role_entry_summary(row)))
    except Exception:  # noqa: BLE001 — degrade to the empty-state page
        logger.debug("policy list read failed", exc_info=True)
        return []
    return entries


def _format_target(scope: str, target_id: int) -> str:
    if scope == "channel":
        return f"<#{target_id}>"
    if scope == "category":
        return f"📁 `{target_id}`"
    if scope == "role":
        return f"<@&{target_id}>"
    return f"`{target_id}`"


def _scope_emoji(scope: str) -> str:
    return {"channel": "🔵", "category": "📁", "role": "👥"}.get(scope, "·")


def build_list_fields(entries: list[PolicyEntry], *,
                      page: int) -> tuple[tuple, int, int]:
    """(fields, clamped_page, total_pages) — the shipped build_list_embed
    field rows verbatim."""
    total = len(entries)
    total_pages = max(1, (total + _PER_PAGE - 1) // _PER_PAGE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * _PER_PAGE
    slice_ = entries[start:start + _PER_PAGE]
    if not entries:
        fields = ((
            "No overrides",
            "The guild uses only the baseline `ai_guild_policy` row. "
            "Use the Policy chooser to add channel / category / role "
            "overrides.", False),)
    else:
        fields = tuple(
            (f"{_scope_emoji(e.scope)} {e.scope}",
             f"{_format_target(e.scope, e.target_id)} · {e.summary}", False)
            for e in slice_)
    return fields, page, total_pages


async def policy_list_open(req) -> Reply | None:
    """The chooser's List overrides click (shipped list_btn — the guild
    guard byte verbatim, then the page-1 list on the anchor)."""
    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_LIST)
    await _open_page(req, "ai.policy_list", {"policy_page": 1})
    return None


async def policy_list_page(req) -> None:
    """Prev/Next — the shipped clamped page-turn re-rendered in place."""
    try:
        page = int(req.args.get("policy_page") or 1)
    except (TypeError, ValueError):
        page = 1
    action = str(req.args.get("session_action") or "")
    page = page - 1 if action == "list_prev" else page + 1
    await _open_page(req, "ai.policy_list", {"policy_page": max(1, page)})
    return None


# --- the G-10 form submits ----------------------------------------------------------------


async def policy_mode_submit(req) -> Reply:
    """ChannelPolicyModal/CategoryPolicyModal.on_submit, verbatim order:
    guild guard → mode roster → optional-int parses → the audited scoped
    op → the shipped ack with the '(generation N)' tail. The scope/target
    params arrive through the kernel modal-args stash (the Edit… click's
    session args)."""
    scope = str(req.args.get("policy_scope") or "")
    target = str(req.args.get("policy_target") or "")
    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_EDIT)
    if scope not in ("channel", "category") or not target.isdigit():
        # a stash miss (restart/eviction) leaves the fields bare — the
        # guard answers, never a write.
        return Reply(SUCCESS, _NEEDS_GUILD_EDIT)
    mode = str(req.args.get("mode") or "").strip()
    if mode not in _VALID_MODES:
        return Reply(SUCCESS, "❌ mode must be one of: "
                     + ", ".join(f"`{m}`" for m in _VALID_MODES))
    try:
        min_level = _parse_optional_int(
            str(req.args.get("min_level") or ""), field="min_level")
        cooldown_seconds = _parse_optional_int(
            str(req.args.get("cooldown_seconds") or ""),
            field="cooldown_seconds")
    except ValueError as exc:
        return Reply(SUCCESS, f"❌ {exc}")

    label = str(req.args.get("policy_target_label") or target)
    if scope == "channel":
        op_key, id_key = "ai.set_channel_policy", "channel_id"
        subject = label
    else:
        op_key, id_key = "ai.set_category_policy", "category_id"
        subject = f"category **{label}**"
    result = await _run_policy_op(req, op_key, {
        id_key: int(target), "mode": mode, "min_level": min_level,
        "cooldown_seconds": cooldown_seconds})
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     f"❌ Couldn't update AI policy for {subject}: "
                     f"{result.user_message or 'write failed'}.")
    bits = [f"mode=`{mode}`"]
    if min_level is not None:
        bits.append(f"min_level=`{min_level}`")
    if cooldown_seconds is not None:
        bits.append(f"cooldown=`{cooldown_seconds}s`")
    return Reply(SUCCESS,
                 f"✅ Updated AI policy for {subject} · "
                 + " · ".join(bits)
                 + f" (generation {_generation(result)}).")


async def policy_role_submit(req) -> Reply:
    """RolePolicyModal.on_submit, verbatim order: guild guard → decision
    roster (lowercased, the shipped .strip().lower()) → optional-int +
    yes/no parses → the audited op → the shipped ack (bypass_cooldown is
    ALWAYS in the ack tail)."""
    target = str(req.args.get("policy_target") or "")
    if not req.guild_id:
        return Reply(SUCCESS, _NEEDS_GUILD_EDIT)
    if not target.isdigit():
        return Reply(SUCCESS, _NEEDS_GUILD_EDIT)
    decision = str(req.args.get("decision") or "").strip().lower()
    if decision not in _VALID_DECISIONS:
        return Reply(SUCCESS, "❌ decision must be one of: "
                     + ", ".join(f"`{d}`" for d in _VALID_DECISIONS))
    try:
        min_level_override = _parse_optional_int(
            str(req.args.get("min_level_override") or ""),
            field="min_level_override")
        bypass_cooldown = _parse_bool(
            str(req.args.get("bypass_cooldown") or ""),
            field="bypass_cooldown")
    except ValueError as exc:
        return Reply(SUCCESS, f"❌ {exc}")

    label = str(req.args.get("policy_target_label") or f"<@&{target}>")
    result = await _run_policy_op(req, "ai.set_role_policy", {
        "role_id": int(target), "decision": decision,
        "min_level_override": min_level_override,
        "bypass_cooldown": bypass_cooldown})
    if result.outcome != SUCCESS:
        return Reply(result.outcome,
                     f"❌ Couldn't update AI policy for {label}: "
                     f"{result.user_message or 'write failed'}.")
    bits = [f"decision=`{decision}`"]
    if min_level_override is not None:
        bits.append(f"min_level_override=`{min_level_override}`")
    bits.append(f"bypass_cooldown=`{bypass_cooldown}`")
    return Reply(SUCCESS,
                 f"✅ Updated AI policy for {label} · "
                 + " · ".join(bits)
                 + f" (generation {_generation(result)}).")


# --- registration — MODULE IMPORT (BUG A rule) ---------------------------------------------

_HANDLERS = (
    ("ai.policy_channel_pick", policy_channel_pick),
    ("ai.policy_category_pick", policy_category_pick),
    ("ai.policy_role_pick", policy_role_pick),
    ("ai.policy_preview_pick", policy_preview_pick),
    ("ai.policy_list_open", policy_list_open),
    ("ai.policy_list_page", policy_list_page),
    ("ai.policy_mode_submit", policy_mode_submit),
    ("ai.policy_role_submit", policy_role_submit),
)

_PROVIDERS = (
    ("ai.policy_category_options", policy_category_options),
    ("ai.policy_role_options", policy_role_options),
)


def _register() -> None:
    from sb.spec.refs import (
        HandlerRef,
        ProviderRef,
        handler,
        is_registered,
        provider,
    )

    for name, fn in _HANDLERS:
        if not is_registered(HandlerRef(name)):
            handler(name)(fn)
    for name, fn in _PROVIDERS:
        if not is_registered(ProviderRef(name)):
            provider(name)(fn)


_register()


def ensure_policy_widget_refs() -> None:
    _register()
