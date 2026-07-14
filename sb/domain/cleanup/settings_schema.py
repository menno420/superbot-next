"""The declared cleanup.* settings schema — the shipped
CLEANUP_CONFIG_SCHEMA (cogs/cleanup/schemas.py @9776401) as SettingSpec
facets. Lives in the DOMAIN (not the manifest module) so the cleanup
settings panel can read the shipped roster without a manifest↔panels
import cycle (the sb/domain/ai/settings_schema.py precedent);
``sb/manifest/cleanup.py`` declares exactly these facets.

The one genuine scalar — the ``!cleanuphistory`` spam-duplicate detection
window — verbatim: default 15 (the historical hardcoded constant), bounds
1..300 ("keep the window sane (1s..5min)"), the ``numeric_presets``
edit-dispatch hint with the shipped (10, 15, 30) roster, and the borrowed
``cleanup.policy.configure`` edit authority (the shipped schema's own
note: ``cleanup.settings.configure`` is not a registered capability).
The shipped DomainPanelSpec ("Cleanup policies" — the discovery field) is
panel copy, not a settings facet — sb/domain/cleanup/panels.py carries
its bytes.
"""

from __future__ import annotations

from sb.spec.settings import SettingSpec

__all__ = ["SHIPPED_CLEANUP_SETTINGS"]

_CAPABILITY = "cleanup.policy.configure"

#: the shipped CLEANUP_SETTINGS tuple VERBATIM (name, type, default,
#: settings_key, capability, hint, bounds, input_hint, presets — the
#: settings page renders exactly this roster).
SHIPPED_CLEANUP_SETTINGS: tuple[SettingSpec, ...] = (
    SettingSpec(
        name="spam_window_seconds",
        value_type=int,
        default=15,
        settings_key="cleanup_spam_window_seconds",
        capability_required=_CAPABILITY,
        hint=("Window (seconds) the `!cleanuphistory` spam sweep treats "
              "two near-identical messages from one author as duplicates."),
        bounds=(1, 300),
        input_hint="numeric_presets",
        presets=(10, 15, 30),
    ),
)
