from pathlib import Path

from ebb.walk import scan_repo

FIXTURE_REPO = Path(__file__).parent / "fixtures" / "acceptance_repo"

EXPECTED_MATCHES = {
    "gpt-4-turbo-2024-04-09",
    "claude-3-5-sonnet-20241022",
    "o1-preview",
    "gpt-4o-mini",
    "claude-3-5-haiku-20241022",
    "gemini-1.5-pro",
    "claude-3-opus-20240229",
    "text-embedding-3-large",
    "claude-3-haiku-20240307",
    "gpt-3.5-turbo",
    "text-bison-001",
    "gemini-1.0-pro",
}


def test_acceptance_repo_yields_exactly_the_twelve_known_references() -> None:
    """CLAUDE_CODE_PLAN.md Session 3's acceptance test: a fixture repository with 12 known
    references yields exactly those 12 — one per format (Python, TypeScript, YAML, TOML,
    JSON, Terraform, Dockerfile, notebook), plus decoys proving gitignore (root and nested)
    and binary-file skipping actually exclude what they're supposed to."""
    matches = list(scan_repo(FIXTURE_REPO))

    assert len(matches) == len(EXPECTED_MATCHES) == 12
    assert {m.matched_text for m in matches} == EXPECTED_MATCHES

    scanned_paths = {m.path.relative_to(FIXTURE_REPO) for m in matches}
    assert not any("vendor" in p.parts for p in scanned_paths), "root .gitignore not honoured"
    assert not any("dist" in p.parts for p in scanned_paths), "nested .gitignore not honoured"
    assert not any(p.name == "logo.png" for p in scanned_paths), "binary file not skipped"
