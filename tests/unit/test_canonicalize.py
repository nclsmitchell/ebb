import pytest

from ebb.canonicalize import canonicalize


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # The literal example from AWS Bedrock's own inference-profiles-support docs.
        ("us.anthropic.claude-3-haiku-20240307-v1:0", "claude-3-haiku-20240307"),
        ("eu.anthropic.claude-3-5-sonnet-20241022-v2:0", "claude-3-5-sonnet-20241022"),
        ("apac.anthropic.claude-3-5-sonnet-20241022-v2:0", "claude-3-5-sonnet-20241022"),
        # Plain (non-cross-region) Bedrock model id: vendor prefix, no region prefix.
        ("anthropic.claude-3-5-sonnet-20241022-v2:0", "claude-3-5-sonnet-20241022"),
        # GCP Vertex AI publisher-model resource paths, short and fully-qualified.
        ("publishers/anthropic/models/claude-3-opus", "claude-3-opus"),
        (
            "projects/my-proj/locations/us-central1/publishers/google/models/gemini-1.5-pro",
            "gemini-1.5-pro",
        ),
        # Vertex AI's @version suffix.
        ("gemini-1.5-pro@001", "gemini-1.5-pro"),
        ("publishers/google/models/gemini-1.5-pro@001", "gemini-1.5-pro"),
        # Already-canonical ids pass through unchanged.
        ("claude-3-opus-20240229", "claude-3-opus-20240229"),
        ("gpt-4-turbo-2024-04-09", "gpt-4-turbo-2024-04-09"),
    ],
)
def test_known_wrapper_forms_collapse_to_the_bare_id(raw: str, expected: str) -> None:
    assert canonicalize(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        # A curated whole registry entry (src/ebb/registries/retirements/openai.yaml) — must survive
        # untouched, or it stops matching its own registry entry.
        "chatgpt-4o-latest",
        # An uncurated floating alias — still not a canonical id after canonicalization, and
        # that's correct: canonicalize() has no way to know what "-latest" currently points to,
        # and must not guess. resolve() (Session 4) is what turns this into Unknown.
        "claude-3-opus-latest",
    ],
)
def test_latest_style_suffixes_are_never_stripped(raw: str) -> None:
    assert canonicalize(raw) == raw


def test_idempotent_on_already_canonicalized_wrapper_forms() -> None:
    once = canonicalize("us.anthropic.claude-3-haiku-20240307-v1:0")
    twice = canonicalize(once)
    assert once == twice == "claude-3-haiku-20240307"
