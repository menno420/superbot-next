# 2026-07-13 — windowed-select grammar successor (ORDER 019 item 7, night lane)

> **Status:** `in-progress`

- **📊 Model:** `Claude Fable` · NIGHT lane · mandate: ORDER 019 item 7,
  claim `control/claims/night-setup-followups-windowed-select.md` (PR #431)

## Scope

Promote the two ad-hoc select-windowing precedents (access_map surface;
admin cogmgr "select pick + ◀/▶ windowing") into a reusable grammar
successor: a spec-level windowed-select construct + kernel panels
paging/rendering support, so any domain surface can declare a select whose
option set exceeds Discord's 25-option cap and pages with prev/next. Wire
ONE consuming surface as proof (preference: the mining title-equip select
parked as honest-pending in PR #371 / D-0043) + goldens.

Definition of done: grammar construct landed at the right layers (sb/spec
+ sb/kernel/panels), one surface migrated/wired, goldens for that surface,
guards green, `python3 -m pytest` green.

## 💡 Session idea

[[fill: close-out]]

## ⟲ Previous-session review

[[fill: close-out]]
