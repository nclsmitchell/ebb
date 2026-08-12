from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RawMatch:
    """One model-identifier-shaped string found in a file.

    Line numbers exist for human-readable output only — per SUITE_ARCHITECTURE.md §3.1, line
    numbers must never enter finding identity. `symbol` is the "normalized surrounding symbol"
    identity actually uses instead: the identifier immediately governing the matched text (an
    assignment target, a JSON/YAML/TOML key, a Dockerfile ENV/ARG name), captured at detection
    time since that's when the full line text is already in hand. See
    ebb.detect.scan_text.nearest_symbol for exactly what "normalized" means here.
    """

    path: Path
    line: int
    matched_text: str
    symbol: str


class Detector(Protocol):
    """A pure function `(path, content) -> list[RawMatch]`. No I/O, no side effects — the
    walker reads file content once and hands it to every detector registered for that file's
    kind. Adding a language means adding one detector and registering it in registry.py."""

    def __call__(self, path: Path, content: str) -> list[RawMatch]: ...
