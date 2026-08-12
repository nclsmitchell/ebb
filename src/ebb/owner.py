import subprocess
from pathlib import Path

import pathspec
from pathspec.pattern import Pattern

_CodeownersSpec = pathspec.PathSpec[Pattern]

# GitHub looks for CODEOWNERS in any of these three locations, root first.
_CODEOWNERS_LOCATIONS = ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS")


def _find_codeowners_file(repo_root: Path) -> Path | None:
    for rel in _CODEOWNERS_LOCATIONS:
        candidate = repo_root / rel
        if candidate.is_file():
            return candidate
    return None


def _parse_codeowners(content: str) -> list[tuple[_CodeownersSpec, list[str]]]:
    # CODEOWNERS pattern syntax is documented by GitHub as "most of the same rules used for
    # .gitignore files" — reusing pathspec's gitignore matching here, same as walk.py's
    # nested-.gitignore handling, rather than reimplementing the same glob semantics twice.
    rules: list[tuple[_CodeownersSpec, list[str]]] = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pattern, *owners = line.split()
        if not owners:
            continue
        rules.append((pathspec.PathSpec.from_lines("gitignore", [pattern]), owners))
    return rules


def owners_from_codeowners(path: Path, repo_root: Path) -> list[str] | None:
    """The last matching rule in the file wins — this is GitHub's own documented CODEOWNERS
    precedence (more specific / later rules override earlier ones), same direction as the
    nested-.gitignore precedence in walk.py but expressed as file order rather than directory
    depth, since CODEOWNERS is a single flat file."""
    codeowners_path = _find_codeowners_file(repo_root)
    if codeowners_path is None:
        return None

    rules = _parse_codeowners(codeowners_path.read_text(encoding="utf-8"))
    rel = str(path.resolve().relative_to(repo_root.resolve()))

    matched: list[str] | None = None
    for spec, owners in rules:
        if spec.match_file(rel):
            matched = owners
    return matched


def owner_via_git_blame(path: Path, line: int, repo_root: Path) -> str | None:
    """Fallback when no CODEOWNERS rule matches: the email of whoever last touched this exact
    line, via `git blame`. Returns None (never raises) if the path isn't in a git repo, has no
    history, or git isn't available — a missing owner is a legitimate, common outcome, not an
    error."""
    try:
        result = subprocess.run(
            ["git", "blame", "-L", f"{line},{line}", "--porcelain", "--", str(path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    for out_line in result.stdout.splitlines():
        if out_line.startswith("author-mail "):
            return out_line.removeprefix("author-mail ").strip("<>")
    return None


def find_owner(path: Path, line: int, repo_root: Path) -> str | None:
    """CODEOWNERS first (an explicit, human-declared ownership decision beats inferred
    history), git blame as fallback. Per specs/ebb.md §2.2: 'Each hit is attributed to an
    owner via CODEOWNERS, then git blame as fallback.'"""
    owners = owners_from_codeowners(path, repo_root)
    if owners:
        return owners[0]
    return owner_via_git_blame(path, line, repo_root)
