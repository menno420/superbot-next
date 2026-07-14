"""Fishing handlers (band 6) — the shipped cast-open lane (energy gate →
spend → the waiting-for-a-bite panel), the Reel commit route,
dex/leaderboard/trophy reads, the slice-1 weather/venue surfaces
(``!forecast`` / ``!sail``), the slice-2 rod-ladder surfaces (``!rod``
/ ``!rodrecipes`` / ``!craftrod``), the slice-3 bait-shelf surfaces
(``!bait`` / ``!craftbait`` / ``!craftpearl`` / ``!craftcharm``) + the
slice-4 coral sinks (``!curios`` / ``!craftcurio``) and structure Build
routes (the ``!tidepool`` / ``!dock`` / ``!boathouse`` / ``!fishery``
panel opens route straight to their PanelSpecs) — ALL 20 shipped
fishing commands are live; the PENDING roster is empty.
``goldens/fishing/sweep_fish.json`` pins the cast-open bytes (the spent
``fishing_energy`` row + the panel), sweep_forecast the Rain forecast
embed, sweep_sail the deepwater toggle + its ``fishing_venue`` row,
sweep_rod / sweep_rodrecipes the fresh tier-0 rod panels,
sweep_craftrod the not-enough-fish guard, sweep_bait / sweep_craftbait
the fresh bait-less bait shop, sweep_craftpearl the no-pearls guard,
sweep_craftcharm the charm-recipe listing, sweep_curios the 0-coral
curio shelf card, sweep_craftcurio the not-carvable guard, and
sweep_tidepool / sweep_dock / sweep_boathouse / sweep_fishery the
not-built structure panels; the dex embed lives on ``fishing.log``
(sb/domain/fishing/panels.py)."""

from __future__ import annotations


from sb.spec.outcomes import BLOCKED, SUCCESS
from sb.kernel.interaction.handler_kit import (
    Reply,
    ctx_from_request as _ctx_from_req,
)

__all__ = ["Reply", "ensure_handler_refs", "reset_pending_casts_for_tests"]

#: In-flight casts keyed by ``(user_id, guild_id)`` — the shipped
#: ``active_casts`` guard + the cast view's in-memory rolled state
#: (views/fishing/cast_view.py:56-63 @cdb26804), collapsed into one
#: registry: ``cast_open`` (= the shipped ``begin_cast``) rolls the
#: catch and parks it here; the Reel route pops it and commits through
#: the audited ``fishing.cast`` op. In-memory only (ADR-002, accepted
#: for game views — not restart-safe, exactly as shipped). The shipped
#: guard released via the timed view's terminal paths / 45 s timeout;
#: the headless port has no timer, so the guard window IS the oracle
#: ``_VIEW_TIMEOUT``: a pending cast older than that stopped being
#: reelable in the oracle (view timed out, fish got away) — its late
#: Reel click answers the shipped got-away terminal, and ``cast_open``
#: sweeps expired entries opportunistically (the oracle view's
#: on-timeout ``active_casts.discard``, cast_view.py:188) so abandoned
#: lines never accumulate. A timed-out cast's ECONOMICS match the
#: oracle exactly (it spent its energy + bait charge and landed
#: nothing); the oracle's UNPROMPTED got-away message — the background
#: window task's edit — now rides the D-0043 slice-2 got-away timer
#: (``_arm_bite_timers``), which pops the entry at bite_at + window and
#: edits the dead panel terminal in prod; the sweep + the dead panel's
#: own click stay the restart-safe net (scope-doc, codex #373).
#: Entries carry a per-cast ``token``
#: echoed through the panel-args binding, so a Reel click only ever
#: lands its OWN cast — never a newer one that replaced it. The parity
#: harness clears this per case (boot.reset_case_state →
#: :func:`reset_pending_casts_for_tests`).
_PENDING_CASTS: dict[tuple[int, int], dict] = {}

#: The shipped safety-net view timeout (cast_view.py ``_VIEW_TIMEOUT``).
PENDING_CAST_TIMEOUT_SECONDS = 45.0

#: The shipped got-away terminal (cast_view.py _run_bite window expiry —
#: the copy a dead line answers; ``minigame.escape_clue`` may append the
#: trophy tease, the oracle ``_got_away`` soft-fail).
_GOT_AWAY = "🌊 *...the line goes slack. The fish got away.*"

#: The shipped premature-spook terminal (cast_view.py reel_btn, the
#: no-grace branch — verbatim; the oracle passes this straight to
#: ``_terminate_interaction`` WITHOUT the ``_got_away`` wrapper, so a
#: premature spook never appends the trophy clue).
_SPOOKED = ("🌀 You reeled too early — the fish darted off. "
            "*Hold your nerve!*")

#: The shipped fight-escape terminal (cast_view.py _on_fight_tap —
#: verbatim; it rides ``_got_away``, so the trophy clue appends — a
#: reel-fight only ever runs on a trophy).
_SNAPPED = "💥 It gave one last thrash, **snapped the line**, and bolted!"

#: The shipped hook / fight prompts (cast_view.py _on_hooked /
#: _on_fight_tap — verbatim; ride the in-place panel edit).
_HOOKED_BIG_ONE = "🎣 **Hooked a big one!** It dives deep — hang on…"

#: The shipped LATE-reel terminal (cast_view.py reel_btn, the
#: armed-but-out-of-window branch — verbatim; rides ``_got_away``, so
#: the trophy clue appends). The D-0043 slice-2 enforcement flip: a
#: click past bite_at + window (or past a fight round's window) answers
#: this instead of landing.
_TOO_SLOW = "🌊 *...too slow. The fish got away.*"

#: The shipped fake-out tease (cast_view.py _run_bite — verbatim; a
#: GAME_COLOR background edit, the button untouched).
_NIBBLE = "🎣 *...something nibbles at the bait...*"

#: The shipped bite arm (cast_view.py _run_bite → _arm — verbatim:
#: SUCCESS_COLOR embed + the Reel button flipped to the armed
#: label/style).
_BITE_ARM = "🐟 **BITE!** Reel it in — quick!"

#: The shipped fight-round window expiry (cast_view.py _run_fight_round
#: — verbatim; rides ``_got_away``).
_FIGHT_SLACK = "🌊 You let the line go slack — it thrashed free and escaped."

#: The shipped armed-button labels (cast_view.py _arm calls — verbatim;
#: both arm with ButtonStyle.success).
_LABEL_BITE = "Reel it in!"
_LABEL_FIGHT = "Reel!"


def _got_away_text(entry: dict, text: str) -> str:
    """*text* with the trophy clue appended when the parked catch was a
    trophy — the oracle ``_got_away`` soft-fail wrapper, verbatim."""
    from sb.domain.fishing import catalog, minigame

    species = catalog.species_by_name(str(entry.get("species", "")))
    if species is None:
        return text
    clue = minigame.escape_clue(species, int(entry.get("level_before", 0)))
    return f"{text}\n{clue}" if clue else text


def _cancel_cast_timers(entry: dict) -> None:
    """Disarm every one-shot timer a parked cast holds (idempotent) —
    called wherever the entry resolves, is swept, or is popped."""
    for handle in entry.pop("timers", ()):  # type: ignore[union-attr]
        handle.cancel()


def _timer_due(fire_at_f: float) -> bool:
    """Is a wall-fired timer's LOGICAL moment actually here? The one-shot
    timers sleep on the event loop's wall clock, but every deadline is a
    SYSTEM_CLOCK timestamp — in prod the two agree and this always
    passes (the 50 ms slack absorbs wall-vs-monotonic drift); under the
    parity harness the logical clock only moves when a step advances it,
    so a timer that wall-fires mid-case (replay wall time can exceed the
    bite delay — DB snapshots between steps) reads a logical now BEFORE
    its deadline and must no-op instead of popping a cast the driven
    steps still own."""
    from sb.kernel.workflow.context import SYSTEM_CLOCK

    return SYSTEM_CLOCK().timestamp() >= fire_at_f - 0.05


async def _push_cast_edit(entry: dict, prompt: str, *,
                          style: str = "", label: str = "",
                          button_style: str = "", disable: bool = False,
                          expire: bool = False) -> None:
    """Edit the parked cast's live panel with NO interaction — the oracle
    background-task ``_edit_message``/``_fail`` edits riding the kernel
    push seam (``push_session_refresh`` → the ``_message_editor`` port).
    Headless/parity: no editor installed ⇒ EDIT_UNAVAILABLE no-op; a
    gone session/message ⇒ EDIT_MISSING no-op (the oracle's
    message-gone debug-and-skip)."""
    from sb.kernel.panels.engine import push_session_refresh

    message_key = entry.get("panel_key")
    if not message_key:
        return
    params: dict = {"cast_prompt": prompt}
    if style:
        params["cast_prompt_style"] = style
    if label:
        params["cast_button_label"] = label
    if button_style:
        params["cast_button_style"] = button_style
    if disable:
        params["cast_disable"] = True
    await push_session_refresh(
        str(message_key), params=params, actor=entry.get("actor"),
        guild_id=entry.get("guild_id"), expire=expire)


