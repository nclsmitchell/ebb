import warnings
from datetime import date
from pathlib import Path

import pytest

from ebb.registry.loader import (
    RegistryLoadError,
    StaleRegistryEntryWarning,
    load_registry,
)

REAL_REGISTRY_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "ebb" / "registries" / "retirements"
)


def write_yaml(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


def test_loads_a_well_formed_file(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path / "openai.yaml",
        """
        - canonical_id: gpt-4-turbo
          provider: openai
          source_url: https://example.com/deprecations
          verified_at: 2026-08-01
        """,
    )
    registry = load_registry([path], today=date(2026, 8, 12))
    assert len(registry.entries) == 1
    assert registry.entries[0].canonical_id == "gpt-4-turbo"


def test_version_is_deterministic_for_the_same_content(tmp_path: Path) -> None:
    content = """
    - canonical_id: gpt-4-turbo
      provider: openai
      source_url: https://example.com/deprecations
      verified_at: 2026-08-01
    """
    a = write_yaml(tmp_path / "a.yaml", content)
    b = write_yaml(tmp_path / "b.yaml", content)

    registry_a = load_registry([a])
    registry_b = load_registry([b])

    assert registry_a.version == registry_b.version


def test_version_changes_when_content_changes(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path / "openai.yaml",
        """
        - canonical_id: gpt-4-turbo
          provider: openai
          source_url: https://example.com/deprecations
          verified_at: 2026-08-01
        """,
    )
    v1 = load_registry([path]).version

    write_yaml(
        path,
        """
        - canonical_id: gpt-4-turbo
          provider: openai
          source_url: https://example.com/deprecations
          verified_at: 2026-08-02
        """,
    )
    v2 = load_registry([path]).version

    assert v1 != v2


def test_a_record_missing_source_url_fails_the_whole_load(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path / "bad.yaml",
        """
        - canonical_id: gpt-4-turbo
          provider: openai
          verified_at: 2026-08-01
        """,
    )
    with pytest.raises(RegistryLoadError):
        load_registry([path])


def test_a_record_missing_verified_at_fails_the_whole_load(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path / "bad.yaml",
        """
        - canonical_id: gpt-4-turbo
          provider: openai
          source_url: https://example.com/deprecations
        """,
    )
    with pytest.raises(RegistryLoadError):
        load_registry([path])


def test_warns_on_an_entry_verified_more_than_90_days_ago(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path / "stale.yaml",
        """
        - canonical_id: gpt-4-turbo
          provider: openai
          source_url: https://example.com/deprecations
          verified_at: 2026-01-01
        """,
    )
    with pytest.warns(StaleRegistryEntryWarning):
        load_registry([path], today=date(2026, 8, 12))


def test_does_not_warn_on_an_entry_verified_within_90_days(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path / "fresh.yaml",
        """
        - canonical_id: gpt-4-turbo
          provider: openai
          source_url: https://example.com/deprecations
          verified_at: 2026-08-01
        """,
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        load_registry([path], today=date(2026, 8, 12))
    assert not any(issubclass(w.category, StaleRegistryEntryWarning) for w in caught)


def test_empty_file_yields_no_entries(tmp_path: Path) -> None:
    path = write_yaml(tmp_path / "empty.yaml", "")
    registry = load_registry([path])
    assert registry.entries == ()


def test_the_real_registry_files_all_load_and_pass_validation() -> None:
    paths = sorted(REAL_REGISTRY_DIR.glob("*.yaml"))
    assert len(paths) == 3, "expected openai.yaml, anthropic.yaml, google.yaml"

    registry = load_registry(paths, today=date(2026, 8, 12))

    assert len(registry.entries) > 0
    for entry in registry.entries:
        assert entry.source_url.startswith("https://")
        assert entry.verified_at <= date(2026, 8, 12)
