from datetime import date

from ebb.registry.loader import Registry
from ebb.registry.models import RegistryEntry
from ebb.registry.resolve import Resolved, Unknown, resolve


def make_registry() -> Registry:
    entries = (
        RegistryEntry(
            canonical_id="claude-3-opus-20240229",
            provider="anthropic",
            aliases=["claude-3-opus-legacy"],
            source_url="https://platform.claude.com/docs/en/about-claude/model-deprecations",
            verified_at=date(2026, 8, 12),
        ),
        # A floating alias that IS itself a curated, verified registry entry — OpenAI
        # deprecated this alias directly, not one dated snapshot behind it.
        RegistryEntry(
            canonical_id="chatgpt-4o-latest",
            provider="openai",
            source_url="https://developers.openai.com/api/docs/deprecations",
            verified_at=date(2026, 8, 12),
        ),
    )
    return Registry(entries=entries, version="test-version")


def test_resolves_by_exact_canonical_id() -> None:
    result = resolve("claude-3-opus-20240229", make_registry())
    assert isinstance(result, Resolved)
    assert result.entry.canonical_id == "claude-3-opus-20240229"
    assert result.matched_via == "canonical_id"


def test_resolves_by_curated_alias() -> None:
    result = resolve("claude-3-opus-legacy", make_registry())
    assert isinstance(result, Resolved)
    assert result.entry.canonical_id == "claude-3-opus-20240229"
    assert result.matched_via == "alias"


def test_a_curated_floating_alias_resolves() -> None:
    """chatgpt-4o-latest is tracked as its own verified registry entry — a legitimate
    "-latest"-suffixed id that resolves because we've actually curated it, not because the
    resolver is guessing what "-latest" currently points to."""
    result = resolve("chatgpt-4o-latest", make_registry())
    assert isinstance(result, Resolved)
    assert result.entry.canonical_id == "chatgpt-4o-latest"


def test_an_uncurated_floating_alias_is_unknown_not_fuzzy_matched() -> None:
    """CLAUDE_CODE_PLAN.md Session 4: 'Floating aliases like -latest are the common case. Test
    that explicitly.' claude-3-opus-latest is NOT a curated entry or alias — it must resolve to
    Unknown, never accidentally match claude-3-opus-20240229 via prefix/fuzzy matching."""
    result = resolve("claude-3-opus-latest", make_registry())
    assert isinstance(result, Unknown)
    assert result.raw_text == "claude-3-opus-latest"


def test_unrelated_text_is_unknown() -> None:
    result = resolve("some-internal-tool-name", make_registry())
    assert isinstance(result, Unknown)


def test_unresolvable_is_unknown_never_clear() -> None:
    """SUITE_ARCHITECTURE.md §3: 'unknown is a verdict, not the absence of one.' There is no
    'this model is fine' result here — only Resolved (we know its status) or Unknown (we
    don't). A caller must never treat Unknown as equivalent to verified-safe."""
    result = resolve("gpt-4o-mini", make_registry())
    assert isinstance(result, Unknown)