def _arm_bite_timers(key: tuple[int, int], entry: dict) -> None:
    """Arm the cast's live-wait cues (the oracle ``_run_bite`` background
    task as three one-shot timers): the fake-out nibble (only when the
    cast rolled one AND the lead fits — the oracle guard
    ``delay − FAKEOUT_LEAD > BITE_DELAY_FLOOR``), the 🐟 BITE! arm at
    bite_at, and the unprompted got-away at bite_at + window (pop the
    entry, terminal edit, NO DB write — the paid cast's economics stand).
    Every callback is identity-guarded so a resolved/replaced cast's
    stale timer exits instead of false-failing (the oracle ``_round_id``
    staleness token), AND due-guarded on SYSTEM_CLOCK (:func:`_timer_due`)
    so a wall-fired timer whose LOGICAL moment has not arrived is a
    no-op — in prod wall == logical and the guard always passes; in
    parity the logical clock never reaches the deadline inside a driven
    case (a step advances it 30 s while replay wall time crawls past the
    delay), so an in-case wall fire can never pop a cast the goldens
    still own. Enforcement itself NEVER rides these timers — it is
    timestamp math on SYSTEM_CLOCK in fish_route."""
    from sb.domain.fishing import minigame
    from sb.kernel.panels import timers

    uid, _gid = key
    delay = float(entry["bite_at_f"]) - float(entry["cast_at_f"])
    window = float(entry["reaction_window"])
    bite_at = float(entry["bite_at_f"])
    handles = []

    async def _nibble() -> None:
        if _PENDING_CASTS.get(key) is not entry or entry.get("fight"):
            return
        if not _timer_due(bite_at - minigame.FAKEOUT_LEAD):
            return
        await _push_cast_edit(entry, _NIBBLE)

    async def _bite() -> None:
        if _PENDING_CASTS.get(key) is not entry or entry.get("fight"):
            return
        if not _timer_due(bite_at):
            return
        await _push_cast_edit(entry, _BITE_ARM, style="green",
                              label=_LABEL_BITE, button_style="success")

    async def _got_away() -> None:
        if _PENDING_CASTS.get(key) is not entry or entry.get("fight"):
            return
        if not _timer_due(bite_at + window):
            return
        # unresolved past the window — the oracle ``_fail``: pop the
        # paid cast (energy/bait spent, NO write) + the terminal edit
        # (ERROR_COLOR, button disabled, session torn down).
        del _PENDING_CASTS[key]
        _cancel_cast_timers(entry)
        await _push_cast_edit(
            entry, _got_away_text(entry, _GOT_AWAY), style="red",
            label=_LABEL_BITE, button_style="success", disable=True,
            expire=True)

    if (entry.get("fakeout")
            and delay - minigame.FAKEOUT_LEAD > minigame.BITE_DELAY_FLOOR):
        handles.append(timers.schedule(
            delay - minigame.FAKEOUT_LEAD, _nibble,
            name=f"fishing:nibble:{uid}"))
    handles.append(timers.schedule(delay, _bite,
                                   name=f"fishing:bite:{uid}"))
    handles.append(timers.schedule(delay + window, _got_away,
                                   name=f"fishing:gotaway:{uid}"))
    entry["timers"] = handles


def _arm_fight_timers(key: tuple[int, int], entry: dict,
                      now_f: float) -> None:
    """Arm one reel-fight round (the oracle ``_run_fight_round``): the
    0.8 s suspense beat then the 💪 keep-reeling arm at
    ``fight_round_open_f``, and the round's got-away expiry one window
    later. Re-armed by the hook and by every non-final tap; the round
    number guard (taps_done at arm time) is the oracle staleness token."""
    from sb.kernel.panels import timers

    uid, _gid = key
    open_f = float(entry["fight_round_open_f"])
    window = float(entry["reaction_window"])
    round_no = int(entry.get("taps_done", 0))
    bar = _tension_bar(round_no, int(entry.get("taps_required", 0)))
    prompt = f"💪 **It's a big one — it dives!** Keep reeling!\n`{bar}`"
    handles = []

    def _stale() -> bool:
        return (_PENDING_CASTS.get(key) is not entry
                or not entry.get("fight")
                or int(entry.get("taps_done", 0)) != round_no)

    async def _arm_round() -> None:
        if _stale() or not _timer_due(open_f):
            return
        await _push_cast_edit(entry, prompt, label=_LABEL_FIGHT,
                              button_style="success")

    async def _round_expired() -> None:
        if _stale() or not _timer_due(open_f + window):
            return
        del _PENDING_CASTS[key]
        _cancel_cast_timers(entry)
        await _push_cast_edit(
            entry, _got_away_text(entry, _FIGHT_SLACK), style="red",
            label=_LABEL_FIGHT, button_style="success", disable=True,
            expire=True)

    handles.append(timers.schedule(max(0.0, open_f - now_f), _arm_round,
                                   name=f"fishing:fight:{uid}"))
    handles.append(timers.schedule(
        max(0.0, open_f + window - now_f), _round_expired,
        name=f"fishing:fight-expire:{uid}"))
    entry["timers"] = handles


def _tension_bar(done: int, total: int) -> str:
    """A tiny reel-progress bar, e.g. ``▰▰▱▱`` (2 of 4 reeled in) — the
    shipped cast_view.py ``_tension_bar``, verbatim."""
    done = max(0, min(done, total))
    return "▰" * done + "▱" * (total - done)


async def _refresh_cast_panel(req, prompt: str) -> bool:
    """Edit the live cast panel IN PLACE with *prompt* as its whole
    description — the oracle ``_edit_message`` shape (a bare description
    embed, the Reel button kept) through the panels refresh seam (the
    deathmatch/settings ``refresh_session_view`` precedent). Returns
    False when the session is gone (restart/eviction) so the caller can
    degrade to a text reply."""
    from sb.kernel.panels.engine import refresh_session_view

    message = getattr(req.origin, "message", None)
    message_key = str(getattr(message, "id", "") or "")
    return await refresh_session_view(
        req, message_key=message_key,
        params={**dict(req.args), "cast_prompt": prompt})

#: Per-cast identity tokens — monotonic, process-local, never rendered
#: and never persisted (they ride the in-memory panel-args binding only).
_cast_token_counter = 0


def _next_cast_token() -> int:
    global _cast_token_counter
    _cast_token_counter += 1
    return _cast_token_counter


def _sweep_expired_casts(now: int) -> None:
    """Drop every pending cast past the oracle view timeout — the
    opportunistic stand-in for the shipped view's on-timeout
    ``active_casts.discard`` (cast_view.py:188, codex #373)."""
    stale = [key for key, entry in _PENDING_CASTS.items()
             if now - entry["rolled_at"] > PENDING_CAST_TIMEOUT_SECONDS]
    for key in stale:
        _cancel_cast_timers(_PENDING_CASTS[key])
        del _PENDING_CASTS[key]


def reset_pending_casts_for_tests() -> None:
    global _cast_token_counter
    for entry in _PENDING_CASTS.values():
        _cancel_cast_timers(entry)
    _PENDING_CASTS.clear()
    _cast_token_counter = 0


def _fmt_wait(seconds: int) -> str:
    """Human "ready in" — ``45s`` / ``2m 05s`` (the shipped
    services/fishing_workflow.py helper)."""
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60:02d}s"


def _embed(title: str, description: str):
    """The shipped ``discord.Embed(title=…, color=_FISHING_COLOR)`` frame
    (_FISHING_COLOR = INFO blue 3447003 — the goldens pin the byte)."""
    from sb.kernel.panels.render import RenderedEmbed

    return RenderedEmbed(title=title, description=description,
                         style_token="blue")


async def _card(req, embed) -> Reply:
    """Present one read card as the shipped public embed reply
    (``ctx.send(embed=…)`` — the mining.card open_panel lane)."""
    import dataclasses

    from sb.kernel.panels.engine import open_panel
    from sb.spec.refs import PanelRef

    await open_panel(PanelRef("fishing.card"), dataclasses.replace(
        req, args={**dict(req.args), "_card": embed}))
    return Reply(SUCCESS, None)


async def _angler_name(user_id: int, guild_id: int) -> str:
    """The leaderboard row's resolved display name (fishing_cog.py
    fishtop/trophies: ``resources.resolve_member`` →
    ``member.display_name``) through the guild-directory read port (the
    panels ``_member_display_name`` recipe) — degrading to the shipped
    ``User {id}`` copy when the member doesn't resolve, never invented
    data."""
    try:
        from sb.domain.utility.service import guild_directory

        member = await guild_directory().member_info(guild_id, user_id)
        name = member.tag.rsplit("#", 1)[0]
    except Exception:  # noqa: BLE001 — unresolved ⇒ shipped fallback
        name = ""
    return name or f"User {user_id}"


