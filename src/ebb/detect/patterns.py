import re

# Structural patterns, not an enumerated list: DEC-06 (specs/ebb.md §1) commits to three
# providers "deeply correct" at launch — OpenAI, Anthropic, Google. Each pattern matches the
# provider's naming *shape* (including older `claude-3-opus-20240229`-style and newer
# `claude-opus-4-8`-style Anthropic ids — both conventions exist in the wild) so a model
# released after this file was written still matches, without needing a code change. This is
# deliberately looser than the versioned registry (Session 4), which pins exact known-valid ids
# with source_url/verified_at; Slice 1 only needs "shaped like a model identifier".
# OpenAI dates ship two conventions: a full ISO date (`-2024-05-13`) and a bare 4-digit code,
# optionally trailed by `-preview` (`-0125`, `-1106-preview`) — both need to be optional and
# tried in this order so the longer ISO form isn't shadowed by the shorter one matching a
# prefix of it.
_OPENAI_DATE_SUFFIX = r"(?:-\d{4}-\d{2}-\d{2}|-\d{4}(?:-preview)?)"
# `4\.\d+` (gpt-4.1, gpt-4.1-mini) must come before bare `4` in the alternation: alternatives
# are tried in order and the first one that lets the overall match succeed wins, so with `4`
# first, "gpt-4.1" would match only "gpt-4" and silently drop the ".1" that makes it a
# different, real model. Found via the Session 7 golden corpus, not guessed.
_OPENAI = (
    r"\bgpt-(?:4o|4\.\d+|4|3\.5|5(?:\.\d+)?)(?:-turbo|-mini|-nano)?" + _OPENAI_DATE_SUFFIX + r"?\b"
)
_OPENAI_O_SERIES = r"\bo[134](?:-preview|-mini|-pro)?" + _OPENAI_DATE_SUFFIX + r"?\b"
_OPENAI_EMBEDDING = r"\btext-embedding-(?:ada-002|3-small|3-large)\b"
_OPENAI_OTHER = r"\b(?:dall-e-[23]|whisper-1)\b"

_ANTHROPIC_DATED = (
    r"\bclaude-\d(?:[.-]\d)?(?:-(?:opus|sonnet|haiku|instant))?(?:-\d{8})?(?:-latest)?\b"
)
# Tier-before-version: covers both the old `claude-instant-1.2` (dotted) and the current
# `claude-opus-4-8` / `claude-haiku-4-5-20251001` (hyphenated) conventions.
_ANTHROPIC_NAMED = r"\bclaude-(?:opus|sonnet|haiku|fable|instant)-\d+(?:[.-]\d+)?(?:-\d{8})?\b"

_GOOGLE_GEMINI = (
    r"\bgemini-\d(?:\.\d)?(?:-pro|-flash|-ultra)?(?:-vision)?(?:-\d{3})?(?:-preview|-exp)?\b"
)
_GOOGLE_BISON = r"\b(?:text|chat)-bison(?:-00[12])?\b"

MODEL_ID_PATTERN = re.compile(
    "|".join(
        [
            _OPENAI,
            _OPENAI_O_SERIES,
            _OPENAI_EMBEDDING,
            _OPENAI_OTHER,
            _ANTHROPIC_DATED,
            _ANTHROPIC_NAMED,
            _GOOGLE_GEMINI,
            _GOOGLE_BISON,
        ]
    )
)
