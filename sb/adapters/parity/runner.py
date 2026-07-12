"""Capture + replay for the NEW bot — the golden document twin.

Produces documents in EXACTLY the imported corpus's schema
(``harness_version`` 1, ``case_id`` / ``subsystem`` / ``seed`` / ``notes`` /
``steps[{input, calls, events?}]`` / ``db_delta``), reusing the imported
harness's own Normalizer, db-snapshot engine, diff and path logic — so a
replay diff line means BEHAVIOR drift, never dialect drift.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from parity.harness.capture import Normalizer
from parity.harness.cases import GoldenCase, Step
from parity.harness.dbsnap import diff_snapshots, reset_database, snapshot
from parity.harness.runner import HARNESS_VERSION, _describe_step, _diff_docs, golden_path
from parity.harness.world import DEFAULT_PERSONAS

from sb.adapters.parity.boot import Harness

__all__ = ["capture_case", "replay_case", "golden_path"]

#: CAPTURE-WORLD GUILD CONFIG, reconstructed (world state, like
#: parity/harness/world.py's channels/personas — seeded BEFORE the
#: before-snapshot so it never appears in any db_delta). The capture
#: guild ran with `ban_delete_message_days` SET to 1: goldens/moderation/
#: sweep_ban pins `delete_message_seconds: 86400` on the ban wire call,
#: while the shipped default is 0 and the shipped kwarg contract only
#: passes the field when a purge window is configured (D-0029's own
#: diagnosis: "capture-world config the reconstruction cannot reseed" —
#: it can: this is the reseed). Keys are the persisted settings
#: vocabulary (SettingSpec.settings_key).
CAPTURE_WORLD_SETTINGS: tuple[tuple[str, str], ...] = (
    ("moderation_ban_delete_message_days", "1"),
)

#: CAPTURE-WORLD PROCESS COUNTERS, reconstructed (world state — the
#: process-local server_logging counter block the shipped status embed
#: renders; goldens/logging/* pin the values). The counters are
#: PROCESS-LIFETIME in both worlds, but the capture's trajectory encodes
#: the CAPTURE run's own ordering (parity/run.py: CURATED_CASES first,
#: then the sweep sorted by command qualified_name — parity/cases/
#: sweep.py:169) plus its boot, neither of which the replay ordering
#: (curated + goldens PATH-sorted, cases.py) reproduces — so the state
#: is seeded per observing case, exactly like CAPTURE_WORLD_SETTINGS
#: above (the #163 reseed lane, extended from settings rows to process
#: memory; the cleanup `_word_cache` golden-pinned-literal precedent is
#: the same class one level up).
#:
#: Derivation, per the shipped counter semantics (disbot services/
#: server_logging.py: EVERY `moderation.action_taken` + every guild-
#: bearing `audit.action_recorded` bumps `skipped_disabled` when
#: `logging.enabled` is off; `_on_moderation_action_public` pre-filters
#: to the disciplinary set {warn, timeout, kick, ban} and counts
#: `mod_public_skipped` under the default "none" selector):
#:
#: * boot: +1 skipped_disabled — the harness boot ran the real on-ready
#:   flows and cleared their CALLS/EVENTS as boot noise
#:   (parity/harness/boot.py "boot noise ... is not case output") but a
#:   process counter cannot be cleared with them; exactly one boot-time
#:   audited mutation carried a guild (the on-ready log-channel binding
#:   auto-provision lane — disbot services/binding_mutation.py's
#:   system-actor class). Measured by the logging.enable_and_bind
#:   golden itself: skipped_disabled = 1 with ZERO bus events in any
#:   earlier curated case (curated order: 4×karma, economy — none emit
#:   audit/moderation events; parity/cases/curated.py).
#: * curated moderation.warn_flow (after enable_and_bind, before every
#:   sweep): +2 (warn audit + warn action) and +1 mod_public_skipped.
#: * sweeps before "logging" in qualified-name order (events counted
#:   from the goldens' own pinned `events` arrays): aireview_preset_add
#:   +1, ban +2 (+1 public), bulkcreate +1, bulkdelete +1,
#:   clearwarnings +2 (NOT disciplinary — no public skip), clone +1,
#:   create +2, createrole +1, del +1, kick +2 (+1 public), lock +1.
#:
#: ⇒ at logging.enable_and_bind: {skipped_disabled: 1}
#: ⇒ at every sweep.logging_* case: 1 + 2 + 15 = {skipped_disabled: 18,
#:   mod_public_skipped: 3} (warn_flow + ban + kick = 3 public skips;
#:   nothing between sweep.logging and sweep.logging_test increments).
CAPTURE_WORLD_COUNTERS: dict[str, dict[str, int]] = {
    "logging.enable_and_bind": {"skipped_disabled": 1},
    **{case_id: {"skipped_disabled": 18, "mod_public_skipped": 3}
       for case_id in ("sweep.logging", "sweep.logging_create",
                       "sweep.logging_routes", "sweep.logging_set",
                       "sweep.logging_status", "sweep.logging_test")},
}

#: CAPTURE-WORLD PROHIBITED-WORD CACHE, reconstructed (world state — the
#: cleanup cog's per-guild process cache the word list renders; the same
#: #163→#167 reseed lane as the counters above, and the very state the
#: playbook's `_word_cache` precedent named). The capture's per-case DB
#: truncate cannot reach a cog attribute, so the sweep's alphabetical
#: order carried `!word add test`'s write into the LATER list cases:
#: goldens/cleanup/sweep_word_list.json renders "Prohibited words:
#: `test`" over a truncated DB (cache HIT), while sweep_word — BEFORE
#: word_add alphabetically — renders the empty copy (cache load-on-miss
#: over the empty DB). Seeded/CLEARED at every case (None ⇒ clear), so
#: gate/report/isolation replay the same trajectory (trap 20:
#: runner-seeded, never accumulated — the ops' own post-mutation
#: invalidation would otherwise leak `test` differently per mode).
CAPTURE_WORLD_WORD_CACHE: dict[str, tuple[str, ...]] = {
    "sweep.word_list": ("test",),
}

#: CAPTURE-WORLD LEAKED CHANNELS, reconstructed (world state — the
#: gateway-cache flavor of the reseed lane, trap 17 READ-only): channels
#: an alphabetically-earlier capture case CREATED lived on in discord.py's
#: guild cache across the per-case DB truncate, so a later case's
#: TextChannelConverter name lookup found them. goldens/xp/
#: sweep_xpimport.json (`!xpimport test`) reads history from the `test`
#: channel minted by `_unmapped` sweep.create's `!create test …`
#: create_channel call — the scan is a pure READ (logs_from → empty), so
#: unlike the setup wall (playbook trap 17) no create twin is needed.
#: Name → constant snowflake; the Normalizer knows neither name nor id,
#: so the id renders `<msg:N>` exactly like the golden's. Seeded/CLEARED
#: at every case head (trap 20: runner-seeded, never accumulated).
#: CAPTURE-WORLD FISHING WEATHER, reconstructed (world state — the
#: wall-clock flavor of the reseed lane): the shipped weather pick is
#: derived from the CALENDAR DATE (utils/fishing/weather.py — a
#: sha256-seeded weighted pick over today's UTC date), and the capture
#: harness never patched ``datetime.now`` — so the capture run read the
#: capture MACHINE's real day and goldens/fishing/sweep_fish pins that
#: day's condition (🌧️ Rain; rain-pick days bracket the corpus capture
#: window — 2026-07-01/02/04/05/09 under the reconstructed table). The
#: replay's frozen per-case clock lands on a clear-sky date, so the
#: capture-day condition is seeded per observing case and CLEARED at
#: every case head (trap 20: runner-seeded, never accumulated — the
#: #163→#167 reseed lane, extended from settings rows / process memory
#: to the shipped unpatched-wall-clock read).
CAPTURE_WORLD_WEATHER: dict[str, str] = {
    "sweep.fish": "rain",
}

CAPTURE_WORLD_CHANNELS: dict[str, dict[str, int]] = {
    "sweep.xpimport": {"test": 700_000_000_000_000_901},
    # the channel-state sweeps target the SAME leaked `test` channel
    # (goldens/channel/sweep_slowmode `!slowmode test 3`, sweep_lock
    # `!lock test`, sweep_unlock `!unlock test` — each channel id
    # renders `<msg:1>`, the reply message `<msg:2>`); unlike the setup
    # wall the edits are RECORDED calls on an already-cached channel, so
    # only the name lookup is world state (trap 17 READ-only extended to
    # golden-pinned EDIT verbs — the create stays with sweep.create).
    "sweep.slowmode": {"test": 700_000_000_000_000_901},
    "sweep.lock": {"test": 700_000_000_000_000_901},
    "sweep.unlock": {"test": 700_000_000_000_000_901},
    # the trap-17 leaked WORKSPACE itself (the setup flip): the
    # alphabetically-earlier `sweep.setup` capture case CREATED
    # #superbot-setup (goldens/setup/sweep_setup.json records the
    # create_channel POST) and discord.py's guild cache carried it into
    # the later slash sweeps — whose goldens record ZERO channel calls
    # while SENDING into it. The shipped ensure_setup_channel's
    # get-before-create name lookup (sb/domain/setup/service.py) finds
    # the seeded channel exactly like the capture's cache hit, so the
    # find branch replays byte-green with no create call (the
    # sweep.xpimport / sweep.slowmode seeding precedent — trap 17's
    # "no ruled twin" claim predates this lane AND #242's create twin).
    # `sweep.setup` itself is NOT seeded: its golden pins the CREATE.
    "sweep.slash_setup-advanced": {"superbot-setup": 700_000_000_000_000_902},
    "sweep.slash_setup-status": {"superbot-setup": 700_000_000_000_000_902},
}


def _flatten_components(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for row in components:
        flat.extend(row.get("components", []))
    return flat


async def _drive(harness: Harness, step: Step, minted: list[int],
                 minted_components: dict[int, list[dict[str, Any]]]) -> str | None:
    """Mirror of parity/harness/runner._drive over the new-bot harness."""
    mentions = tuple(DEFAULT_PERSONAS[m]["id"] for m in step.mentions)
    if step.kind == "command":
        content = step.content
        if "__CHANNEL_" in content and harness.world is not None:
            for name, cid in harness.world.channels.items():
                content = content.replace(f"__CHANNEL_{name.upper()}__", f"<#{cid}>")
        await harness.send_command(content, persona=step.persona,
                                   channel=step.channel, mentions=mentions)
        return None
    if step.kind == "slash":
        await harness.invoke_slash(step.name, list(step.options),
                                   persona=step.persona, channel=step.channel)
        return None
    if step.kind == "click":
        index = step.target_message - 1
        if index < 0 or index >= len(minted):
            raise ValueError(
                f"step targets <msg:{step.target_message}> but only "
                f"{len(minted)} bot messages were minted")
        message_id = minted[index]
        custom_id = step.custom_id
        component_type = step.component_type
        if not custom_id and step.component_index >= 0:
            flat = _flatten_components(minted_components.get(message_id, []))
            if step.component_index >= len(flat):
                raise ValueError(
                    f"component_index {step.component_index} out of range "
                    f"({len(flat)} components on <msg:{step.target_message}>)")
            component = flat[step.component_index]
            custom_id = component.get("custom_id", "")
            component_type = component.get("type", component_type)
        await harness.click(message_id=message_id, custom_id=custom_id,
                            component_type=component_type,
                            values=list(step.values) if step.values is not None else None,
                            persona=step.persona, channel=step.channel)
        return custom_id
    if step.kind == "modal":
        # wire-type-5 modal submit (D-0073): target_message is optional —
        # a form driven at the feed seam with no earlier bot message in
        # the case carries no originating message (the kernel stash then
        # misses harmlessly; the submitted fields are the whole payload).
        message_id = 0
        if step.target_message:
            index = step.target_message - 1
            if index < 0 or index >= len(minted):
                raise ValueError(
                    f"step targets <msg:{step.target_message}> but only "
                    f"{len(minted)} bot messages were minted")
            message_id = minted[index]
        await harness.modal_submit(message_id=message_id,
                                   custom_id=step.custom_id,
                                   fields=dict(step.fields),
                                   persona=step.persona, channel=step.channel)
        return None
    raise ValueError(f"unknown step kind {step.kind!r}")  # pragma: no cover


async def capture_case(harness: Harness, case: GoldenCase) -> dict[str, Any]:
    """Run one case against the booted NEW bot; return its golden document."""
    if harness.world is None or harness.http is None:
        raise RuntimeError("harness not started")
    random.seed(case.seed)
    harness.world.clock.set_case_base(case.id)
    harness.reset_case_state()

    seeded_counters = CAPTURE_WORLD_COUNTERS.get(case.id)
    if seeded_counters is not None:
        # capture-world PROCESS state (see CAPTURE_WORLD_COUNTERS above) —
        # in-memory, so it seeds outside the DB block and never appears in
        # any db_delta.
        from sb.domain.server_logging.service import seed_counters_for_replay

        seed_counters_for_replay(seeded_counters)

    # capture-world PROCESS state, cleanup flavor (CAPTURE_WORLD_WORD_CACHE
    # above) — seeded OR cleared at every case so the cache never
    # accumulates across replayed cases (trap 20 mode-dependence).
    from sb.domain.cleanup.service import seed_word_cache_for_replay

    seed_word_cache_for_replay(harness.world.guild_id,
                               CAPTURE_WORLD_WORD_CACHE.get(case.id))

    # capture-world GATEWAY-CACHE state (CAPTURE_WORLD_CHANNELS above) —
    # reset_case_state() cleared the map; seed only what this case's
    # capture saw. In-memory, so it never appears in any db_delta.
    harness.leaked_channels.update(CAPTURE_WORLD_CHANNELS.get(case.id, {}))

    # capture-world FISHING WEATHER (CAPTURE_WORLD_WEATHER above) —
    # seeded OR cleared at every case so the override never leaks across
    # replayed cases (trap 20 mode-dependence). In-memory, no db_delta.
    from sb.domain.fishing.weather import seed_weather_for_replay

    seed_weather_for_replay(CAPTURE_WORLD_WEATHER.get(case.id))

    before: dict[str, Any] = {}
    pool = None
    if harness.db_ready:
        from sb.kernel.db import pool as pool_mod

        pool = pool_mod
        await reset_database(pool)
        for key, value in CAPTURE_WORLD_SETTINGS:
            await pool.execute(
                "INSERT INTO settings (guild_id, key, value) "
                "VALUES ($1, $2, $3) ON CONFLICT (guild_id, key) "
                "DO UPDATE SET value = EXCLUDED.value",
                (harness.world.guild_id, key, value))
        for statement in case.fixture_sql:
            await pool.execute(statement)
        before = await snapshot(pool)

    normalizer = Normalizer(harness.world)
    minted: list[int] = []
    minted_components: dict[int, list[dict[str, Any]]] = {}
    steps_out: list[dict[str, Any]] = []
    harness.take_calls()
    harness.take_events()
    harness.http.gaps.clear()

    for step in case.steps:
        resolved_custom_id = await _drive(harness, step, minted, minted_components)
        if harness.http.gaps:
            gaps = sorted(set(harness.http.gaps))
            harness.http.gaps.clear()
            raise RuntimeError(
                f"capture integrity: transport gap(s) hit during {case.id}: "
                f"{gaps} — extend sb/adapters/parity/transport.py.")
        raw_calls = harness.take_calls()
        for call in raw_calls:
            rid = getattr(call, "response_id", None)
            if rid is not None:
                minted.append(rid)
                components = (call.payload or {}).get("components")
                if components:
                    minted_components[rid] = components
        events = harness.take_events()
        events.sort(key=lambda e: e["event"])   # same fan-out-order rule
        input_doc = _describe_step(step)
        if resolved_custom_id:
            input_doc["custom_id"] = normalizer.normalize(resolved_custom_id)
        step_doc: dict[str, Any] = {
            "input": input_doc,
            "calls": normalizer.calls(raw_calls),
        }
        if events:
            step_doc["events"] = normalizer.events(events)
        steps_out.append(step_doc)

    delta: dict[str, Any] = {}
    if pool is not None:
        after = await snapshot(pool)
        delta = normalizer.db_delta(diff_snapshots(before, after))

    return {
        "harness_version": HARNESS_VERSION,
        "case_id": case.id,
        "subsystem": case.subsystem,
        "seed": case.seed,
        "notes": case.notes,
        "steps": steps_out,
        "db_delta": delta,
    }


async def replay_case(harness: Harness, case: GoldenCase,
                      goldens_root: Path) -> tuple[bool, list[str]]:
    """Re-run a case against the NEW bot and diff against its stored golden.
    True = parity (the flip evidence); the problem list is the honest gap."""
    path = golden_path(goldens_root, case)
    if not path.exists():
        return False, [f"golden missing: {path}"]
    expected = json.loads(path.read_text())
    actual = await capture_case(harness, case)
    # flag-13 dispositions (ORDER 009 / Q-0262.3): the three owner-accepted
    # corpus-red classes are dropped from BOTH docs, symmetrically, before
    # the diff — every other byte still diffs.
    from sb.adapters.parity.dispositions import apply_dispositions

    problems = _diff_docs(apply_dispositions(expected),
                          apply_dispositions(actual))
    return (not problems), problems