def _register() -> None:
    from sb.spec.refs import HandlerRef, handler, is_registered

    if is_registered(HandlerRef("fishing.fish_route")):
        return

    @handler("fishing.cast_open")
    async def cast_open(req) -> Reply:
        """!fish / the hub Cast button — the FULL shipped ``begin_cast``
        (services/fishing_workflow.py:384-518 @cdb26804): active-cast
        guard → one structures read (Boathouse regen + Tide Pool / Dock
        / Fishery knobs) → settle/gate at the Boathouse-adjusted
        interval → read rod/venue/weather/bait/gear → compound
        ``effective_pull`` / ``effective_bite_speed`` / the fishery
        ``double_catch_chance`` → ROLL the catch now (the shipped
        ``roll_cast`` timing; energy is only spent once a catch actually
        rolled, so a catalog-load failure never charges) → spend energy
        → spend one bait charge (a missed reel still spends both — the
        shipped "charge per attempt" rule) → park the rolled cast in the
        pending registry → open the waiting-for-a-bite panel. The energy
        write is the shipped direct game-state write (autocommit,
        non-money — the energy-spend posture); the bait consume is a
        single conditional relative decrement
        (``store.consume_bait_charge``) so a coin-bought bait load
        committing behind ``lock_bait_slot`` mid-cast is never clobbered
        by a stale absolute write-back (the #213/#217 doctrine — bait is
        money-bearing; user-visible bytes unchanged);
        goldens/fishing/sweep_fish pins the spent fresh-bar row + the
        shore panel bytes (every knob reads exactly neutral on a fresh
        player, so the wired cast is byte-identical there)."""
        import dataclasses

        from sb.domain.fishing import bait as bait_mod
        from sb.domain.fishing import catalog
        from sb.domain.fishing import energy as energy_mod
        from sb.domain.fishing import gear as gear_mod
        from sb.domain.fishing import minigame
        from sb.domain.fishing import ops as ops_mod
        from sb.domain.fishing import rods as rods_mod
        from sb.domain.fishing import store
        from sb.domain.fishing import venue as venue_mod
        from sb.domain.fishing import weather as weather_mod
        from sb.domain.fishing.panels import CAST_PANEL_ID
        from sb.domain.games import xp as game_xp
        from sb.domain.games.store import game_xp_rows
        from sb.domain.mining import character
        from sb.domain.mining import structures as structures_mod
        from sb.domain.mining.store import (
            get_equipment,
            get_skills,
            get_structures,
        )
        from sb.kernel.panels.engine import open_panel
        from sb.kernel.workflow.context import SYSTEM_CLOCK
        from sb.spec.refs import PanelRef

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        # the timing fields need sub-second resolution (a shore bite can
        # land 1.5 s after the cast), so the float timestamp is kept
        # beside the int the 45 s sweep / energy math always used.
        now_f = SYSTEM_CLOCK().timestamp()
        now = int(now_f)
        # the shipped one-line-in-the-water guard (cast_view.py
        # prepare_cast L86-87); a pending cast past the oracle view
        # timeout would have timed out live — sweep it (and every other
        # expired line) instead: its got-away terminal surfaces on the
        # dead panel's own Reel click.
        pending = _PENDING_CASTS.get((uid, gid))
        if (pending is not None
                and now - pending["rolled_at"]
                <= PENDING_CAST_TIMEOUT_SECONDS):
            return Reply(BLOCKED,
                         "🎣 You've already got a line in the water — "
                         "reel that one in first!")
        _sweep_expired_casts(now)
        # RESERVE the slot BEFORE the first await: no await sits between
        # the guard read above and this write, so two Cast interactions
        # for one player on one event loop can never both pass the guard
        # and double-spend energy/bait (codex #373 P1 — the oracle had
        # the same TOCTOU: its guard read at prepare_cast L86 but its
        # ``active_casts.add`` only ran in view.start() L184, after
        # begin_cast's awaits; the reservation closes it). Every
        # non-parked exit below releases the reservation.
        token = _next_cast_token()
        reservation = {"rolled_at": now, "token": token}
        _PENDING_CASTS[(uid, gid)] = reservation
        parked = False
        try:
            # ONE structures read serves every structure knob AND the
            # Boathouse regen speed-up, known before the settle so the
            # out-of-energy gate + "ready in" wait already reflect it
            # (begin_cast L393-401). Unbuilt ⇒ ×1.0 ⇒ REGEN_SECONDS.
            built = await get_structures(uid, gid)
            regen_seconds = energy_mod.regen_seconds_for(
                structures_mod.boathouse_regen_mult(
                    built.get(structures_mod.BOATHOUSE, 0)))
            cur, ts = await store.get_fishing_energy(uid, gid)
            state = energy_mod.EnergyState(cur, ts)
            settled = energy_mod.settle(state, now,
                                        regen_seconds=regen_seconds)
            if not energy_mod.can_cast(settled):
                wait = energy_mod.seconds_until(
                    state, now, energy_mod.CAST_COST,
                    regen_seconds=regen_seconds)
                return Reply(BLOCKED,
                             "🎣 You're out of energy — let the line "
                             "rest. Ready to cast again in "
                             f"**{_fmt_wait(wait)}**.")
            rod = rods_mod.rod_for_tier(
                await store.get_rod_tier(uid, gid))
            profile = venue_mod.profile_for(
                await store.get_fishing_venue(uid, gid))
            weather = weather_mod.current_weather()
            # the shipped get_active_bait resolve (fishing_workflow.py
            # L368-381): a stale key / non-positive charges read as none.
            bait_key, bait_charges = await store.get_active_bait(uid, gid)
            bait = bait_mod.bait_by_key(bait_key)
            if bait is None or bait_charges <= 0:
                bait, bait_charges = None, 0
            # the 4th "how-well" knob: equipped fishing gear (L430-435).
            gear_stats = character.character_stats(
                await get_equipment(uid, gid),
                await get_skills(uid, gid))
            gear_pull = gear_mod.fishing_pull_mult(gear_stats)
            gear_bite_speed = gear_mod.fishing_bite_speed_mult(gear_stats)
            # the structure knobs (L441-451): all exactly neutral unbuilt.
            tide_pool_level = built.get(structures_mod.TIDE_POOL, 0)
            tide_pool_pull = structures_mod.tide_pool_pull_mult(
                tide_pool_level)
            dock_level = built.get(structures_mod.DOCK, 0)
            dock_bite_speed = structures_mod.dock_bite_speed_mult(
                dock_level)
            fishery_level = built.get(structures_mod.FISHERY, 0)
            double_catch_chance = (
                ops_mod.BONUS_CATCH_CHANCE
                + structures_mod.fishery_bonus_chance(fishery_level))
            # the compound formulas — begin_cast L458-471 verbatim:
            # rod × bait × weather × gear × tide pool (pull) and
            # rod × bait × weather × gear × dock (bite speed).
            effective_pull = (
                rod.rarity_pull
                * (bait.rarity_pull if bait else 1.0)
                * weather.rarity_mult
                * gear_pull
                * tide_pool_pull
            )
            effective_bite_speed = (
                rod.bite_speed
                * (bait.bite_speed if bait else 1.0)
                * weather.bite_speed_mult
                * gear_bite_speed
                * dock_bite_speed
            )
            # roll the cast NOW — the shipped roll_cast
            # (fishing_workflow.py L127-171): xp read → level_before →
            # the weighted species roll on the module's private cast RNG
            # (runner-armed for goldens).
            xp_rows = {str(r["game"]): int(r["xp"])
                       for r in await game_xp_rows(uid, gid)}
            level_before = catalog.fishing_level_from_xp(
                xp_rows.get(game_xp.GAME_FISHING, 0))
            catch = ops_mod.roll_catch(level_before, ops_mod.cast_rng(),
                                       rarity_pull=effective_pull,
                                       venue=profile.key)
            if catch is None:
                # the shipped quiet-venue guard (begin_cast L480-488) —
                # energy is never spent on a catalog-load failure.
                return Reply(BLOCKED,
                             f"{profile.emoji} The {profile.name.lower()} "
                             "is quiet right now — try later.")
            # --- the D-0043 slice-1 timing rolls, STRICTLY AFTER the
            # catch roll on the SAME private cast RNG: the catch draws
            # (species choices → weight uniform) stay first so every
            # pinned species/weight trajectory in the existing cast-write
            # goldens is unmoved; the timing draws (bite uniform →
            # fake-out random) EXTEND the stream after them. Reordering
            # these shifts every cast-write golden — don't. This consumes
            # the previously-discarded effective_bite_speed (the oracle
            # _run_bite, cast_view.py) at the venue's bite band.
            bite_delay = minigame.roll_bite_delay(
                ops_mod.cast_rng(),
                speed=effective_bite_speed,
                lo=profile.bite_delay_min,
                hi=profile.bite_delay_max,
                floor=profile.bite_delay_floor)
            # rolled NOW (not in slice 2) so the fake-out's slice-2
            # visibility wiring never shifts an already-pinned RNG
            # trajectory; outcome-inert this slice — a pre-bite click
            # resolves premature whether or not the shake tempted it.
            fakeout = minigame.roll_fakeout(ops_mod.cast_rng())
            # the fairness knob compound (oracle FishingCastView.__init__):
            # every reaction window = the venue's base + the rod's bonus.
            reaction_window = profile.reaction_window + rod.window_bonus
            trophy = minigame.is_trophy(catch.species, level_before)
            taps_required = (minigame.reel_fight_taps(catch.species)
                             if trophy else 0)
            spent = energy_mod.spend(state, now,
                                     regen_seconds=regen_seconds)
            await store.set_fishing_energy(uid, gid, spent.current,
                                           spent.updated_at)
            # consume one bait charge — only now that the cast is
            # actually happening (begin_cast L493-502: the same "charge
            # per attempt" rule as energy; the pack clears at 0 left).
            # ONE conditional relative decrement, never an absolute
            # write-back of the stale read above: the buy/craft legs
            # stack/replace the loadout behind lock_bait_slot in their
            # own txn, and this lockless leg racing them with
            # set_active_bait(bait_charges - 1) would eat a purchase's
            # coin-bought charges (or clear a freshly replaced pack) —
            # the #213/#217 read-then-settle lost update on a
            # money-bearing slot. consume_bait_charge decrements the
            # COMMITTED count (and clears the pack in-statement at 0);
            # None = the loadout was swapped/emptied concurrently — the
            # shipped "no bait" posture (nothing to spend), the cast
            # keeps the effects it rolled with.
            charges_left = 0
            if bait is not None:
                remaining = await store.consume_bait_charge(
                    uid, gid, bait.key)
                if remaining is not None:
                    charges_left = remaining
            _PENDING_CASTS[(uid, gid)] = {
                "rolled_at": now,
                "token": token,
                "species": catch.species.name,
                "weight": catch.weight,
                "venue": profile.key,
                "double_catch_chance": double_catch_chance,
                "level_before": level_before,
                # --- D-0043 slice-1 timing state (floats: the int
                # truncation above stays confined to the 45 s sweep /
                # energy fields) ---
                "cast_at_f": now_f,
                "bite_at_f": now_f + bite_delay,
                "reaction_window": reaction_window,
                "grace": rod.premature_grace,
                "grace_used": False,
                "fakeout": fakeout,        # stored; outcome-inert (slice 2)
                "trophy": trophy,
                "taps_required": taps_required,
                "taps_done": 0,
                "fight": False,
                "rod_name": rod.name,      # the grace-forgive copy
                "escape_resist": rod.escape_resist,
                "base_escape": profile.base_escape,
            }
            parked = True
        finally:
            # release the reservation on every non-parked exit (the
            # BLOCKED gates above, or a raise) — never a parked cast.
            if (not parked
                    and _PENDING_CASTS.get((uid, gid)) is reservation):
                del _PENDING_CASTS[(uid, gid)]
        # the panel opens OUTSIDE the try: a failed send keeps the
        # rolled, PAID cast parked and reelable (its costs are spent).
        message_key = await open_panel(
            PanelRef(CAST_PANEL_ID),
            dataclasses.replace(
                req, args={
                    **dict(req.args),
                    "cast_energy": spent.current,
                    "cast_venue": profile.key,
                    "cast_bait_key": bait.key if bait is not None else "",
                    "cast_bait_charges_left": charges_left,
                    "cast_gear_bonus":
                        gear_mod.has_fishing_bonus(gear_stats),
                    "cast_tide_pool": tide_pool_level > 0,
                    "cast_dock": dock_level > 0,
                    # the cast's identity — rides the in-memory
                    # panel-args binding to the Reel click, so a stale
                    # Reel can never pop a newer cast (codex #373 P1).
                    "cast_token": token,
                }))
        # --- D-0043 slice 2: arm the live-wait cues on the freshly
        # opened panel (the oracle view.start() → _run_bite task). The
        # push-edit context rides the entry; edits no-op headless
        # (EDIT_UNAVAILABLE) and enforcement never depends on them.
        entry = _PENDING_CASTS.get((uid, gid))
        if entry is not None and entry.get("token") == token:
            entry["panel_key"] = message_key
            entry["actor"] = req.actor
            entry["guild_id"] = gid
            _arm_bite_timers((uid, gid), entry)
        return Reply(SUCCESS, None)

    @handler("fishing.fish_route")
    async def fish_route(req) -> Reply:
        """The cast panel's Reel button — resolves the pending cast
        rolled at cast time against its D-0043 slice-1 timing state
        (the shipped cast_view.py ``reel_btn`` ladder), then lands it
        through the audited ``fishing.cast`` K7 op (dex upsert + pearl /
        coral / fish materials + game XP in one leg txn):

        * BEFORE the rolled bite moment (fake-out clicks included) —
          the rod's ``premature_grace`` can forgive ONE slip per cast
          (the oracle 😅 panel edit; the line stays in the water), else
          the spook terminal (``_SPOOKED``, no DB write, cast gone).
        * IN the reaction window, ordinary fish — the commit, unchanged.
        * IN the window, trophy — the reel-fight: the hook click flips
          the panel to ``_HOOKED_BIG_ONE``; each further click is one
          tap with a per-tap ``roll_escape`` (venue ``base_escape`` ×
          rod ``escape_resist``) — snap free (``_SNAPPED`` + the trophy
          clue, no write) or advance the ▰▰▱▱ bar; the last tap commits.
          Fight rounds open ``FIGHT_INTER_ROUND_DELAY`` after the
          previous resolve (the oracle suspense beat): a click before
          the round opens is the oracle mash-ignore (deferred, no
          state), one past the round's window is too-slow.
        * AFTER the window (D-0043 slice 2 — ENFORCED now that the
          push-edit seam makes the bite visible): the oracle too-slow
          got-away terminal (``_TOO_SLOW`` + the trophy clue), no DB
          write. Enforcement is ``minigame.reel_is_in_time`` timestamp
          math on SYSTEM_CLOCK — never the wall-clock timers, so parity
          decides identically on the logical clock. In prod the armed
          got-away timer usually pops the entry first and a later click
          answers the stale-token ``_GOT_AWAY`` terminal instead.

        The click carries the cast's identity token (the panel-args
        binding), so a STALE Reel — the cast timed out, or a newer cast
        replaced it — answers the shipped got-away terminal (cast_view
        window-expiry copy + the ``_got_away`` trophy clue) instead of
        landing a dead fish or popping a newer cast (codex #373 P1);
        the 45 s pending sweep stays the OUTER bound around the whole
        ladder. The entry is popped only for the commit and RESTORED on
        a failed commit (codex #373 P2). A token-less Reel with no
        pending cast keeps the leg's roll-at-commit starter seam (the
        shipped legacy ``fish()`` — the direct-invocation path)."""
        from sb.domain.fishing import catalog, minigame
        from sb.domain.fishing import ops as ops_mod
        from sb.kernel.workflow import engine
        from sb.kernel.workflow.context import SYSTEM_CLOCK
        from sb.spec.refs import WorkflowRef

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        now_f = SYSTEM_CLOCK().timestamp()
        now = int(now_f)
        key = (uid, gid)
        token = req.args.get("cast_token")
        entry = _PENDING_CASTS.get(key)
        if entry is not None and "species" not in entry:
            entry = None  # a mid-flight reservation is never reelable
        if token is not None and (entry is None
                                  or entry.get("token") != token):
            # this Reel belongs to an OLDER cast whose line is dead —
            # timed out and swept, or replaced by a newer cast (which
            # stays parked, untouched). The oracle's timed-out view was
            # no longer reelable; answer its terminal.
            return Reply(BLOCKED, _GOT_AWAY)
        if (entry is not None
                and now - entry["rolled_at"] > PENDING_CAST_TIMEOUT_SECONDS):
            # the oracle view timed out at 45 s — the PAID cast got away
            # (the shipped economics: energy + bait already spent, no
            # write); surface it with the oracle ``_got_away`` soft-fail
            # clue at the cast's own level_before.
            _cancel_cast_timers(entry)
            del _PENDING_CASTS[key]
            species = catalog.species_by_name(str(entry["species"]))
            clue = (minigame.escape_clue(species,
                                         int(entry["level_before"]))
                    if species is not None else None)
            return Reply(BLOCKED,
                         f"{_GOT_AWAY}\n{clue}" if clue else _GOT_AWAY)
        # ------- the D-0043 slice-1 click-gated resolution ladder -------
        # (timing rolls draw on the SAME private cast RNG as the cast /
        # commit draws, so a runner-armed seed pins the whole trajectory;
        # entries missing the timing fields — the pre-slice shape only
        # tests construct — resolve as in-time, i.e. the old behavior.)
        if entry is not None and entry.get("fight"):
            # mid-reel-fight: this click is one tap — but only inside
            # its round's window (D-0043 slice 2; entries armed before
            # the flip carry no round timestamp and stay in-time).
            round_open = entry.get("fight_round_open_f")
            if round_open is not None:
                if now_f < float(round_open):
                    # between fight rounds — the oracle mash-ignore
                    # (safe_defer: no state moves, no rng draw).
                    return Reply(SUCCESS, None)
                if not minigame.reel_is_in_time(
                        now_f - float(round_open),
                        float(entry.get("reaction_window", 0.0))):
                    # the round's window closed — too slow (the oracle
                    # reel_btn late branch; clue appends, a fight IS a
                    # trophy). No write, the paid cast is gone.
                    _cancel_cast_timers(entry)
                    del _PENDING_CASTS[key]
                    return Reply(BLOCKED, _got_away_text(entry, _TOO_SLOW))
            species = catalog.species_by_name(str(entry["species"]))
            if species is not None and minigame.roll_escape(
                    species,
                    escape_resist=float(entry.get("escape_resist", 0.0)),
                    base_escape=float(
                        entry.get("base_escape",
                                  minigame.SHORE_ESCAPE_CHANCE)),
                    rng=ops_mod.cast_rng()):
                # snapped free — terminal, the paid cast is gone, no
                # write; the clue always appends (a fight IS a trophy).
                _cancel_cast_timers(entry)
                del _PENDING_CASTS[key]
                clue = minigame.escape_clue(species,
                                            int(entry["level_before"]))
                return Reply(BLOCKED,
                             f"{_SNAPPED}\n{clue}" if clue else _SNAPPED)
            entry["taps_done"] = int(entry.get("taps_done", 0)) + 1
            if entry["taps_done"] < int(entry.get("taps_required", 0)):
                # the next round opens after the oracle suspense beat —
                # re-arm its live cues (the oracle re-spawned
                # _run_fight_round per tap).
                _cancel_cast_timers(entry)
                entry["fight_round_open_f"] = (
                    now_f + minigame.FIGHT_INTER_ROUND_DELAY)
                _arm_fight_timers(key, entry, now_f)
                bar = _tension_bar(int(entry["taps_done"]),
                                   int(entry["taps_required"]))
                prompt = f"💪 Reeling it in… `{bar}`"
                if not await _refresh_cast_panel(req, prompt):
                    return Reply(SUCCESS, prompt)
                return Reply(SUCCESS, None)
            # the last tap lands it — fall through to the commit.
        elif entry is not None:
            if now_f < float(entry.get("bite_at_f", 0.0)):
                # reeled BEFORE the bite (a fake-out click lands here too
                # — the shake rides FAKEOUT_LEAD ahead of the real bite).
                if (not entry.get("grace_used")
                        and minigame.roll_premature_grace(
                            float(entry.get("grace", 0.0)),
                            ops_mod.cast_rng())):
                    # the rod steadies it — spent once per cast; the line
                    # stays in the water and the parked cast stays live.
                    # The armed bite timers stay armed too: the oracle's
                    # still-running bite task arms the real bite after a
                    # forgiven slip (cast_view.py reel_btn @bbc524e).
                    entry["grace_used"] = True
                    prompt = (
                        "😅 *You twitch the rod too soon — but the "
                        f"{entry.get('rod_name', 'rod')} steadies it. "
                        "The line's still in the water… hold your "
                        "nerve.*")
                    if not await _refresh_cast_panel(req, prompt):
                        return Reply(SUCCESS, prompt)
                    return Reply(SUCCESS, None)
                # spooked it (no grace left / bare rod) — terminal, the
                # paid cast is gone, no write (oracle: no trophy clue on
                # a premature spook).
                _cancel_cast_timers(entry)
                del _PENDING_CASTS[key]
                return Reply(BLOCKED, _SPOOKED)
            if ("bite_at_f" in entry
                    and not minigame.reel_is_in_time(
                        now_f - float(entry["bite_at_f"]),
                        float(entry.get("reaction_window", 0.0)))):
                # bite_at + window < now — TOO SLOW (D-0043 slice 2: the
                # enforcement flip; the oracle reel_btn late branch, clue
                # appended for a trophy). No write, the paid cast is
                # gone. Pre-slice entries (no bite_at_f) stay in-time.
                _cancel_cast_timers(entry)
                del _PENDING_CASTS[key]
                return Reply(BLOCKED, _got_away_text(entry, _TOO_SLOW))
            # bite_at ≤ now ≤ bite_at + window — in the window.
            if entry.get("trophy") and int(entry.get("taps_required",
                                                     0)) > 0:
                # hooked a big one — flip into the reel-fight; the
                # commit waits for the taps. The bite cues retire and
                # the first fight round arms (the oracle _on_hooked →
                # _run_fight_round spawn).
                _cancel_cast_timers(entry)
                entry["fight"] = True
                entry["fight_round_open_f"] = (
                    now_f + minigame.FIGHT_INTER_ROUND_DELAY)
                _arm_fight_timers(key, entry, now_f)
                if not await _refresh_cast_panel(req, _HOOKED_BIG_ONE):
                    return Reply(SUCCESS, _HOOKED_BIG_ONE)
                return Reply(SUCCESS, None)
            # ordinary fish in time — fall through to the commit.
        params: dict = {}
        if entry is not None:
            # pop EXCLUSIVELY for the commit (two racing Reels can never
            # double-land one cast) … — the live cues retire with it (a
            # restored-on-failed-commit entry stays clickable; only its
            # edits are lost, never the window math).
            _cancel_cast_timers(entry)
            _PENDING_CASTS.pop(key, None)
            params = {k: entry[k]
                      for k in ("species", "weight", "venue",
                                "double_catch_chance", "level_before")}
        result = await engine.run(WorkflowRef("fishing.cast"),
                                  _ctx_from_req(req, params))
        if result.outcome != SUCCESS:
            # … and RESTORE the paid cast on a failed commit so it stays
            # landable — unless a newer cast already took the slot.
            if entry is not None and key not in _PENDING_CASTS:
                _PENDING_CASTS[key] = entry
            return Reply(result.outcome,
                         result.user_message or "The line came back "
                                                "empty.")
        after = (result.after or {}).get("cast", {})
        return Reply(SUCCESS, after.get("message", ""))

    @handler("fishing.forecast_view")
    async def forecast_view(req) -> Reply:
        """!forecast — the shipped date-seeded forecast embed
        (fishing_cog.py ``forecast``: _FISHING_COLOR blue; title
        ``{emoji} Today's fishing forecast: {name}``, description
        ``{blurb}\\n\\n**Effect on every cast:** {effect}``, footer
        ``Same for everyone today · 🎣 !fish to cast`` —
        goldens/fishing/sweep_forecast pins the capture-day Rain bytes;
        the replay seam is CAPTURE_WORLD_WEATHER, trap 36a)."""
        from sb.domain.fishing import weather as weather_mod
        from sb.kernel.panels.render import RenderedEmbed

        w = weather_mod.current_weather()
        embed = RenderedEmbed(
            title=f"{w.emoji} Today's fishing forecast: {w.name}",
            description=(f"{w.blurb}\n\n**Effect on every cast:** "
                         f"{weather_mod.effect_text(w)}"),
            footer="Same for everyone today · 🎣 !fish to cast",
            style_token="blue")
        return await _card(req, embed)

    @handler("fishing.sail_route")
    async def sail_route(req) -> Reply:
        """!sail / the hub ⛵ Set sail / Dock button — the shipped venue
        toggle (fishing_cog.py ``sail`` → services/fishing_workflow.py
        ``toggle_venue``/``set_venue``): flip shore ↔ deepwater and
        persist it. The write is the shipped direct game-state upsert
        (autocommit, non-money, no audit — the energy-spend posture);
        goldens/fishing/sweep_sail pins the deepwater message + the
        minted ``fishing_venue`` row."""
        from sb.domain.fishing import store, venue as venue_mod

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        current = await store.get_fishing_venue(uid, gid)
        profile = venue_mod.profile_for(venue_mod.toggle(current))
        await store.set_fishing_venue(uid, gid, profile.key)
        if profile.key == venue_mod.DEEPWATER:
            message = (
                f"{profile.emoji} **You set sail for deepwater.** Rare "
                "boat-only fish lurk here — they bite slower and fight "
                "harder to break free, so a rod with good escape-resist "
                "pays off. Cast with `!fish`.")
        else:
            message = (
                f"{profile.emoji} **You docked back on the shore.** "
                "Relaxed casting for the everyday catch. Cast with "
                "`!fish`.")
        return Reply(SUCCESS, message)

    async def _op_after(req, op_key: str, params: dict | None = None):
        """Run a one-leg fishing op; (outcome-reply, after) — reply is
        None on SUCCESS so the caller composes the shipped copy from
        `after` (the mining service `_op_after` shape)."""
        from sb.kernel.workflow import engine
        from sb.spec.refs import WorkflowRef

        result = await engine.run(WorkflowRef(op_key),
                                  _ctx_from_req(req, dict(params or {})))
        if result.outcome != SUCCESS:
            return (Reply(result.outcome,
                          result.user_message or "Couldn't do that."), {})
        return (None, next(iter((result.after or {}).values()), {}))

    def _rest_arg(req) -> str:
        """The invocation's rest-string argument — a select pick
        (``values``) wins over the typed tail (``argv``), mirroring the
        shipped keyword-rest ``*, bait: str = ""`` cog signature and the
        select callbacks' direct-key calls."""
        values = tuple(req.args.get("values", ()) or ())
        if values:
            return str(values[0])
        return " ".join(str(t) for t in
                        tuple(req.args.get("argv", ()) or ()))

    @handler("fishing.rod_shop")
    async def rod_shop(req) -> Reply:
        """!rod — open the rod shop panel (fishing_cog.py ``rod``:
        build_rod_embed + RodShopView). A pure read — the open renders
        the live tier/balance and writes nothing;
        goldens/fishing/sweep_rod pins the fresh tier-0 bytes."""
        import dataclasses

        from sb.domain.fishing.panels import ROD_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef(ROD_PANEL_ID),
                         dataclasses.replace(req, args=dict(req.args)))
        return Reply(SUCCESS, None)

    @handler("fishing.rodrecipes_view")
    async def rodrecipes_view(req) -> Reply:
        """!rodrecipes — open the rod recipe browser (fishing_cog.py
        ``rodrecipes``: build_recipe_panel). A pure read;
        goldens/fishing/sweep_rodrecipes pins the fresh tier-0 bytes."""
        import dataclasses

        from sb.domain.fishing.panels import ROD_RECIPES_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef(ROD_RECIPES_PANEL_ID),
                         dataclasses.replace(req, args=dict(req.args)))
        return Reply(SUCCESS, None)

    @handler("fishing.craftrod_route")
    async def craftrod_route(req) -> Reply:
        """!craftrod / the rod panels' craft buttons — craft the next rod
        up the ladder from caught fish (fishing_cog.py ``craftrod`` →
        services/fishing_workflow.py ``craft_rod``). The maxed /
        not-enough-fish refusals are computed as PURE READS (tier +
        inventory + the smallest-first spend plan) so the failed attempt
        writes no row, exactly as the oracle's txn never opens —
        goldens/fishing/sweep_craftrod pins the fresh-player
        \"need **10** fish of size ≤ **6**\" guard byte. Only a stocked
        craft runs the audited fish-debit + tier-raise op
        (depth.exemptions.fishing guard-only-capture: fishing_rod)."""
        from sb.domain.fishing import crafting, rods as rods_mod, store
        from sb.domain.mining.store import get_mining_inventory

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        tier = await store.get_rod_tier(uid, gid)
        nxt = rods_mod.next_rod(tier)
        if nxt is None:
            top = rods_mod.rod_for_tier(tier)
            return Reply(BLOCKED,
                         f"You already wield the **{top.name}** "
                         f"{top.emoji} — the finest rod there is!")
        recipe = rods_mod.rod_recipe(nxt.tier)
        if recipe is None:  # defensive — every non-starter tier has one
            return Reply(BLOCKED,
                         f"The **{nxt.name}** {nxt.emoji} can't be "
                         "crafted from fish — buy it with `!rod`.")
        inventory = await get_mining_inventory(uid, gid)
        if crafting.plan_fish_spend(inventory, recipe) is None:
            return Reply(BLOCKED,
                         f"You need **{recipe.fish_count}** fish of size "
                         f"≤ **{recipe.max_size_rank}** to craft the "
                         f"**{nxt.name}** {nxt.emoji} — catch more fish "
                         "with `!fish` (or buy it with `!rod`).")
        blocked, after = await _op_after(req, "fishing.craft_rod")
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    @handler("fishing.rod_upgrade_route")
    async def rod_upgrade_route(req) -> Reply:
        """The rod shop's ⬆️ Upgrade rod button — buy the next rod up the
        ladder (views/fishing/rod_shop.py ``upgrade_btn`` →
        services/fishing_workflow.py ``buy_rod``). The maxed /
        insufficient-funds refusals are computed as PURE READS (tier +
        balance) so the failed attempt writes no coin ledger / audit
        row, exactly as the oracle's txn rolls back. Only a funded
        upgrade runs the audited debit-and-bump op (#217 advisory-fenced
        locking read; economy.balance_changed emits after commit). No
        golden drives the click — copy oracle-source-verbatim."""
        from sb.domain.economy.store import get_coins
        from sb.domain.fishing import rods as rods_mod, store

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        tier = await store.get_rod_tier(uid, gid)
        nxt = rods_mod.next_rod(tier)
        if nxt is None:
            top = rods_mod.rod_for_tier(tier)
            return Reply(BLOCKED,
                         f"You already wield the **{top.name}** "
                         f"{top.emoji} — the finest rod there is!")
        balance = await get_coins(uid, gid)
        if balance < nxt.price:
            return Reply(BLOCKED,
                         f"The **{nxt.name}** {nxt.emoji} costs "
                         f"**{nxt.price}** 🪙 — you only have "
                         f"**{balance}** 🪙.")
        blocked, after = await _op_after(req, "fishing.buy_rod")
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    async def _open_bait_shop(req) -> Reply:
        """Open the bait shop panel (the ``!bait`` open and the shipped
        no-arg ``!craftbait`` fallthrough — ``await self.bait(ctx)``)."""
        import dataclasses

        from sb.domain.fishing.panels import BAIT_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef(BAIT_PANEL_ID),
                         dataclasses.replace(req, args=dict(req.args)))
        return Reply(SUCCESS, None)

    @handler("fishing.bait_shop")
    async def bait_shop(req) -> Reply:
        """!bait — open the bait shop panel (fishing_cog.py ``bait``:
        build_bait_embed + BaitShopView). A pure read — the open renders
        the live loadout/pearls/balance and writes nothing;
        goldens/fishing/sweep_bait pins the fresh bait-less bytes."""
        return await _open_bait_shop(req)

    @handler("fishing.craftbait_route")
    async def craftbait_route(req) -> Reply:
        """!craftbait [bait] / the bait shop's craft select — craft one
        pack from small caught fish (fishing_cog.py ``craftbait`` →
        services/fishing_workflow.py ``craft_bait``). No argument opens
        the bait panel (the shipped ``await self.bait(ctx)`` — the
        byte-identical open goldens/fishing/sweep_craftbait pins); an
        unknown / non-craftable bait and the not-enough-fish case are
        computed as PURE READS so the failed attempt writes no row,
        exactly as the oracle's txn never opens. Only a stocked craft
        runs the audited fish-debit + load op
        (depth.exemptions.fishing guard-only-capture: fishing_bait)."""
        from sb.domain.fishing import bait as bait_mod, crafting
        from sb.domain.mining.store import get_mining_inventory

        text = _rest_arg(req)
        if not text:
            return await _open_bait_shop(req)
        key = bait_mod.craftable_key_for(text)
        if key is None:
            craftable = ", ".join(
                bait_mod.bait_by_key(k).name
                for k in bait_mod.CRAFTABLE_KEYS)
            return Reply(BLOCKED,
                         f"You can't craft **{text}** from fish. "
                         f"Craftable: {craftable}.")
        bait = bait_mod.bait_by_key(key)
        recipe = bait_mod.craft_recipe(key)
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        inventory = await get_mining_inventory(uid, gid)
        if crafting.plan_fish_spend(inventory, recipe) is None:
            return Reply(BLOCKED,
                         f"You need **{recipe.fish_count}** fish of size "
                         f"≤ **{recipe.max_size_rank}** to craft "
                         f"**{bait.name}** {bait.emoji} — catch more "
                         "small fish with `!fish`.")
        blocked, after = await _op_after(req, "fishing.craft_bait",
                                         {"bait_key": key})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    @handler("fishing.craftpearl_route")
    async def craftpearl_route(req) -> Reply:
        """!craftpearl [bait] / the bait shop's pearl select — craft the
        premium bait from pearls (fishing_cog.py ``craftpearl`` →
        services/fishing_workflow.py ``craft_pearl_bait``). No argument
        auto-selects the single pearl recipe (the shipped
        len(PEARL_CRAFTABLE_KEYS) == 1 branch); the unknown-bait and
        not-enough-pearls refusals are computed as PURE READS so the
        failed attempt writes no row — goldens/fishing/sweep_craftpearl
        pins the fresh-player \"need **4** 🦪 pearls\" guard byte. Only
        a stocked craft runs the audited pearl-debit + load op."""
        from sb.domain.fishing import bait as bait_mod
        from sb.domain.fishing.ops import PEARL_ITEM
        from sb.domain.mining.store import get_mining_inventory

        text = _rest_arg(req)
        key = bait_mod.pearl_craftable_key_for(text)
        if not text and len(bait_mod.PEARL_CRAFTABLE_KEYS) == 1:
            key = bait_mod.PEARL_CRAFTABLE_KEYS[0]
        if key is None:
            craftable = ", ".join(
                bait_mod.bait_by_key(k).name
                for k in bait_mod.PEARL_CRAFTABLE_KEYS)
            return Reply(BLOCKED,
                         f"You can't craft **{text}** from pearls. "
                         f"Pearl-craftable: {craftable}.")
        bait = bait_mod.bait_by_key(key)
        pearl_cost = bait_mod.pearl_recipe(key)
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        inventory = await get_mining_inventory(uid, gid)
        have = inventory.get(PEARL_ITEM, 0)
        if have < pearl_cost:
            return Reply(BLOCKED,
                         f"You need **{pearl_cost}** 🦪 pearls to craft "
                         f"**{bait.name}** {bait.emoji} — you have "
                         f"**{have}**. Pearls drop rarely when you reel "
                         "in a fish (bigger fish, better odds).")
        blocked, after = await _op_after(req, "fishing.craft_pearl_bait",
                                         {"bait_key": key})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    @handler("fishing.craftcharm_route")
    async def craftcharm_route(req) -> Reply:
        """!craftcharm [charm] — craft a CHARM-slot fishing charm from
        caught fish (fishing_cog.py ``craftcharm`` →
        services/fishing_workflow.py ``craft_charm``). No argument / an
        unknown charm lists the craftable recipes (the shipped listing —
        goldens/fishing/sweep_craftcharm pins the no-arg bytes); the
        not-enough-fish refusal is a PURE READ. Only a stocked craft
        runs the audited fish-debit + charm-grant op (the charm name
        byte-matches the mining gear catalog, so it equips via
        `!gear`)."""
        from sb.domain.fishing import crafting, gear as gear_mod
        from sb.domain.mining.store import get_mining_inventory

        text = _rest_arg(req)
        name = gear_mod.craftable_charm_for(text)
        if not text or name is None:
            lines = [
                f"🎣 **{r.charm.title()}** — "
                f"{gear_mod.charm_recipe_text(r)}"
                for r in gear_mod.CHARM_RECIPES.values()]
            prefix = (
                f"You can't craft **{text}** from fish.\n"
                if text
                else "Craft a fishing charm from caught fish "
                     "(or buy one with `!gear`):\n")
            return Reply(SUCCESS if not text else BLOCKED,
                         prefix + "\n".join(lines))
        recipe = gear_mod.charm_recipe(name)
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        inventory = await get_mining_inventory(uid, gid)
        if crafting.plan_fish_spend(inventory, recipe) is None:
            return Reply(BLOCKED,
                         f"You need **{recipe.fish_count}** fish of size "
                         f"≤ **{recipe.max_size_rank}** to craft a "
                         f"**{recipe.charm}** — catch more fish with "
                         "`!fish`.")
        blocked, after = await _op_after(req, "fishing.craft_charm",
                                         {"charm_name": name})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    @handler("fishing.bait_buy_route")
    async def bait_buy_route(req) -> Reply:
        """The bait shop's buy select — buy one pack of the picked bait
        (views/fishing/bait_shop.py ``_BaitSelect`` →
        services/fishing_workflow.py ``buy_bait``). The unknown-bait /
        insufficient-funds refusals are computed as PURE READS (shelf +
        balance) so the failed attempt writes no coin ledger / audit
        row, exactly as the oracle's txn rolls back. Only a funded buy
        runs the audited debit-and-load op (#217 advisory-fenced locking
        read; economy.balance_changed emits after commit; same-bait
        stacks, different-bait replaces). No golden drives the pick —
        copy oracle-source-verbatim."""
        from sb.domain.economy.store import get_coins
        from sb.domain.fishing import bait as bait_mod

        bait = bait_mod.bait_by_key(_rest_arg(req))
        if bait is None:
            return Reply(BLOCKED,
                         "That bait doesn't exist on the shelf.")
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        balance = await get_coins(uid, gid)
        if balance < bait.price:
            return Reply(BLOCKED,
                         f"A pack of **{bait.name}** {bait.emoji} costs "
                         f"**{bait.price}** 🪙 — you only have "
                         f"**{balance}** 🪙.")
        blocked, after = await _op_after(req, "fishing.buy_bait",
                                         {"bait_key": bait.key})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    @handler("fishing.curios_view")
    async def curios_view(req) -> Reply:
        """!curios — the coral-carving collection card (fishing_cog.py
        ``curios``, inline embed verbatim: the _FISHING_COLOR blue 🪸
        Coral Curios embed — coral count + owned/total description, one
        ✅/🔨/🔒 field per catalog curio, the carve footer). A pure
        read; goldens/fishing/sweep_curios pins the fresh 0-coral
        bytes."""
        from sb.domain.fishing import curios as curios_mod
        from sb.domain.fishing.ops import CORAL_ITEM
        from sb.domain.mining.store import get_mining_inventory
        from sb.kernel.panels.render import RenderedEmbed

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        inventory = await get_mining_inventory(uid, gid)
        coral = inventory.get(CORAL_ITEM, 0)
        owned, total = curios_mod.collection_progress(inventory)
        fields = []
        for curio in curios_mod.CURIO_CATALOG:
            have = inventory.get(curio.item, 0)
            mark = "✅" if have > 0 else (
                "🔨" if coral >= curio.coral_cost else "🔒")
            owned_txt = f" ×{have}" if have > 0 else ""
            fields.append((
                f"{mark} {curio.emoji} {curio.name}{owned_txt}",
                f"{curios_mod.cost_text(curio)} · {curio.rarity}"))
        embed = RenderedEmbed(
            title="🪸 Coral Curios",
            description=(
                f"You have **{coral}** 🪸 coral · collection "
                f"**{owned}/{total}** carved.\n"
                "Coral drops rarely on a **deepwater** reel (`!sail` to "
                "the boat)."),
            fields=tuple(fields),
            footer="Carve with !craftcurio <name>",
            style_token="blue")
        return await _card(req, embed)

    @handler("fishing.craftcurio_route")
    async def craftcurio_route(req) -> Reply:
        """!craftcurio [curio] — carve a cosmetic curio from coral (the
        deepwater rare-material sink; fishing_cog.py ``craftcurio`` →
        services/fishing_workflow.py ``craft_curio``). No argument / an
        unknown curio answers the shipped carvable listing —
        goldens/fishing/sweep_craftcurio pins the no-arg bytes; the
        not-enough-coral refusal is a PURE READ so the failed attempt
        writes no row, exactly as the oracle's txn never opens. Only a
        stocked carve runs the audited coral-debit + curio-grant op."""
        from sb.domain.fishing import curios as curios_mod
        from sb.domain.fishing.ops import CORAL_ITEM
        from sb.domain.mining.store import get_mining_inventory

        text = _rest_arg(req)
        key = curios_mod.curio_craftable_key_for(text)
        if key is None:
            craftable = ", ".join(
                c.name for c in curios_mod.CURIO_CATALOG)
            return Reply(BLOCKED,
                         f"That isn't a carvable curio. Carvable: "
                         f"{craftable}. See `!curios` for your "
                         "collection.")
        curio = curios_mod.curio_by_key(key)
        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        inventory = await get_mining_inventory(uid, gid)
        have = inventory.get(CORAL_ITEM, 0)
        if have < curio.coral_cost:
            return Reply(BLOCKED,
                         f"You need **{curio.coral_cost}** 🪸 coral to "
                         f"carve **{curio.name}** {curio.emoji} — you "
                         f"have **{have}**. Coral drops rarely when you "
                         "reel in a fish out in **deepwater** (`!sail` "
                         "to the boat first).")
        blocked, after = await _op_after(req, "fishing.craft_curio",
                                         {"curio_key": key})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    async def _structure_build(req, structure_key: str) -> Reply:
        """One structure panel's Build button — build/upgrade the coral
        structure one level (views/fishing/{tide_pool,dock,boathouse,
        fishery}.py ``build_btn`` → services/mining_workflow.py
        ``build_structure``). The maxed / short-on-materials /
        insufficient-funds refusals are computed as PURE READS (level +
        inventory + balance) so the failed attempt writes no coin
        ledger / audit row, exactly as the oracle's txn rolls back. Only
        a funded, stocked build runs the audited debit + consume + raise
        op (#217 advisory-fenced locking read;
        economy.balance_changed emits after commit;
        mining_structures written only via the mining.store sole-writer
        seam). No golden drives the click — copy
        oracle-source-verbatim."""
        from sb.domain.economy.store import get_coins
        from sb.domain.mining import structures, workshop
        from sb.domain.mining.store import (
            get_mining_inventory,
            get_structures,
        )

        uid = int(getattr(req.actor, "user_id", 0) or 0)
        gid = int(req.guild_id or 0)
        display = structures.display_name(structure_key)
        built = await get_structures(uid, gid)
        level = built.get(structure_key, 0)
        cost = structures.build_cost(structure_key, level)
        if cost is None:
            name = structures.level_name(structure_key, level)
            return Reply(BLOCKED,
                         f"Your {display} is already at its maximum "
                         f"level (**{name}**).")
        inventory = await get_mining_inventory(uid, gid)
        if any(inventory.get(mat, 0) < qty
               for mat, qty in cost.materials.items()):
            return Reply(BLOCKED,
                         f"Building the {display} needs "
                         f"{workshop.describe_materials(cost.materials)} "
                         f"plus {cost.coins} 🪙 — you're short on "
                         "materials.")
        balance = await get_coins(uid, gid)
        if balance < cost.coins:
            return Reply(BLOCKED,
                         f"Building the {display} costs "
                         f"**{cost.coins}** 🪙 — you only have "
                         f"**{balance}** 🪙.")
        blocked, after = await _op_after(req, "fishing.build_structure",
                                         {"structure": structure_key})
        if blocked is not None:
            return blocked
        return Reply(SUCCESS, after.get("message", ""))

    @handler("fishing.tidepool_build_route")
    async def tidepool_build_route(req) -> Reply:
        from sb.domain.mining import structures

        return await _structure_build(req, structures.TIDE_POOL)

    @handler("fishing.dock_build_route")
    async def dock_build_route(req) -> Reply:
        from sb.domain.mining import structures

        return await _structure_build(req, structures.DOCK)

    @handler("fishing.boathouse_build_route")
    async def boathouse_build_route(req) -> Reply:
        from sb.domain.mining import structures

        return await _structure_build(req, structures.BOATHOUSE)

    @handler("fishing.fishery_build_route")
    async def fishery_build_route(req) -> Reply:
        from sb.domain.mining import structures

        return await _structure_build(req, structures.FISHERY)

    @handler("fishing.menu_view")
    async def menu_view(req) -> Reply:
        from sb.domain.fishing import catalog

        return Reply(SUCCESS,
                     f"🎣 **Fishing** — {len(catalog.SPECIES)} species "
                     "across 7 size bands.\n`!fish` cast a line · "
                     "`!fishlog` your dex · `!fishtop` top anglers · "
                     "`!trophies` biggest catches")

    @handler("fishing.rules_view")
    async def rules_view(req) -> Reply:
        """The hub's 📖 How-to-fish affordance — the shipped static
        rules card (views/fishing/menu.py ``_rules_embed`` sent
        ephemeral by ``rules_btn``; fishing.rules_card,
        grammar-rendered — the creature.rules_view precedent)."""
        import dataclasses

        from sb.domain.fishing.panels import RULES_PANEL_ID
        from sb.kernel.panels.engine import open_panel
        from sb.spec.refs import PanelRef

        await open_panel(PanelRef(RULES_PANEL_ID),
                         dataclasses.replace(req, args=dict(req.args)))
        return Reply(SUCCESS, None)

    @handler("fishing.top_view")
    async def top_view(req) -> Reply:
        """!fishtop — the shipped 🎣 Top Anglers embed (fishing_cog.py
        fishtop: _FISHING_COLOR blue; the empty-world description is
        golden-pinned — goldens/fishing/sweep_fishtop). The populated
        leaderboard body is the shipped copy verbatim
        (fishing_cog.py:154-164): 🥇🥈🥉 medals then ``**N.**``,
        resolved display names, ``— **N** caught (S/21 species)``."""
        from sb.domain.fishing import catalog, store

        rows = await store.top_fishers(int(req.guild_id or 0),
                                       catalog.fish_names())
        if not rows:
            desc = "No one has cast a line yet — be the first with `!fish`!"
        else:
            medals = ["🥇", "🥈", "🥉"]
            lines = []
            for rank, r in enumerate(rows):
                prefix = (medals[rank] if rank < len(medals)
                          else f"**{rank + 1}.**")
                name = await _angler_name(int(r["user_id"]),
                                          int(req.guild_id or 0))
                lines.append(
                    f"{prefix} {name} — **{r['total']}** caught "
                    f"({r['species']}/{len(catalog.SPECIES)} species)")
            desc = "\n".join(lines)
        return await _card(req, _embed("🎣 Top Anglers", desc))

    @handler("fishing.trophies_view")
    async def trophies_view(req) -> Reply:
        """!trophies — the shipped 🏅 Biggest Catches embed
        (fishing_cog.py trophies: _FISHING_COLOR blue; the empty-world
        description is golden-pinned — goldens/fishing/sweep_trophies).
        The populated hall-of-fame body is the shipped copy verbatim
        (fishing_cog.py:181-192): medals, the species emoji (🐟 when
        the catalog misses), ``**{weight:g} kg** {Species} — {name}``."""
        from sb.domain.fishing import catalog, store

        rows = await store.top_trophies(int(req.guild_id or 0),
                                        catalog.fish_names())
        if not rows:
            desc = ("No trophies landed yet — reel in a big one with "
                    "`!fish`!")
        else:
            medals = ["🥇", "🥈", "🥉"]
            lines = []
            for rank, r in enumerate(rows):
                prefix = (medals[rank] if rank < len(medals)
                          else f"**{rank + 1}.**")
                name = await _angler_name(int(r["user_id"]),
                                          int(req.guild_id or 0))
                fish = catalog.species_by_name(str(r["species"]))
                emoji = fish.emoji if fish else "🐟"
                lines.append(
                    f"{prefix} {emoji} **{float(r['best_weight']):g} kg** "
                    f"{str(r['species']).title()} — {name}")
            desc = "\n".join(lines)
        return await _card(req, _embed("🏅 Biggest Catches", desc))


