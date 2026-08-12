from datetime import date

import pytest
from pydantic import ValidationError

from ebb.registry.models import Provider, RegistryEntry


def _entry(**overrides: object) -> dict[str, object]:
    defaults: dict[str, object] = {
        "canonical_id": "gpt-4-turbo",
        "provider": "openai",
        "source_url": "https://developers.openai.com/api/docs/deprecations",
        "verified_at": date(2026, 8, 12),
    }
    defaults.update(overrides)
    return defaults


def test_a_complete_entry_loads() -> None:
    entry = RegistryEntry(**_entry())
    assert entry.provider is Provider.OPENAI
    assert entry.aliases == []
    assert entry.shutdown_at is None


def test_missing_source_url_is_rejected() -> None:
    record = _entry()
    del record["source_url"]
    with pytest.raises(ValidationError):
        RegistryEntry(**record)


def test_missing_verified_at_is_rejected() -> None:
    record = _entry()
    del record["verified_at"]
    with pytest.raises(ValidationError):
        RegistryEntry(**record)


def test_blank_source_url_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RegistryEntry(**_entry(source_url="   "))


def test_blank_canonical_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RegistryEntry(**_entry(canonical_id=""))


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RegistryEntry(**_entry(provider="mistral"))
