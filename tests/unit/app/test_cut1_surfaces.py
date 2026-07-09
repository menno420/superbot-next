"""CUT-1 successor surfaces (completion-report flag 30): the app-command
tree built from the LIVE manifests (sb/adapters/discord/command_tree.py),
the gated GUILD-scoped sync leg, and the message-feed adapter
(sb/adapters/discord/message_feed.py) — the ONE armed message-band
consumer (prefix dispatch; fuzzy/NL/passive hooks stay dormant).

Hermetic + roster-free on purpose (see TestManifestPanelRegistration's
docstring): every manifest here is synthetic — no sb.manifest imports.
The command_tree cases need discord.py and skip where it is absent (the
ci.yml `tests` job runs without runtime deps by design); the message-feed
adapter is duck-typed and tests everywhere."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from sb.adapters.discord import command_tree, message_feed
from sb.kernel.interaction import adapters as adapters_mod
from sb.kernel.interaction.adapters import install_target_index
from sb.kernel.interaction.request import Surface, TargetRef


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def _install_fake_index(keys: dict[tuple[str, Surface], object]) -> None:
    index = {k: TargetRef(key=k[0], spec=spec) for k, spec in keys.items()}
    install_target_index(lambda key, surface: index.get((key, surface)))


# --------------------------------------------------------------- guild sync gate


class TestGuildSyncTarget:
    def _cfg(self, **kw):
        base = {"SB_APPCMD_SYNC_GUILD_ID": None, "SB_DATA_PLANE": "test"}
        base.update(kw)
        return SimpleNamespace(**base)

    def test_absent_opt_in_means_no_sync(self):
        from sb.app.main import guild_sync_target

        assert guild_sync_target(self._cfg()) is None

    def test_test_plane_plus_opt_in_returns_the_guild(self):
        from sb.app.main import guild_sync_target

        cfg = self._cfg(SB_APPCMD_SYNC_GUILD_ID=1350952413737259151)
        assert guild_sync_target(cfg) == 1350952413737259151

    def test_prod_plane_never_syncs_even_when_opted_in(self):
        from sb.app.main import guild_sync_target

        cfg = self._cfg(SB_APPCMD_SYNC_GUILD_ID=123, SB_DATA_PLANE="prod")
        assert guild_sync_target(cfg) is None


# ------------------------------------------------------------------ message feed


class _FakeMessage:
    def __init__(self, content: str, *, bot_author: bool = False) -> None:
        self.content = content
        self.author = SimpleNamespace(id=42, bot=bot_author)
        self.guild = SimpleNamespace(id=7, owner_id=42)
        self.channel = SimpleNamespace(id=9)
        self.id = 1001
        self.replies: list[str] = []

    async def reply(self, content: str | None = None, **kwargs: object):
        self.replies.append(content)
        return SimpleNamespace(id=2002)


class TestMatchPrefixTarget:
    def test_longest_qualified_match_wins(self):
        spec = SimpleNamespace(name="add", route=object())
        _install_fake_index({("karma add", Surface.PREFIX): spec,
                             ("karma", Surface.PREFIX): spec})
        try:
            assert message_feed.match_prefix_target(
                "!karma add @u thanks", prefix="!") == ("karma add",
                                                        ["@u", "thanks"])
            assert message_feed.match_prefix_target(
                "!karma", prefix="!") == ("karma", [])
        finally:
            adapters_mod.reset_adapter_ports_for_tests()

    def test_non_prefix_and_unknown_are_not_consumed(self):
        _install_fake_index({("help", Surface.PREFIX): SimpleNamespace()})
        try:
            assert message_feed.match_prefix_target("hello", prefix="!") is None
            assert message_feed.match_prefix_target("!", prefix="!") is None
            assert message_feed.match_prefix_target("!nosuch", prefix="!") is None
        finally:
            adapters_mod.reset_adapter_ports_for_tests()


class TestHandleGatewayMessage:
    def test_bot_authors_are_ignored_before_anything(self, monkeypatch):
        called = []
        monkeypatch.setattr(message_feed, "dispatch_prefix",
                            lambda *a, **k: called.append(1))
        msg = _FakeMessage("!help", bot_author=True)
        assert run(message_feed.handle_prefix_message(msg, prefix="!")) is None
        assert not called

    def test_known_command_dispatches_with_the_prefix_ctx_shape(self, monkeypatch):
        _install_fake_index({("help", Surface.PREFIX): SimpleNamespace()})
        seen: dict[str, object] = {}

        async def fake_dispatch(ctx, *, responder):
            seen["ctx"] = ctx
            seen["responder"] = responder
            return "RESULT"

        monkeypatch.setattr(message_feed, "dispatch_prefix", fake_dispatch)
        try:
            msg = _FakeMessage("!help me now")
            result = run(message_feed.handle_prefix_message(msg, prefix="!"))
        finally:
            adapters_mod.reset_adapter_ports_for_tests()
        assert result == "RESULT"
        ctx = seen["ctx"]
        assert ctx.command.qualified_name == "help"
        assert ctx.kwargs == {"argv": ("me", "now"), "text": "me now"}
        assert ctx.author is msg.author and ctx.guild is msg.guild
        assert ctx.message is msg
        assert seen["responder"].surface is Surface.PREFIX

    def test_dispatch_fault_renders_the_error_envelope(self, monkeypatch):
        _install_fake_index({("help", Surface.PREFIX): SimpleNamespace()})

        async def boom(ctx, *, responder):
            raise RuntimeError("wiring fault")

        monkeypatch.setattr(message_feed, "dispatch_prefix", boom)
        try:
            msg = _FakeMessage("!help")
            result = run(message_feed.handle_prefix_message(msg, prefix="!"))
        finally:
            adapters_mod.reset_adapter_ports_for_tests()
        assert result is None
        assert len(msg.replies) == 1        # the K8 envelope, not a traceback

    def test_non_command_content_is_left_alone(self, monkeypatch):
        called = []
        monkeypatch.setattr(message_feed, "dispatch_prefix",
                            lambda *a, **k: called.append(1))
        msg = _FakeMessage("just chatting")
        assert run(message_feed.handle_prefix_message(msg, prefix="!")) is None
        assert not called and not msg.replies


class TestPrefixContextReply:
    def test_reply_content_is_optional_for_the_panel_presenter(self):
        # DiscordPanelPresenter replies embed/view-only (panel_view.py
        # origin.reply(embed=..., view=...)) — found by the live proof run.
        msg = _FakeMessage("!help")
        ctx = message_feed._PrefixContext(msg, target_key="help", rest=[])
        run(ctx.reply(embed="E", view="V"))
        assert msg.replies == [None]


class TestHandleChatAward:
    def _patch_core(self, monkeypatch):
        import sb.domain.xp.service as xp_service
        awards: list[tuple[int, int]] = []

        async def fake_award(user_id, guild_id, *, now):
            awards.append((user_id, guild_id))
            return "AWARD"

        monkeypatch.setattr(xp_service, "handle_chat_message", fake_award)
        return awards

    def test_bots_and_dms_never_award(self, monkeypatch):
        awards = self._patch_core(monkeypatch)
        assert run(message_feed.handle_chat_award(
            _FakeMessage("hi", bot_author=True))) is None
        dm = _FakeMessage("hi")
        dm.guild = None
        assert run(message_feed.handle_chat_award(dm)) is None
        assert not awards

    def test_human_guild_message_awards_commands_included(self, monkeypatch):
        awards = self._patch_core(monkeypatch)
        assert run(message_feed.handle_chat_award(
            _FakeMessage("just chatting"))) == "AWARD"
        assert run(message_feed.handle_chat_award(
            _FakeMessage("!help"))) == "AWARD"    # shipped: commands award too
        assert awards == [(42, 7), (42, 7)]

    def test_award_fault_never_breaks_the_loop(self, monkeypatch):
        import sb.domain.xp.service as xp_service

        async def boom(user_id, guild_id, *, now):
            raise RuntimeError("db down")

        monkeypatch.setattr(xp_service, "handle_chat_message", boom)
        assert run(message_feed.handle_chat_award(
            _FakeMessage("hello"))) is None


class TestArmMessageFeed:
    def test_registers_an_additive_on_message_listener(self):
        listeners: list[tuple[object, str]] = []
        bot = SimpleNamespace(
            add_listener=lambda coro, name: listeners.append((coro, name)))
        message_feed.arm_message_feed(bot, prefix="!")
        assert len(listeners) == 1
        assert listeners[0][1] == "on_message"
        assert asyncio.iscoroutinefunction(listeners[0][0])

    def test_listener_runs_prefix_dispatch_then_chat_award(self, monkeypatch):
        order: list[str] = []

        async def fake_prefix(message, *, prefix):
            order.append("prefix")

        async def fake_award(message):
            order.append("award")

        monkeypatch.setattr(message_feed, "handle_prefix_message", fake_prefix)
        monkeypatch.setattr(message_feed, "handle_chat_award", fake_award)
        listeners: list[tuple[object, str]] = []
        bot = SimpleNamespace(
            add_listener=lambda coro, name: listeners.append((coro, name)))
        message_feed.arm_message_feed(bot, prefix="!")
        run(listeners[0][0](_FakeMessage("!rank")))
        assert order == ["prefix", "award"]     # capture order: dispatch first


# ------------------------------------------------------------------ command tree


class TestSlashDescription:
    def test_clips_to_discords_100_char_bound(self):
        spec = SimpleNamespace(name="x", summary="s" * 150)
        text = command_tree.slash_description(spec)
        assert len(text) == 100 and text.endswith("…")

    def test_empty_summary_falls_back_to_the_name(self):
        assert command_tree.slash_description(
            SimpleNamespace(name="karma", summary="")) == "karma"


needs_discord = pytest.mark.skipif(
    not command_tree.DISCORD_AVAILABLE,
    reason="discord.py absent (the ci.yml tests job runs dep-free by design)")


def _manifest(*cmds):
    return SimpleNamespace(commands=cmds, panels=())


def _bot():
    import discord
    from discord.ext import commands

    return commands.Bot(command_prefix="!", intents=discord.Intents.none(),
                        help_command=None)


@needs_discord
class TestRegisterAppCommands:
    def test_kind_partition_and_names(self):
        bot = _bot()
        manifests = [
            _manifest(
                SimpleNamespace(name="settings", kind="both", group="",
                                summary="Open the settings hub."),
                SimpleNamespace(name="thanks", kind="prefix", group="",
                                summary="prefix-only — must NOT register"),
            ),
            _manifest(
                SimpleNamespace(name="karma", kind="slash", group="",
                                summary="Show your karma."),
            ),
        ]
        count = command_tree.register_app_commands(bot, manifests)
        names = {c.name for c in bot.tree.get_commands()}
        assert count == 2
        assert names == {"settings", "karma"}

    def test_group_path_nests_like_qualified_name(self):
        bot = _bot()
        manifests = [_manifest(
            SimpleNamespace(name="channel", kind="slash", group="logging",
                            summary="Bind the logging channel."))]
        assert command_tree.register_app_commands(bot, manifests) == 1
        group = bot.tree.get_command("logging")
        assert group is not None
        sub = group.get_command("channel")
        assert sub is not None and sub.qualified_name == "logging channel"

    def test_callback_funnels_through_dispatch_interaction(self, monkeypatch):
        import sb.kernel.interaction.adapters.slash as slash_mod

        seen: dict[str, object] = {}

        async def fake_dispatch(interaction, *, responder):
            seen["interaction"] = interaction
            seen["responder"] = responder

        # patched BEFORE register: _make_callback binds at registration.
        monkeypatch.setattr(slash_mod, "dispatch_interaction", fake_dispatch)
        bot = _bot()
        command_tree.register_app_commands(bot, [_manifest(
            SimpleNamespace(name="help", kind="both", group="",
                            summary="Everything the bot can do."))])
        cmd = bot.tree.get_command("help")
        interaction = SimpleNamespace(
            id=1, user=SimpleNamespace(id=2), guild=None, channel_id=3,
            command=SimpleNamespace(qualified_name="help"),
            namespace=SimpleNamespace())
        run(cmd.callback(interaction))
        assert seen["interaction"] is interaction
        assert seen["responder"].surface is Surface.SLASH

    def test_sync_guild_commands_writes_the_guild_scope_only(self):
        calls: dict[str, object] = {}

        class _Tree:
            def copy_global_to(self, *, guild):
                calls["copied_to"] = guild.id

            async def sync(self, *, guild=None):
                calls["synced_guild"] = getattr(guild, "id", None)
                return [SimpleNamespace(name="settings"),
                        SimpleNamespace(name="help")]

        bot = SimpleNamespace(tree=_Tree())
        synced = run(command_tree.sync_guild_commands(bot, 555))
        assert synced == ("help", "settings")
        assert calls == {"copied_to": 555, "synced_guild": 555}