#: The fishing deep-system commands (shipped names) → pending copy.
#: forecast/sail left this dict in slice 1 (weather + venue);
#: rod/rodrecipes/craftrod in slice 2 (the rod ladder);
#: bait/craftbait/craftpearl/craftcharm in slice 3 (the bait shelf).
#: curios/craftcurio/tidepool/dock/boathouse/fishery left in slice 4
#: (the coral sinks + structures — the FINAL slice): curios_view /
#: craftcurio_route in _register() carry the curio shelf card + the
#: not-carvable guard, and the four structure commands route straight
#: to their live PanelSpecs (the Build buttons run the audited
#: fishing.build_structure write op).
#: This EMPTIES the fishing deep-system PENDING roster — all 20 shipped
#: fishing commands are ported (the D-0043 fishing ladder is complete).
#: The cast-leg depth wiring then made the cast LEG itself live: the
#: venue/rod/bait/gear/structure/weather knobs now drive the roll
#: (deepwater species pool, coral drop, the compounded rarity_pull, the
#: per-cast bait charge spend, the pull/regen/double-catch structure
#: mults — cast_open above = the shipped begin_cast; record_cast =
#: commit_catch). The D-0043 minigame TIMING rung then made the timing
#: knobs gate outcomes — slice 1 (click-gated): cast_open rolls
#: bite-delay (consuming the compounded effective_bite_speed) +
#: fake-out at cast time and fish_route resolves the Reel click
#: (premature spook / one premature-grace forgive, the trophy
#: reel-fight with per-tap escape rolls); slice 2 (live cues + full
#: enforcement): the cast panel edits itself mid-wait — fake-out
#: nibble, 🐟 BITE! arm, fight-round prompts, the unprompted got-away
#: expiry — via the D-0090 kernel one-shot timers +
#: push_session_refresh seam, and a LATE reel (past bite_at + window,
#: or past a fight round's window) now answers the oracle too-slow
#: got-away terminal (reel_is_in_time on SYSTEM_CLOCK — parity decides
#: identically on the logical clock; the timers only carry edits and
#: no-op headless via EDIT_UNAVAILABLE). The ONLY remainder is the
#: _FishingDoneView Cast-again continuation (the games-finalization
#: review's ranked gap 3 — a named successor, not this rung).
PENDING: dict[str, str] = {}


#: The hub-button-only pending set is EMPTY too: the 📖 How-to-fish
#: button (the last `_register_hub_pending` occupant —
#: fishing.howtofish_pending) now routes to the live static rules card
#: (fishing.rules_view → fishing.rules_card, the oracle _rules_embed
#: verbatim); the 🏗 Structures button left in slice 4. The retired
#: pending ref no longer registers (trap 12a).


def ensure_handler_refs() -> None:
    _register()
    from sb.domain.operator_spine import pending_handler

    for name, system in PENDING.items():
        pending_handler(
            f"fishing.{name}_pending",
            f"🎣 `!{name}` needs the fishing {system} — the fishing "
            "depth port is named successor work (D-0043); the core "
            "cast loop is live at the starter profile.")


_register()
