from collections.abc import Iterator
from pathlib import Path

import pathspec
from pathspec.pattern import Pattern

from ebb.detect.base import RawMatch
from ebb.detect.registry import get_detector

_GitignoreSpec = pathspec.PathSpec[Pattern]

MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB, per CLAUDE_CODE_PLAN.md Session 3
_SNIFF_BYTES = 8192

# Common binary format signatures. This plus the null-byte fallback in is_binary() below is
# the same heuristic git itself uses to decide "is this file binary" — real magic-byte
# sniffing (libmagic) would need a system dependency this repo doesn't otherwise need.
_BINARY_SIGNATURES: tuple[bytes, ...] = (
    b"\x89PNG\r\n\x1a\n",
    b"\xff\xd8\xff",  # JPEG
    b"GIF87a",
    b"GIF89a",
    b"PK\x03\x04",  # ZIP / JAR / DOCX / XLSX / ...
    b"PK\x05\x06",  # empty ZIP
    b"%PDF-",
    b"\x7fELF",
    b"\x1f\x8b\x08",  # gzip
    b"\xca\xfe\xba\xbe",  # Mach-O fat binary / Java class
    b"\x00\x00\x01\x00",  # ICO
)


def is_binary(sample: bytes) -> bool:
    if any(sample.startswith(sig) for sig in _BINARY_SIGNATURES):
        return True
    return b"\x00" in sample


def _load_gitignore(directory: Path) -> _GitignoreSpec | None:
    gitignore = directory / ".gitignore"
    if not gitignore.is_file():
        return None
    try:
        lines = gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None
    return pathspec.PathSpec.from_lines("gitignore", lines)


def _is_ignored(entry: Path, is_dir: bool, specs: list[tuple[Path, _GitignoreSpec]]) -> bool:
    # Deepest (nearest-ancestor) gitignore checked first, matching git's own precedence: a
    # nested .gitignore's rules for paths under it win over an outer one's.
    for base, spec in reversed(specs):
        rel = str(entry.relative_to(base))
        if is_dir:
            rel += "/"
        if spec.match_file(rel):
            return True
    return False


def iter_files(root: Path) -> Iterator[Path]:
    """Streaming, gitignore-aware file discovery. Yields one path at a time — never builds a
    list of the whole tree. `.git/` is always skipped; nested `.gitignore` files are honoured
    with rules scoped to their own subtree."""
    root = root.resolve()

    def walk(directory: Path, specs: list[tuple[Path, _GitignoreSpec]]) -> Iterator[Path]:
        own_spec = _load_gitignore(directory)
        if own_spec is not None:
            specs = [*specs, (directory, own_spec)]

        try:
            entries = sorted(directory.iterdir())
        except OSError:
            return

        for entry in entries:
            if entry.name == ".git":
                continue
            is_dir = entry.is_dir()
            if _is_ignored(entry, is_dir, specs):
                continue
            if is_dir:
                yield from walk(entry, specs)
            elif entry.is_file():
                yield entry

    yield from walk(root, [])


def scan_repo(root: Path) -> Iterator[RawMatch]:
    """Walks `root` and runs every registered detector against every file it applies to.
    Streaming end to end: one file's bytes exist in memory at a time, never the whole tree."""
    for path in iter_files(root):
        detector = get_detector(path)
        if detector is None:
            continue

        try:
            if path.stat().st_size > MAX_FILE_SIZE_BYTES:
                continue
            raw = path.read_bytes()
        except OSError:
            continue

        if is_binary(raw[:_SNIFF_BYTES]):
            continue

        content = raw.decode("utf-8", errors="replace")
        yield from detector(path, content)
