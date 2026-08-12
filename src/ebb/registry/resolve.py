from dataclasses import dataclass

from ebb.registry.loader import Registry
from ebb.registry.models import RegistryEntry


@dataclass(frozen=True, slots=True)
class Resolved:
    entry: RegistryEntry
    matched_via: str  # "canonical_id" | "alias"


@dataclass(frozen=True, slots=True)
class Unknown:
    raw_text: str


Resolution = Resolved | Unknown


def resolve(raw_text: str, registry: Registry) -> Resolution:
    """Exact-match only, deliberately: no prefix matching, no fuzzy matching, no stripping
    suffixes like "-latest" to guess an intended target. A floating alias that isn't itself a
    curated registry entry resolves to Unknown, never to whatever registry entry happens to
    share a prefix — SUITE_ARCHITECTURE.md §3: unresolvable means unknown, never clear.

    Full canonicalisation — dated snapshots, version suffixes, regional prefixes collapsing to
    one id — is Session 5, not this. This is a literal lookup against curated canonical ids
    and their curated aliases only.
    """
    for entry in registry.entries:
        if raw_text == entry.canonical_id:
            return Resolved(entry=entry, matched_via="canonical_id")
        if raw_text in entry.aliases:
            return Resolved(entry=entry, matched_via="alias")
    return Unknown(raw_text=raw_text)
