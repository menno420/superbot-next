"""The automation template catalogue — the preset-referenced subset
(ORACLE disbot/services/automation_templates.py:129-210 @ f969b95, data
verbatim).

Carries exactly the THREE slugs the shipped presets stage
(``add_rule`` payloads in sb/domain/setup/preset_select.py — the
``_KNOWN_TEMPLATE_SLUGS`` set validates against the same three): the
onboarding templates ``welcome-message`` / ``new-member-role`` /
``notify-staff-on-join``. The oracle's wider catalogue
(rules-channel-binding, delayed-followup-message, the server-pulse set)
arrives with the automation panel port, not this write seam.

``required_overrides`` ride along verbatim as DECLARED template facts:
the oracle presets stage the default configs unchanged (channel_id 0 /
role_id 0) and the rule inserts DISABLED, so an unconfigured target is
inert — the operator fills it when the automation panel ports.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["AutomationTemplate", "TEMPLATES", "get_template"]


@dataclass(frozen=True)
class AutomationTemplate:
    """One installable template (automation_templates.AutomationTemplate,
    the declarative subset this seam consumes)."""

    slug: str
    display_name: str
    description: str
    trigger_kind: str
    action_kind: str
    default_trigger_config: dict = field(default_factory=dict)
    default_action_config: dict = field(default_factory=dict)
    required_overrides: tuple[str, ...] = ()
    category: str = "onboarding"


TEMPLATES: tuple[AutomationTemplate, ...] = (
    AutomationTemplate(
        slug="welcome-message",
        display_name="Welcome message",
        description=(
            "Send a configurable welcome message to a specific "
            "channel whenever a new member joins."),
        trigger_kind="member_join",
        action_kind="send_message",
        default_action_config={
            "channel_id": 0,
            "template": "Welcome, {{member}}! 👋",
        },
        required_overrides=("channel_id",),
        category="onboarding"),
    AutomationTemplate(
        slug="new-member-role",
        display_name="New member role",
        description=(
            "Assign the configured role to anyone who joins the guild. "
            "Operator picks the role id."),
        trigger_kind="member_join",
        action_kind="assign_role",
        default_action_config={"role_id": 0},
        required_overrides=("role_id",),
        category="onboarding"),
    AutomationTemplate(
        slug="notify-staff-on-join",
        display_name="Notify staff on join",
        description=(
            "Post a notice to the configured staff channel whenever a "
            "new member joins."),
        trigger_kind="member_join",
        action_kind="send_message",
        default_action_config={
            "channel_id": 0,
            "template": "🆕 {{member}} joined the server.",
        },
        required_overrides=("channel_id",),
        category="onboarding"),
)


def get_template(slug: str) -> AutomationTemplate | None:
    for template in TEMPLATES:
        if template.slug == slug:
            return template
    return None
