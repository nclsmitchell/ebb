import hashlib
import json
import warnings
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import yaml
from pydantic import ValidationError

from ebb.registry.models import RegistryEntry

STALE_AFTER_DAYS = 90


class RegistryLoadError(Exception):
    """Raised when a registry YAML file contains a record that fails validation — e.g. missing
    source_url or verified_at. Refusing to load beats silently dropping a bad record: a
    retirement date the loader couldn't verify is worse than no data at all."""


class StaleRegistryEntryWarning(UserWarning):
    """A record's verified_at is more than STALE_AFTER_DAYS days old."""


@dataclass(frozen=True, slots=True)
class Registry:
    entries: tuple[RegistryEntry, ...]
    version: str


def _compute_version(entries: tuple[RegistryEntry, ...]) -> str:
    # Deterministic, content-derived — the same registry content always yields the same
    # version, regardless of when or where it's loaded. This is what gets stamped on findings
    # later (Session 6's Finding.rule_version) to prove which registry produced a result.
    canonical = [e.model_dump(mode="json") for e in sorted(entries, key=lambda e: e.canonical_id)]
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode("utf-8")).hexdigest()
    return digest[:16]


def load_registry(paths: Iterable[Path], *, today: date | None = None) -> Registry:
    """Loads and validates every YAML file in `paths`. Each file is a flat list of entries.

    A record missing source_url or verified_at fails the whole load (RegistryLoadError) —
    provenance is a hard rule, not a lint warning. Emits StaleRegistryEntryWarning for any
    entry verified more than 90 days ago; loading still succeeds, since a stale-but-present
    entry is still better than none, but the warning is real and filterable.
    """
    today = today or datetime.now(UTC).date()
    entries: list[RegistryEntry] = []

    for path in paths:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if raw is None:
            continue
        for i, record in enumerate(raw):
            try:
                entries.append(RegistryEntry(**record))
            except ValidationError as exc:
                raise RegistryLoadError(f"{path}[{i}]: {exc}") from exc

    for entry in entries:
        age_days = (today - entry.verified_at).days
        if age_days > STALE_AFTER_DAYS:
            warnings.warn(
                f"{entry.canonical_id} ({entry.provider.value}) last verified "
                f"{entry.verified_at} — {age_days} days ago, over the {STALE_AFTER_DAYS}-day "
                f"freshness bar",
                StaleRegistryEntryWarning,
                stacklevel=2,
            )

    return Registry(entries=tuple(entries), version=_compute_version(tuple(entries)))
