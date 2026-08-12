import pytest

from ebb.detect.patterns import MODEL_ID_PATTERN


@pytest.mark.parametrize(
    "text",
    [
        "gpt-4-turbo-2024-04-09",
        "gpt-4o-mini",
        "gpt-3.5-turbo",
        "o1-preview",
        "o1-mini-2024-09-12",
        "text-embedding-3-large",
        "text-embedding-ada-002",
        "dall-e-3",
        "whisper-1",
        "claude-3-opus-20240229",
        "claude-3-5-sonnet-20241022",
        "claude-2.1",
        "claude-instant-1.2",
        "claude-opus-4-8",
        "claude-sonnet-5",
        "claude-haiku-4-5-20251001",
        "gemini-1.5-pro",
        "gemini-1.0-pro-vision",
        "text-bison-001",
        "chat-bison",
    ],
)
def test_known_model_ids_match(text: str) -> None:
    assert MODEL_ID_PATTERN.search(text) is not None


@pytest.mark.parametrize(
    "text",
    [
        "gpt-nonsense",
        "banana-3-5-sonnet",
        "just some prose about language models",
        "version-4-turbo",
        "def gpt_helper(): pass",  # underscore, not a model id shape
    ],
)
def test_unrelated_strings_do_not_match(text: str) -> None:
    assert MODEL_ID_PATTERN.search(text) is None
