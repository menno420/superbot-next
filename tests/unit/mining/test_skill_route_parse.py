"""Pure unit tests for the WP-5 skill-spend arg parse
(`sb/domain/mining/ops.py::_branch_amount_from`) — the positional
`!skill <branch> [amount]` split the ported `skill_service.allocate` leg reads.

The oracle `skill_cmd(ctx, branch: str = None, amount: int = 1)` is a
positional discord.py parse: the first token is the branch, the second (if
numeric) is the amount (default 1). `_branch_amount_from` reproduces that off
the workflow-context `argv` (falling back to `values`), leaving branch
normalization (strip/lower) to the allocate body — oracle verbatim. Pure: no
DB, no Discord, no clock.
"""

from __future__ import annotations

from types import SimpleNamespace

from sb.domain.mining.ops import _branch_amount_from


def _ctx(**params):
    return SimpleNamespace(params=params)


def test_branch_only_defaults_amount_to_one():
    assert _branch_amount_from(_ctx(argv=("mining",))) == ("mining", 1)


def test_branch_and_numeric_amount():
    assert _branch_amount_from(_ctx(argv=("combat", "3"))) == ("combat", 3)


def test_first_numeric_token_is_the_amount():
    # The first non-numeric token is the branch, the first numeric is the amount.
    assert _branch_amount_from(_ctx(argv=("fortune", "2"))) == ("fortune", 2)


def test_falls_back_to_values_when_argv_empty():
    assert _branch_amount_from(_ctx(argv=(), values=("crafting",))) == (
        "crafting", 1)


def test_argv_wins_over_values():
    assert _branch_amount_from(
        _ctx(argv=("mining",), values=("combat",))) == ("mining", 1)


def test_no_tokens_yields_blank_branch_default_amount():
    # A blank branch is left for the allocate body to reject with the oracle's
    # `(blank)` copy — the parser does not invent one.
    assert _branch_amount_from(_ctx()) == ("", 1)


def test_case_is_preserved_normalization_is_the_leg_body_job():
    # strip/lower is allocate's job (oracle verbatim), so the parser preserves
    # the raw token.
    assert _branch_amount_from(_ctx(argv=("Mining",))) == ("Mining", 1)
