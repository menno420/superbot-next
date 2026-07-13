# 2026-07-13 — windowed-select grammar successor (ORDER 019 item 7, night lane)

> **Status:** `complete`

- **📊 Model:** `Claude Fable` (Claude 5 family) · NIGHT lane · mandate:
  ORDER 019 item 7, claim `control/claims/night-setup-followups-windowed-select.md`
  (PR #431, merged)

## Scope

Promote the two ad-hoc select-windowing precedents (access_map surface;
admin cogmgr "select pick + ◀/▶ windowing") into a reusable grammar
successor: a spec-level windowed-select construct + kernel panels
paging/rendering support, so any domain surface can declare a select whose
option set exceeds Discord's 25-option cap and pages with prev/next. Wire
ONE consuming surface as proof + goldens-convention tests.

Definition of done: grammar construct landed at the right layers (sb/spec
+ sb/kernel/panels), one surface migrated/wired, byte-pinning tests for
that surface, guards green, `python3 -m pytest tests/` green.

## Close-out

Landed as PR #435. The shipped `SelectWindow` grammar (oracle
menno420/superbot `views/paginated_select.py` @ `bbc524e4`, read via
GitHub MCP at the pinned SHA — the local clone is walled in this venue,
see the CAPABILITIES entry this session appended) made declarative:

- `sb/spec/panels.py` — `SelectorSpec.windowed` [S], opt-in; `False`
  keeps the pre-successor first-25 truncation byte-verbatim (non-churn).
- `sb/kernel/panels/selectwindow.py` — the engine: window algebra over
  the shared `browserview.paginate` core; the
  `nav:selwin:<control>:<panel_id>:<selector_id>:<window>` codec (the
  `nav:browse:` posture — parsed at click time, inside the nav
  namespace, never a parallel scheme); the shipped ◀ Prev / Next ▶
  button faces disabled at the bounds; the shipped
  `{placeholder} — page p/n` suffix (the window position rides the
  placeholder, never a third button — two buttons keep a windowed
  select viable on a shared button row).
- `render.py` / `router.py` / `registry.py` / `engine.py` — windowed
  materialization + per-window min/max clamp; `NavBinding(kind=selwin)`;
  `_handle_selwin` refreshes a live session IN PLACE (no second card),
  else the browse/page-turn present posture; malformed/stale ids land on
  the §3.4 polite expiry. Window state threads through the reserved
  `ctx.params` key so renderer_override panels inherit it.
- WIRED SURFACE: the setup 43-cog routing picker
  (`sb/domain/setup/cog_routing.py` — the completeness table's named
  waiting surface): the provider now returns the FULL 43-row harvest and
  the declared windowed select pages it; the shipped ad-hoc first-25
  window (18 cogs unreachable — the #1040 class re-shipped) is retired.
  The stepwise reveal carries the window nav with the cog select; the
  page suffix survives the per-scope placeholder patch; row 4 holds
  exactly 5 buttons at full reveal (Enable · Disable · ↩ Back + ◀/▶).
- Deliberate deviation from the dispatch brief, flagged: the brief's
  preferred surface (mining title-equip) was NOT wired — its option set
  maxes at 10 (9 titles + "(none)", oracle
  `views/mining/titles_panel.py::_TitleSelect`), so it can never
  exercise windowing, and its real blockers (equip write lane,
  absent-when-empty select, note re-render) are a feature slice of
  their own, not this grammar. The brief's own fallback clause (b)
  names the 43-cog picker; wired that instead, honestly.
- Tests (the browserview goldens convention — parity goldens are
  oracle-captured read-only fixtures, so the byte pins live in unit
  tests): `tests/unit/panels/test_selectwindow.py` (26 tests — algebra,
  codec, shipped control bytes, render integration incl. the ctx.params
  thread + non-churn truncation pin, dispatch contract incl. in-place
  session refresh) + `tests/unit/setup_band/test_routing_ticket_flows.py`
  updated to the windowed reality (full 43-option provider, windowed
  declaration, reveal + row-budget + placeholder-suffix pins).

Verified: `python3 -m pytest tests/ -q` → 2918 passed / 15 skipped;
`python3 bootstrap.py check --strict` → green minus this card's own
designed born-red hold (+ pre-existing claims advisories, not this
lane's); all four guards clean (check_symbol_shadowing forced the codec
renames `encode_window`/`decode_window`/`window_panel_id`/
`apply_window_delta` — same-package collision with browserview).

## 💡 Session idea

`_handle_browse` and `_handle_selwin` now differ in exactly one
behavior: selwin refreshes a live session in place (no duplicate card)
while browse always re-presents — so a browse-armed session panel still
spawns a second message per sort/filter/page click. Guard recipe: lift
the message-key → `refresh_session_view` → fallback dance out of
`_handle_selwin` (sb/kernel/panels/engine.py) into a shared
`_re_render_nav(spec, req, *, browse=None, window=None)`, point both
handlers at it, and pin it with a browse twin of
`test_selwin_click_refreshes_a_live_session_in_place`
(tests/unit/panels/test_selectwindow.py) asserting
`edit_message_ref is not None`.

## ⟲ Previous-session review

The setup-compound-2 session (PR #429) closed its lane cleanly: both new
op legs kept the pure-DB single-leg NATURAL_KEY posture its predecessor's
card argued for (dodging the once()-pre-effect trap by construction), and
its close-out named every flagged decision with anchors. Two things this
session leaned on directly: its `routing.set_policy` port is exactly what
makes the 43-cog picker's staged rows APPLY — without it this slice's
windowing would page a fail-closed select — and its CI-red note (the
check_compat_frozen standalone-job class, amended via the sanctioned
`--write` path) is the kind of verbatim-wall recording the CAPABILITIES
discovery rule wants; the one gap: its card's routing-fake triplication
warning (💡) still isn't a conftest fixture, and this session's routing
test edits brushed the same files it warned about.
