"""The L-24 locale / i18n seam (Gate-0 l24-presentation-riders §2).

A declared render-layer HOOK, not a translation system: ``PanelContext``
carries a ``LocaleContext``; every place the renderer emits an [S] copy
string passes it through the registered ``CopyResolver``. v1 registers
``IDENTITY_COPY_RESOLVER`` (verbatim authored copy — zero behavior change);
a future locale build registers a table-backed resolver WITHOUT touching any
spec — the seam is the entire point.

Stdlib-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

__all__ = [
    "CopyResolver",
    "IDENTITY_COPY_RESOLVER",
    "LocaleContext",
    "active_copy_resolver",
    "install_copy_resolver",
    "reset_copy_resolver_for_tests",
]


@dataclass(frozen=True)
class LocaleContext:
    locale: str = "en"      # [S]/runtime — BCP-47-ish tag; "en" = the authored corpus


class CopyResolver(Protocol):
    def resolve(self, copy: str, *, locale: LocaleContext) -> str: ...


class _IdentityCopyResolver:
    """Returns copy verbatim — the v1 default."""

    def resolve(self, copy: str, *, locale: LocaleContext) -> str:
        return copy


IDENTITY_COPY_RESOLVER: CopyResolver = _IdentityCopyResolver()

_resolver: CopyResolver = IDENTITY_COPY_RESOLVER


def install_copy_resolver(resolver: CopyResolver) -> None:
    global _resolver
    _resolver = resolver


def active_copy_resolver() -> CopyResolver:
    return _resolver


def reset_copy_resolver_for_tests() -> None:
    global _resolver
    _resolver = IDENTITY_COPY_RESOLVER
