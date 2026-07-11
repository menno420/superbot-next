"""Counting K7 lanes (band 6) — the shipped counting_cog config
mutations + the on_message hot path as audited one-leg ops over the
counting_state blob (the leg's txn IS the shipped per-channel
scope_lock: read-modify-write under one conn).

* ``counting.record_count`` — the V/M/A hot path: load state, run the
  headless ``engine.compute_decision`` (mutates in place), persist only
  when the decision says state mutated, and hand the decision back to
  the MESSAGE FEED in ``after`` (delete / reply / reaction are the
  feed's Discord side, band-2 moderation auto-delete seam).
* config lanes — enable (the shipped start_match config shape verbatim,
  incl. multiples/custom/skip arguments), disable, reset, the two
  toggles, set_skip_step.
* ``counting.scrub_subject_counts`` — the MEMBER_ID erasure body.

DEVIATION (ledgered D-0044): the shipped start_match CREATES a fresh
``<mode>-counting-<timestamp>`` channel and end_match DELETES it —
channel provisioning/teardown rides the resource-provision port (the
band-2/band-5 honest-wait posture, same as logging.create_channels).
The lanes here arm counting on EXISTING channels; the routes say so
politely until the port arms.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sb.domain.counting import engine as counting_engine
from sb.domain.counting import game_logic, store
from sb.kernel.interaction.errors import ValidatorError
from sb.kernel.workflow.context import LegOutcome, WorkflowContext
from sb.kernel.workflow.registry import REGISTRY
from sb.kernel.workflow.result import StepResult
from sb.kernel.workflow.spec import (
    CompoundOpSpec,
    IdempotencyPosture,
    LegKind,
    LegSpec,
    WorkflowLane,
)
from sb.spec.refs import WorkflowRef, is_registered, workflow

__all__ = ["VALID_MODES", "ensure_ops_refs", "register_ops"]

# shipped start_match vocabulary verbatim
VALID_MODES = (
    "normal", "reverse", "skip", "random", "multiples", "prime",
    "fibonacci", "squares", "cubes", "factorials", "custom",
)

_RESET_TO_ZERO = (
    "normal", "random", "skip", "multiples", "prime", "fibonacci",
    "squares", "cubes", "factorials", "custom",
)


def _ids(ctx: WorkflowContext) -> tuple[int, int]:
    return (int(getattr(ctx.actor, "user_id", 0) or 0),
            int(ctx.guild_id or 0))


def _channels(state: dict) -> dict:
    return state.setdefault("channels", {})


def _require_channel(state: dict, channel_id: str) -> dict:
    data = _channels(state).get(channel_id)
    if data is None:
        # copy-only form: the raise-site sentence IS the user copy,
        # rendered BARE (the role ops `_verr` posture) — the one-arg param
        # form wrapped it in the missing-argument boilerplate, but the
        # shipped cog answered the plain byte
        # (goldens/counting/sweep_reset_count +
        # sweep_toggle_reset_on_wrong_count pin it).
        raise ValidatorError(
            "", "Counting game is not set up for this channel.")
    return data


def _now_ts() -> float:
    return datetime.now(tz=timezone.utc).timestamp()


def channel_config(mode: str, *, skip_step: int = 5,
                   multiple: int | None = None,
                   custom_sequence: list[int] | None = None) -> dict:
    """The shipped start_match per-channel config shape, verbatim."""
    starting_count = 1000 if mode == "reverse" else 0
    rand_target = rand_lo = rand_hi = None
    if mode == "random":
        rand_target, rand_lo, rand_hi = game_logic.start_random_round(
            starting_count)
    config: dict = {
        "current_count": starting_count,
        "last_user": None,
        "taking_turns": False,
        "leaderboard": {},
        "mode": mode,
        "step": skip_step if mode == "skip" else 1,
        "multiple": multiple if mode == "multiples" else None,
        "custom_sequence": custom_sequence if mode == "custom" else None,
        "sequence_index": 0,
        "last_count_time": _now_ts(),
        "reset_on_wrong_count": False,
        "next_expected": rand_target,
        "range_lo": rand_lo,
        "range_hi": rand_hi,
    }
    if mode == "prime":
        config["prime_numbers"] = []
    return config


@workflow("counting.record_count_leg")
async def _record_count(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    channel_id = str(ctx.params.get("channel_id") or 0)
    content = str(ctx.params.get("content") or "")
    mention = str(ctx.params.get("author_mention") or f"<@{uid}>")
    state = await store.get_state(gid, conn=conn)
    data = _channels(state).get(channel_id)
    if data is None:
        return LegOutcome(step=StepResult(uid, "record_count", True),
                          before={}, after={"active": False})
    decision = counting_engine.compute_decision(
        content=content, author_mention=mention, channel_data=data,
        user_id=str(uid))
    if decision.state_mutated:
        await store.set_state(conn, guild_id=gid, state=state)
    return LegOutcome(
        step=StepResult(uid, "record_count", True), before={},
        after={
            "active": True,
            "accepted": decision.accepted,
            "delete_message": decision.delete_message,
            "reply": decision.reply,
            "add_reaction": decision.add_reaction,
            "state_mutated": decision.state_mutated,
            "reply_delete_after": decision.reply_delete_after,
        })


@workflow("counting.record_enable")
async def _record_enable(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    channel_id = str(ctx.params.get("channel_id") or 0)
    mode = str(ctx.params.get("mode") or "").lower()
    if mode not in VALID_MODES:
        raise ValidatorError(
            f"Invalid mode. Available modes: {', '.join(VALID_MODES)}.")
    multiple = ctx.params.get("multiple")
    custom_sequence = ctx.params.get("custom_sequence")
    skip_step = int(ctx.params.get("skip_step") or 5)
    if mode == "multiples":
        if not isinstance(multiple, int) or multiple < 1:
            raise ValidatorError("Multiple must be a positive integer.")
    if mode == "custom":
        if not custom_sequence:
            raise ValidatorError(
                "Invalid sequence. Please provide a comma-separated "
                "list of integers.")
    if skip_step < 1:
        raise ValidatorError(
            "Skip step must be a positive integer, e.g. "
            "`!start_match skip 5`.")
    state = await store.get_state(gid, conn=conn)
    if channel_id in _channels(state):
        raise ValidatorError(
            "A counting match is already active in this channel.")
    config = channel_config(
        mode, skip_step=skip_step,
        multiple=multiple if isinstance(multiple, int) else None,
        custom_sequence=list(custom_sequence) if custom_sequence else None)
    _channels(state)[channel_id] = config
    await store.set_state(conn, guild_id=gid, state=state)
    if mode == "skip":
        extra = (f" Count up by **{skip_step}** — 1, {1 + skip_step}, "
                 f"{1 + 2 * skip_step}, …")
    elif mode == "random":
        extra = (f" Guess the secret number — it's between "
                 f"**{config['range_lo']}–{config['range_hi']}**.")
    else:
        extra = ""
    return LegOutcome(
        step=StepResult(uid, "enable_channel", True), before={},
        after={"mode": mode,
               "message": f"Started a **{mode.capitalize()}** counting "
                          f"match in <#{channel_id}>!{extra}"})


@workflow("counting.record_disable")
async def _record_disable(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    channel_id = str(ctx.params.get("channel_id") or 0)
    state = await store.get_state(gid, conn=conn)
    if channel_id not in _channels(state):
        raise ValidatorError(
            "No active counting match found in the specified channel.")
    del _channels(state)[channel_id]
    await store.set_state(conn, guild_id=gid, state=state)
    return LegOutcome(
        step=StepResult(uid, "disable_channel", True), before={},
        after={"message": f"Ended the counting match in <#{channel_id}>."})


@workflow("counting.record_reset")
async def _record_reset(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    channel_id = str(ctx.params.get("channel_id") or 0)
    state = await store.get_state(gid, conn=conn)
    data = _require_channel(state, channel_id)
    mode = data.get("mode", "normal")
    counting_engine.reset_channel_data(data, mode)
    if mode == "random":
        target, lo, hi = game_logic.start_random_round(
            int(data.get("current_count", 0)))
        data["next_expected"] = target
        data["range_lo"], data["range_hi"] = lo, hi
    await store.set_state(conn, guild_id=gid, state=state)
    start = data["current_count"]
    return LegOutcome(
        step=StepResult(uid, "reset_count", True), before={},
        after={"message": f"The count in <#{channel_id}> has been reset "
                          f"to **{start}**."})


@workflow("counting.record_toggle")
async def _record_toggle(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    channel_id = str(ctx.params.get("channel_id") or 0)
    flag = str(ctx.params.get("flag") or "")
    if flag not in ("taking_turns", "reset_on_wrong_count"):
        raise ValidatorError("Unknown counting flag.")
    state = await store.get_state(gid, conn=conn)
    data = _require_channel(state, channel_id)
    data[flag] = not data.get(flag, False)
    await store.set_state(conn, guild_id=gid, state=state)
    status = "enabled" if data[flag] else "disabled"
    label = ("Taking turns" if flag == "taking_turns"
             else "'Reset on wrong count'")
    return LegOutcome(
        step=StepResult(uid, "toggle_flag", True), before={},
        after={"value": data[flag],
               "message": f"{label} has been {status} in "
                          f"<#{channel_id}>."})


@workflow("counting.record_set_skip")
async def _record_set_skip(conn, ctx: WorkflowContext) -> LegOutcome:
    uid, gid = _ids(ctx)
    channel_id = str(ctx.params.get("channel_id") or 0)
    step = ctx.params.get("step")
    state = await store.get_state(gid, conn=conn)
    data = _require_channel(state, channel_id)
    if data.get("mode") != "skip":
        raise ValidatorError(
            "The skip step can only be set for a 'skip' match.")
    if not isinstance(step, int) or step < 1:
        raise ValidatorError(
            "Please provide a single positive integer, e.g. "
            "`!set_skip_numbers 5`.")
    data["step"] = step
    await store.set_state(conn, guild_id=gid, state=state)
    return LegOutcome(
        step=StepResult(uid, "set_skip_step", True), before={},
        after={"message": f"Skip step updated to **{step}** — 1, "
                          f"{1 + step}, {1 + 2 * step}, …"})


@workflow("counting.scrub_subject_counts")
async def _scrub_subject(conn, ctx: WorkflowContext) -> LegOutcome:
    uid = int(ctx.params.get("subject_user_id")
              or getattr(ctx.actor, "user_id", 0) or 0)
    touched = await store.scrub_subject(conn, user_id=uid)
    return LegOutcome(step=StepResult(uid, "scrub", True), before={},
                      after={"rows_touched": touched,
                             "disposition": "scrubbed"})


def _op(op_key: str, verb: str, leg_ref: str) -> CompoundOpSpec:
    return CompoundOpSpec(
        op_key=op_key, domain="counting", lane=WorkflowLane.DOMAIN,
        authority_ref="user",
        legs=(LegSpec("record", LegKind.DB, WorkflowRef(leg_ref),
                      "reversible"),),
        idempotency=IdempotencyPosture.NATURAL_KEY, dedup_key=None,
        audit_verb=verb)


RECORD_COUNT = _op("counting.record_count", "counting_counted",
                   "counting.record_count_leg")
ENABLE = _op("counting.enable_channel", "counting_match_started",
             "counting.record_enable")
DISABLE = _op("counting.disable_channel", "counting_match_ended",
              "counting.record_disable")
RESET = _op("counting.reset_count", "counting_count_reset",
            "counting.record_reset")
TOGGLE = _op("counting.toggle_flag", "counting_flag_toggled",
             "counting.record_toggle")
SET_SKIP = _op("counting.set_skip_step", "counting_skip_set",
               "counting.record_set_skip")

_OPS = (RECORD_COUNT, ENABLE, DISABLE, RESET, TOGGLE, SET_SKIP)

_REF_TABLE = (
    ("counting.record_count_leg", _record_count),
    ("counting.record_enable", _record_enable),
    ("counting.record_disable", _record_disable),
    ("counting.record_reset", _record_reset),
    ("counting.record_toggle", _record_toggle),
    ("counting.record_set_skip", _record_set_skip),
    ("counting.scrub_subject_counts", _scrub_subject),
)


def _op_runner(op: CompoundOpSpec):
    async def _run(ctx):
        from sb.kernel.workflow import engine

        return await engine.run(op, ctx)
    return _run


def _register_op_markers() -> None:
    from sb.spec.refs import workflow as _workflow

    for op in _OPS:
        if not is_registered(WorkflowRef(op.op_key)):
            _workflow(op.op_key)(_op_runner(op))


def register_ops() -> None:
    for op in _OPS:
        try:
            REGISTRY.register(op)
        except ValueError as exc:
            if "duplicate CompoundOpSpec" not in str(exc):
                raise
    _register_op_markers()


def ensure_ops_refs() -> None:
    from sb.spec.refs import workflow as _workflow

    for name, fn in _REF_TABLE:
        if not is_registered(WorkflowRef(name)):
            _workflow(name)(fn)
    _register_op_markers()
