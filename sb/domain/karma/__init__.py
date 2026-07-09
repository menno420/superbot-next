"""Karma domain (band 4) — peer reputation (thanks/upvote).

INV-K: every karma mutation rides the audited K7 ``karma.give`` op;
``sb/domain/karma/store.py`` is the sole writer of ``karma`` +
``karma_audit_log``. The audit log doubles as the anti-abuse source of
truth (cooldown + daily cap are reads over it — no separate cooldown
table, shipped design carried verbatim).
"""
