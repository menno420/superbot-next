"""Shared band-2 operator-spine helpers (declaration-first slices).

Every operator subsystem gets a REAL hub read-view for free: a generated
FieldsBlock provider over THE K7 settings declarations (name → resolved
value, per-guild → global → default), the same projection family as the
band-1 settings hub. `Reply` is the minimal HandlerRef result shape the
resolver renders; `pending_handler` is the sanctioned declared-but-port-
not-armed terminal (declared surface, honest BLOCKED copy — successor
slices install the real ops)."""

from __future__ import annotations

from dataclasses import dataclass

from sb.kernel.panels.registry import register_panel
from sb.spec.outcomes import BLOCKED
from sb.spec.panels import (
    Audience,
    EmbedFrameSpec,
    FieldsBlock,
    FooterMode,
    NavigationSpec,
    PanelSpec,
    TextBlock,
)
from sb.spec.refs import (
    HandlerRef,
    PanelRef,
    ProviderRef,
    handler,
    is_registered,
    panel,
    provider,
)

__all__ = [
    "Reply",
    "ensure_hub",
    "hub_spec",
    "pending_handler",
]


@dataclass(frozen=True)
class Reply:
    outcome: str
    user_message: str


def _settings_provider_name(subsystem: str) -> str:
    return f"{subsystem}.hub_settings"


def _ensure_settings_provider(subsystem: str) -> ProviderRef:
    name = _settings_provider_name(subsystem)
    ref = ProviderRef(name)
    if not is_registered(ref):
        @provider(name)
        async def hub_settings(ctx: object, _sub: str = subsystem):
            from sb.kernel import settings as ksettings

            guild_id = int(getattr(ctx, "guild_id", 0) or 0)
            rows = []
            for decl in ksettings.iter_declarations(_sub):
                try:
                    value = await ksettings.resolve(guild_id, _sub, decl.name)
                except Exception:  # noqa: BLE001 — headless read = default
                    value = decl.default
                rows.append((decl.name, f"`{value}`"))
            if not rows:
                # honest empty state (owner-ordered render rule: never a
                # bare dash) — say WHY it is empty and WHAT arrives next.
                return ((
                    "No declared settings",
                    f"The `{_sub}` subsystem declares no settings yet. "
                    "Menu actions for this hub arrive with the "
                    "operator-spine successor slices."),)
            return tuple(rows[:24])
    return ref


def hub_spec(subsystem: str, title: str, blurb: str) -> PanelSpec:
    return PanelSpec(
        panel_id=f"{subsystem}.hub",
        subsystem=subsystem,
        title=title,
        audience=Audience.INVOKER,
        frame=EmbedFrameSpec(footer_mode=FooterMode.SUBSYSTEM),
        body=(TextBlock(blurb),
              FieldsBlock(provider=_ensure_settings_provider(subsystem))),
        navigation=NavigationSpec(),
    )


def ensure_hub(subsystem: str, title: str, blurb: str) -> None:
    """Register the hub panel factory ref + the registry entry (idempotent)."""
    _ensure_settings_provider(subsystem)
    ref = PanelRef(f"{subsystem}.hub")
    if not is_registered(ref):
        @panel(f"{subsystem}.hub")
        def _factory(_sub: str = subsystem, _t: str = title, _b: str = blurb):
            return hub_spec(_sub, _t, _b)
    try:
        register_panel(hub_spec(subsystem, title, blurb))
    except ValueError as exc:
        if "already registered" not in str(exc) and "duplicate" not in str(exc):
            raise


def pending_handler(name: str, message: str) -> HandlerRef:
    """A declared-surface terminal for ops whose Discord state-mutation
    port has not armed yet (declared + honest refusal, never silent)."""
    ref = HandlerRef(name)
    if not is_registered(ref):
        @handler(name)
        async def _pending(req, _msg: str = message) -> Reply:
            return Reply(BLOCKED, _msg)
    return ref
