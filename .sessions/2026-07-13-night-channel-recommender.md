# 2026-07-13 — night: native channel-recommender port (ORDER 019 item 5c)

> **Status:** `in-progress`

- **📊 Model:** `fable-5` · night lane worker · mandate: ORDER 019 item 5(c) — native channel-recommender port (perms-bearing snapshot), surviving setup-wizard follow-up per `docs/status/completeness-table-2026-07-13.md` setup row · claim: `control/claims/night-setup-followups-windowed-select.md` (PR #431)

## Scope

Port the oracle's channel recommender natively: pure scoring service
(`disbot/services/channel_recommender.py` @bbc524e — `recommend(intent_slug,
snapshot)` with reasons), a perms-bearing guild-channel snapshot type at the
right layer, the discord adapter fill, and the setup channels section
rendering "likely #channel (confidence)" + reasons like the oracle
(`disbot/views/setup/sections/channels.py::_recommendation_for`). Shared
heuristic `disbot/utils/channel_classify.py::classify_channel_name` also
powers cleanup profiles + cog_routing_profiles. Table-driven scorer tests;
section render tests per setup_band conventions. True up the completeness
table setup row if it lists this follow-up.

## Previous-session review

[[fill: one-line review of the newest other session card]]

## What shipped

[[fill: close-out]]

## 💡 Session idea

[[fill: idea]]
