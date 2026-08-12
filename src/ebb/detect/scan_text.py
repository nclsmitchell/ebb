import re
from pathlib import Path

from ebb.detect.base import RawMatch
from ebb.detect.patterns import MODEL_ID_PATTERN

# The identifier immediately before the nearest '=' or ':' preceding a match on its own line —
# covers Python/TypeScript assignments (MODEL = "..."), JSON/YAML/TOML keys ("model": "...",
# model: ...), and Dockerfile ENV/ARG forms (ENV MODEL=...). Language-agnostic on purpose: a
# real per-language symbol table (AST-scoped to the enclosing function/class) would be far more
# precise, but is a much bigger undertaking than this session's scope — this heuristic is
# "good enough to keep identity stable across reformatting," which is the actual requirement
# (SUITE_ARCHITECTURE.md §3.1), not "semantically perfect."
_ASSIGNMENT_PATTERN = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)[\"']?\s*[:=]")
_MAX_FALLBACK_SYMBOL_LENGTH = 40


def nearest_symbol(line: str, match_start: int) -> str:
    """Never empty: falls back to a bounded prefix of the line itself (e.g. a bare string in a
    list has no assignment to name it), and finally to "unknown" for a blank line — every match
    gets a stable, non-empty symbol so identity never depends on an absent one."""
    prefix = line[:match_start]
    candidates = list(_ASSIGNMENT_PATTERN.finditer(prefix))
    if candidates:
        return candidates[-1].group(1)
    stripped = line.strip()
    return stripped[:_MAX_FALLBACK_SYMBOL_LENGTH] if stripped else "unknown"


def scan_lines(path: Path, content: str) -> list[RawMatch]:
    """Line-oriented regex scan shared by every format where a model id appears as plain text
    inside otherwise-structured content (source code, YAML/TOML/JSON values, Terraform,
    Dockerfiles). One RawMatch per occurrence — no dedup here, that's identity's job later
    (SUITE_ARCHITECTURE.md §3.1), not the raw-match layer's."""
    matches: list[RawMatch] = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        for m in MODEL_ID_PATTERN.finditer(line):
            matches.append(
                RawMatch(
                    path=path,
                    line=lineno,
                    matched_text=m.group(0),
                    symbol=nearest_symbol(line, m.start()),
                )
            )
    return matches
