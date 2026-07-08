# Rubric v2 — classes 11 / 12 / 13 (PROPOSAL — owner-gated, not self-applied)

> **Status:** `proposal` (S11, 2026-07-08). The review rubric is an owner-directed system
> (Q-0233 froze the ten classes): these three classes + the precedence rule are **proposed
> for adoption** (spec 10 T-1), never self-applied. Source of the full drop-in text:
> `superbot:docs/analysis/rebuild-discovery/foundations/design/strand-3-cross-cutting-concerns/10-security-abuse-rubric.md` §2.A.
> The **checkable mechanics landed in THIS repo at S11** regardless of rubric adoption —
> the lens is proposed; the fences are live.

## The three classes (one-line probes)

| # | Class | Probe (fastest form) | Mechanization (live in this repo) |
|---|---|---|---|
| 11 | Cost / quota / abuse-of-resource | "Name the spend/rate counter this feature reads before it acts — no counter is the finding." | `CommandSpec.cost_posture` + `quota_ref` grammar (`sb/spec/cost.py`) + `tools/check_cost_posture.py` (Phase 1 declaration-presence; Phase 2 live-binding sequences after T2-15). Cardinality leg = `tools/check_metric_cardinality.py`. FAIL_CLOSED = the L-16 media default-OFF rule. |
| 12 | Privacy / retention / erasure | "Trace one member's PII from input to every store and third party it reaches, then name its erasure hook." | `StoreSpec.{data_class, erasure_ref, is_cache, cache_scope}` (`sb/spec/versioning.py`) + `tools/check_data_lifecycle.py` + the member-erasure executor `sb/kernel/privacy/erasure.py` (+ the A-15 `run_export` read-only twin). PII-in-prompts stays a judgment probe. |
| 13 | Security / abuse-of-trust + non-functional integrity | "Who can abuse this to affect someone else or escalate — what untrusted data crosses IN, and what binds data on the way OUT?" | Reply egress = the frozen `SurfaceResponder` default-deny (S9); **send egress = the `ChannelEmitter` port** (`sb/kernel/interaction/egress.py`, RC-21/Q-D26) + `tools/check_egress.py` (the AST fence, A-5-widened to raw Discord state mutations). Owner axis = the K6 fences (S7). N-1/N-2/N-3 fixes land at S13/S15. |

## Orthogonality + total precedence (13 > 12 > 11)

Score by **victim/axis**; a multi-victim issue scores the **most-severe victim**:
13 = another user / the guild / bot integrity (highest) · 12 = the data-subject ·
11 = the payer / availability. Precedence sets the ONE scored class (Q-0236);
secondary axes are still recorded as findings.

## The adversarial-abuse pass (spec 10 §2.B — procedure saved here)

One structured adversarial walk over the frozen surface, run once before Gate-0 (the
retroactive coverage of Stage-1; the classes run forward 43× in Stage-2). Three axes —
**owner** (override sites: membership-bound, single `is_platform_owner`, TransparencySink),
**input** (every trust boundary in: validator→envelope, cost bound, data_class posture, K1
validate routing, panel cooldown/audit step exists), **output-binding** (both egress ports
default-deny, alt-text, no un-redacted secret on any log/metric path, caches scoped).
Output: one findings table per axis (`axis · threat · site · closing mechanic OR ⚑ hole ·
Gate-0 disposition`); every ⚑ binds to a Gate-0 checklist item; a clean axis records the
closing mechanic, never silence.

## Flagged for owner (spec 10 §4)

- **T-1** adopt classes 11/12/13 as the cut (recommended: yes, with the precedence rule).
- **T-2** retroactivity (recommended: forward-only classes + the one retroactive pass).
- **T-3** who runs the pass (recommended: a dedicated adversarial agent, rotated lenses).
- Rubric-v2 co-merge: these three classes must merge with audit-B's other v2 facets in ONE
  rubric-v2 router Q to avoid a fork (spec 10 §6).
