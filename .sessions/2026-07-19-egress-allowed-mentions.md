# Session — egress allowed-mentions fence: cover the mention-OPENING branches

> **Status:** `in-progress`
>
> Born-red first commit: this card alone holds the substrate-gate. The test
> lands next; the `complete` flip is the deliberate LAST commit.

- **📊 Model:** opus-4.8 · high · test writing

## Order

FINAL improvement probe — land ONE genuinely-valuable, contained,
behavior-preserving improvement or report an honest dry. Read-only HUNT found
that `sb/adapters/discord/egress.py:allowed_mentions_for` — the S11 default-deny
mass-ping fence and the ONLY module that constructs `discord.AllowedMentions` —
has its mention-OPENING branches (`everyone`/`here`, `role:`, mixed) and the
critical trust-fence-over-allowlist branch UNtested. The two existing e2e tests
(`tests/e2e/test_egress_trust_policy_e2e.py`) cover only `none()` and a single
`user:` token; the kernel-side `neutralize_untrusted` is covered
(`tests/unit/privacy/test_s11_mechanics.py`) but the adapter transform is not.

## Scope

Test-only. Add `tests/unit/adapters/test_allowed_mentions_for.py`. Zero `sb/`
source edited; no dependency change (pip-audit n/a).
