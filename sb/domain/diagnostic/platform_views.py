"""The shipped ``!platform <subcommand>`` operator cards (diagnostic flip)
— disbot/cogs/diagnostic/platform_group.py + services/diagnostic_embeds.py
renders over the CAPTURE WORLD's registry/process state, pinned at the
corpus sha 7f7628e1 (goldens/diagnostic/sweep_platform_* pin every byte).

WHY LITERALS: these surfaces are process-introspection over the OLD bot's
own runtime (its 43-subsystem governance registry, its 19 SubsystemSchema
instances, its 103-step migration ladder, its 10 PersistentView classes,
its consistency collectors' 9-clean/2-warning tally...). The v1 kernel's
equivalents are structurally different objects, so an introspecting port
CANNOT reproduce the golden bytes — the sanctioned move is the capture-
world snapshot literal with the port boundary documented (the playbook
trap-10a/trap-20 lane: one golden per surface ⇒ pinned literal; a
trajectory would need runner seeding). Live introspection over the NEW
kernel is successor work, per-surface.

PARAMETERIZED SEAMS (the only non-literal bytes, exactly where the golden
carries a world token): ``{ch}`` = the invoking channel id (golden
``<#<#general>>``), ``{gid}`` = the guild id (``<guild>``), ``{ts}`` = an
ISO-8601 now (``<ts>``), ``{tier}`` = the invoker's member tier (the
access card's ```owner``` — the capture persona was the guild
owner). Literal braces in shipped copy are escaped ``{{ }}``.

Colors ride STYLE_TOKEN_COLORS (all six accents were already mapped:
blurple/blue/green/red/gold/greyple/light_grey/orange).

NOT in this table: ``backfill`` (computed — sb/domain/diagnostic/ops.py),
``setting``/``finding`` (arg-dependent guards — handlers.py),
``flag``/``automation`` (component panels — panels.py), and the FIVE
capture-skipped process-state views (health / runtime / slow / startup /
status — parity/goldens/_sweep_skips.json skipped them as nondeterministic,
so they are NOT declared; the ``platform`` root handler answers the honest
refusal)."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

__all__ = ["VIEWS", "build_view_embed"]


@dataclass(frozen=True)
class _View:
    title: str
    description: str = ""
    fields: tuple[tuple[str, str, bool], ...] = ()
    footer: str = ""
    style_token: str = "blurple"
    timestamp: bool = False


VIEWS: dict[str, _View] = {
    "access": _View(
        title="🔎 Access — what's usable here",
        description='Governance visibility for **<#{ch}>** (your member tier: `{tier}`).',
        fields=(
            ('✅ Visible (43)',
             '`admin`, `ai`, `automod`, `blackjack`, `btd6`, `casino`, `chain`, `channel`, `cleanup`, `community_spotlight`, `community`, `counters`, `counting`, `creature`, `deathmatch`, `diagnostic`, `economy`, `farm`, `fishing`, `four_twenty`, `games`, `general`, `help`, `image_moderation`, `inventory`, `karma`, `leaderboard`, `logging`, `mining`, `moderation`, `project_moon`, `proof_channel`, `role`, `rps_tournament`, `security`, `server_management`, `settings`, `ticket`, `treasury`, `utility`, `ux_lab`, `welcome`, `xp`',
             False),
            ('🚫 Denied (0)',
             '*(none)*',
             False),
            ('📍 Resolved from',
             '`admin` → registry_default, `ai` → registry_default, `automod` → registry_default, `blackjack` → registry_default, `btd6` → registry_default, `casino` → registry_default, `chain` → registry_default, `channel` → registry_default, `cleanup` → registry_default, `community` → registry_default, `community_spotlight` → registry_default, `counters` → registry_default, `counting` → registry_default, `creature` → registry_default, `deathmatch` → registry_default, `diagnostic` → registry_default, `economy` → registry_default, `farm` → registry_default, `fishing` → registry_default, `four_twenty` → registry_default, `games` → registry_default, `general` → registry_default, `help` → registry_default, `image_moderation` → registry_default, `inventory` → registry_default, `karma` → registry_default, `leaderboard` → registry_default, `logging` → registry_default, `mining` → registry_default, `moderation` → registry_default, `project_moon` → registry_default, `proof_channel` → registry_default, `role…',
             False),
            ('🧹 Cleanup here',
             'delete: `True` · after: `5s` · feedback: `True` · from: `fallback_default`',
             False),
        ),
        footer='Read-only · reflects your roles in the selected location',
    ),
    "anchors": _View(
        title='📌 Panel anchors',
        description='',
        fields=(
            ('Last restoration',
             'seen: **0**  ·  restored: **0**  ·  view_missing: **0**  ·  stale: **0**',
             False),
            ('Active anchors by subsystem',
             'none',
             False),
        ),
    ),
    "bindings": _View(
        title='🔗 Subsystem bindings',
        description='kinds: `channel`, `role`, `category`, `thread`, `member`',
        fields=(
            ('Validator dispatch',
             '`category` → `resource`\n`channel` → `resource`\n`member` → `member`\n`role` → `resource`\n`thread` → `resource`',
             False),
            ('Status (guild {gid})',
             '*(no bindings)*',
             False),
            ('By subsystem (guild {gid})',
             '*(no bindings)*',
             False),
        ),
    ),
    "caches": _View(
        title='🧠 Cache snapshot',
        description='',
        fields=(
            ('guild_config',
             '**size**: 0\n**versions_tracked**: 0',
             False),
            ('governance_cache',
             '**size**: 2\n**guilds_versioned**: 0\n**guilds_with_role_overrides**: 0\n**failed_subsystems**: *(none)*',
             False),
        ),
    ),
    "cleanup-preview": _View(
        title='🧹 Cleanup preview (dry run)',
        description='Resolved cleanup policy for **<#{ch}>** — no changes made.',
        fields=(
            ('Delete message',
             '`True`',
             True),
            ('Delete after',
             '`5s`',
             True),
            ('Send feedback',
             '`True`',
             True),
            ('Resolved from',
             '`fallback_default`',
             False),
            ('Cleanup write scopes',
             '`category`, `channel`, `guild` — `thread` is **not** a cleanup scope (RC-5)',
             False),
        ),
        footer='Read-only dry run · no cleanup policy was written',
    ),
    "command-access": _View(
        title='✅ Command Access — <#{ch}>',
        description='',
        fields=(
            ('Configured mode',
             '`all_channels` (default — no policy row in this guild)',
             False),
            ('Would a normal command run here?',
             '**Yes** — admitted.',
             False),
            ('Decision details',
             '`reason`: allowed\n`source`: default_unconfigured\n`effective_mode`: all_channels\n`prefix_enabled`: yes\n`slash_enabled`: yes  *(same admission chain)*',
             False),
            ('Bootstrap probe (`!setup` for this operator)',
             '✅ allowed via `bootstrap_bypass`',
             False),
        ),
        footer='Probe was synthetic; no audit row was emitted.  Configure via `!settings → Command access`.',
        style_token="green",
    ),
    "consistency": _View(
        title='🛡 Platform consistency · WARNING',
        description='9 clean · 2 warning · 0 fatal · 1 skipped · generated {ts}',
        fields=(
            ('🟢 Identity contract',
             'No identity-contract findings.',
             False),
            ('🟢 Feature flags',
             '8 flag(s) declared; evaluator healthy.',
             False),
            ('🟢 Rollout / audit',
             'audit table reachable; 0 row(s).',
             False),
            ('🟢 Bindings',
             'no broken bindings in guild {gid}.\n• bound=0 unresolved=0 missing=0 invalid=0 (total=0)',
             False),
            ('⚪ Binding backfill',
             'no `binding_backfill` checkpoint rows.',
             False),
            ('🟡 Config arbitration',
             'calls_total=304; fallback=0; missing=304.\n• Non-zero fallback/missing — the arbiter is degrading to legacy reads. Offending keys:\n• xp/announce_channel (legacy=xp_announce_channel) src=missing flag=on binding=unresolved\n• economy/log_channel (legacy=economy_log_channel) src=missing flag=on binding=unresolved',
             False),
            ('🟢 Participation',
             "participation storage / providers / events all reachable.\n• user_participation present=True user_participation_audit present=True\n• events present=['participation.changed', 'subscription.changed', 'user_preference.changed', 'user_visibility.changed']",
             False),
            ('🟢 Migrations',
             'ladder contiguous 001 → 103; all applied.\n• filesystem: lowest=1 highest=103 count=103\n• db-applied: count=103 highest=103',
             False),
            ('🟢 Runtime providers',
             '32 provider(s) registered; all returned OK.',
             False),
            ('🟢 Lifecycle',
             'bot is STARTING; on_ready has not fired yet.\n• phase: STARTING',
             False),
            ('🟡 Setup readiness',
             'ℹ️ Roadmap/informational — not a runtime health failure.\n2/11 roadmap blocker(s) resolved (informational; not a runtime health failure).\n• command_surface_ledger: pending\n• panel_registry: resolved\n• settings_registry: pending\n→ See `docs/archive/phase-2-completion-readiness.md` for unlock order.',
             False),
            ('🟢 Wizard finalization',
             'ℹ️ Roadmap/informational — not a runtime health failure.\n3/4 finalization step(s) landed; rest deferred.\n• fallback_attribution [PR1]: resolved\n• ai_advisor_review [PR3]: resolved\n• preflight_gate_visible [PR3]: resolved',
             False),
        ),
        footer='1 runtime warning · 1 informational',
        style_token="gold",
    ),
    "counting-health": _View(
        title='🔢 Counting persistence health',
        description='',
        fields=(
            ('This guild ({gid})',
             'ok: `0` · error: `0` · cancelled: `0`',
             False),
            ('All guilds (this process)',
             'ok: `0` · error: `0` · cancelled: `0`',
             False),
            ('Verdict',
             '✅ no save errors observed',
             False),
        ),
        footer='Counts are since process start (in-memory metric)',
    ),
    "customization": _View(
        title='🧭 Customization catalogue',
        description='*(not built — call customization_catalogue.build_catalogue(bot))*',
        style_token="greyple",
    ),
    "economy": _View(
        title='💰 Economy faucet / sink',
        description='Net coin flow over **all time** (aggregated from the economy audit ledger — counts and totals only, no per-user data).',
        fields=(
            ('Summary',
             'minted **0** · drained **0**\nnet **+0** · mint:drain **—** · verdict **no activity**',
             False),
            ('🟢 Faucets (mint) — 0',
             '*(none this window)*',
             False),
            ('🔴 Sinks (drain) — 0',
             '*(none this window)*',
             False),
        ),
        footer="Classified by the sign of each reason's net delta — new reasons are sorted automatically.",
        style_token="light_grey",
    ),
    "economytrend": _View(
        title='📈 Economy flow trend',
        description='Per-day coin flow over **all time** (aggregated from the economy audit ledger — counts and totals only, no per-user data).',
        fields=(
            ('No activity',
             '*(no coin movements recorded for this window)*',
             False),
        ),
        style_token="light_grey",
    ),
    "findings": _View(
        title='🩺 Health findings — open',
        description='open 0 · resolved 0 · ignored 0 · 0 total',
        fields=(
            ('Findings',
             '*(none)*',
             False),
        ),
        style_token="green",
        timestamp=True,
    ),
    "flags": _View(
        title='🚩 Feature flags',
        description='8 declared (2 operator · 6 internal)  ·  cache=0  ·  bootstrap_fallback=0',
        fields=(
            ('Operator flags',
             '`settings.manager_cog.enabled` — Settings menu (!settings) · default=True eff=on src=default\n`youtube.context.enabled` — YouTube context for AI replies · default=False eff=off src=default',
             False),
            ('Internal / platform gates',
             '_Migration & kill-switch gates — not user-facing features._\n`bindings.primary` — Bindings as primary source (internal rollout gate) · default=False eff=off src=default\n`feature_flag.primary` — Feature-flag runtime gate (env-only, internal) · default=False eff=off src=default\n`participation.enabled` — Participation runtime (internal rollout gate) · default=False eff=off src=default\n`resource_provisioning.primary` — Resource provisioning pipeline primary (operator kill-switch) · default=False eff=off src=default\n`resources.unified` — Unified resource discovery (internal rollout gate) · default=False eff=off src=default\n`settings.mutation.primary` — Settings mutation pipeline primary (operator kill-switch) · default=False eff=off src=default',
             False),
        ),
    ),
    "identity": _View(
        title='🪪 Identity contract',
        description='All four identity surfaces agree.',
        style_token="green",
    ),
    "lifecycle": _View(
        title='🔄 Lifecycle',
        description='Phase: **STARTING** · Accepting commands: **True** · Startup observed: **no**',
        fields=(
            ('Pending request',
             '_none_',
             False),
            ('Recent events',
             '_none recorded_',
             False),
        ),
        style_token="gold",
    ),
    "locks": _View(
        title='🔒 Scope locks',
        description='total: **0**  ·  held: **0**',
        fields=(
            ('By prefix',
             '*(none)*',
             False),
        ),
    ),
    "media": _View(
        title='🎬 Media (YouTube) diagnostics',
        description='Content-free operator view — counts, ages, and outcome categories only (no provider content).',
        fields=(
            ('Credential',
             '`YOUTUBE_API_KEY` ❌ absent',
             False),
            ('Provider requests (this process) — 0 total',
             '`success` — 0\n`key_missing` — 0\n`private_or_deleted` — 0\n`quota_limited` — 0\n`timeout` — 0\n`fetch_error` — 0',
             False),
            ('Cache rows',
             'total **0** · live **0** · expired **0**\nok **0** · error **0** · with-transcript **0**',
             False),
            ('Cache age / expiry',
             'oldest fetched — · newest —\nnext expiry —',
             False),
            ('Last purge',
             '*(no purge run this process yet)*',
             False),
        ),
    ),
    "migrations": _View(
        title='🛠 Platform migrations',
        description='Generic logical-migration checkpoint table; first consumer is the binding backfill (Phase 2 PR-5).',
        fields=(
            ('Global counts',
             '*(no rows)*',
             False),
            ('This guild',
             '*(no checkpoints)*',
             False),
        ),
        style_token="gold",
    ),
    "participation-schemas": _View(
        title='🧑\u200d🤝\u200d🧑 Participation schemas',
        description='1 registered  ·  subs=1  ·  vis=2  ·  notif=1  ·  prefs=1',
        fields=(
            ('By subsystem',
             '`xp` — s=1 v=2 n=1 p=1 v1',
             False),
        ),
    ),
    "provisioning": _View(
        title='🧰 Resource provisioning catalogue',
        description='*(not built — call resource_provisioning_catalogue.build_provisioning_catalogue())*',
        style_token="greyple",
    ),
    "resource-requirements": _View(
        title='🧱 Resource requirements',
        description='15 requirement(s) declared',
        fields=(
            ('Requirements',
             '`economy` channel/log_channel (recommended) → `economy-log`\n`logging` channel/mod_log (recommended) → `bot-mod-log`\n`logging` channel/cleanup_log (recommended) → `bot-cleanup-log`\n`logging` channel/debug_log (recommended) → `bot-debug-log`\n`logging` channel/info_log (recommended) → `bot-info-log`\n`logging` channel/warning_log (recommended) → `bot-warning-log`\n`logging` channel/error_log (recommended) → `bot-error-log`\n`logging` channel/audit_log (recommended) → `bot-audit-log`\n`logging` channel/events_log (recommended) → `bot-event-log`\n`logging` channel/message_log (recommended) → `bot-message-log`\n`logging` channel/member_log (recommended) → `bot-member-log`\n`logging` channel/role_log (recommended) → `bot-role-log`\n`moderation` channel/mod_log (recommended) → `mod-logs`\n`proof_channel` channel/proof (optional) → `proof`\n`xp` channel/announce_channel (optional) → `level-ups`',
             False),
        ),
    ),
    "resources": _View(
        title='🧱 Resources',
        description='package: `core.resources`  ·  kinds: `channel`, `role`, `category`, `thread`',
        fields=(
            ('Submodules',
             '`status`, `types`, `discovery`, `channel_service`, `role_service`',
             False),
            ('Cached status (guild {gid})',
             '*(no cached rows)*',
             False),
        ),
    ),
    "schemas": _View(
        title='📐 Subsystem schemas',
        description='19 registered  ·  bindings=17  ·  settings=100  ·  resources=15',
        fields=(
            ('By subsystem',
             '`ai` — b=1 s=10 r=0 v=1\n`automod` — b=0 s=11 r=0 v=1\n`blackjack` — b=0 s=1 r=0 v=1\n`btd6` — b=2 s=0 r=0 v=1\n`cleanup` — b=0 s=1 r=0 v=1\n`counters` — b=0 s=7 r=0 v=1\n`deathmatch` — b=0 s=1 r=0 v=1\n`economy` — b=1 s=0 r=1 v=1\n`help` — b=0 s=0 r=0 v=1\n`image_moderation` — b=0 s=8 r=0 v=1\n`karma` — b=0 s=4 r=0 v=1\n`logging` — b=11 s=12 r=11 v=5\n`moderation` — b=0 s=15 r=1 v=7\n`proof_channel` — b=1 s=0 r=1 v=1\n`role` — b=0 s=3 r=0 v=1\n`rps_tournament` — b=0 s=1 r=0 v=1\n`security` — b=0 s=11 r=0 v=1\n`welcome` — b=0 s=12 r=0 v=1\n`xp` — b=1 s=3 r=1 v=1',
             False),
        ),
    ),
    "sessions": _View(
        title='🎫 Active sessions',
        description='all subsystems',
        fields=(
            ('By subsystem',
             '*(none)*',
             False),
        ),
    ),
    "settings-registry": _View(
        title='🗂️ Settings registry',
        description='*(not built — call settings_registry.build_registry())*',
        style_token="greyple",
    ),
    "setup-readiness": _View(
        title='🛰 Setup Readiness — 0%',
        description='**0/17** bindings · **0/100** settings · **15** resource declarations · health `0 err` `0 warn` `17 info`',
        fields=(
            ('🎫 Support Tickets',
             "🔴 **Not set up** — members can't open support tickets yet. Enable them in the **Support Tickets** setup step (`!setup`) or run `!ticketsetup @StaffRole [#log]`.",
             False),
            ('Subsystems (1–15)',
             '`ai            ` bindings 0/1 · settings 0/10 · resources 0 · 0%\n`automod       ` bindings 0/0 · settings 0/11 · resources 0 · 0%\n`blackjack     ` bindings 0/0 · settings 0/1 · resources 0 · 0%\n`btd6          ` bindings 0/2 · settings 0/0 · resources 0 · 0%\n`cleanup       ` bindings 0/0 · settings 0/1 · resources 0 · 0%\n`counters      ` bindings 0/0 · settings 0/7 · resources 0 · 0%\n`deathmatch    ` bindings 0/0 · settings 0/1 · resources 0 · 0%\n`economy       ` bindings 0/1 · settings 0/0 · resources 1 · 0%\n`help          ` bindings 0/0 · settings 0/0 · resources 0 · —\n`image_moderation` bindings 0/0 · settings 0/8 · resources 0 · 0%\n`karma         ` bindings 0/0 · settings 0/4 · resources 0 · 0%\n`logging       ` bindings 0/11 · settings 0/12 · resources 11 · 0%\n`moderation    ` bindings 0/0 · settings 0/15 · resources 1 · 0%\n`proof_channel ` bindings 0/1 · settings 0/0 · resources 1 · 0%\n`role          ` bindings 0/0 · settings 0/3 · resources 0 · 0%',
             False),
            ('Subsystems (16–19)',
             '`rps_tournament` bindings 0/0 · settings 0/1 · resources 0 · 0%\n`security      ` bindings 0/0 · settings 0/11 · resources 0 · 0%\n`welcome       ` bindings 0/0 · settings 0/12 · resources 0 · 0%\n`xp            ` bindings 0/1 · settings 0/3 · resources 1 · 0%',
             False),
        ),
        footer='Read-only. Empty settings_keys (legacy KV) count as unconfigured. Subsystems with no declared config show — in the score column.',
    ),
    "tasks": _View(
        title='🔁 Managed tasks',
        description='0 active',
    ),
    "views": _View(
        title='🖼 Persistent views',
        description='10 registered',
        fields=(
            ('Subsystems',
             '`ai`, `btd6`, `economy`, `help`, `mining`, `moderation`, `role`, `server_management`, `ticket`, `ux_lab`',
             False),
        ),
    ),}


def build_view_embed(name: str, *, channel_id: int | None,
                     guild_id: int | None, member_tier: str):
    """One card's RenderedEmbed — the pinned strings formatted with the
    request's world values (module docstring: the four seams)."""
    from sb.kernel.panels.render import RenderedEmbed

    view = VIEWS[name]
    mapping = {
        "ch": channel_id if channel_id is not None else 0,
        "gid": guild_id if guild_id is not None else 0,
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "tier": member_tier or "user",
    }

    def _fmt(text: str) -> str:
        return text.format(**mapping) if text else text

    return RenderedEmbed(
        title=_fmt(view.title),
        description=_fmt(view.description),
        fields=tuple((_fmt(n), _fmt(v), i) for n, v, i in view.fields),
        footer=_fmt(view.footer),
        style_token=view.style_token,
        timestamp=(mapping["ts"] if view.timestamp else ""),
    )
