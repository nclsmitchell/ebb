import subprocess
from pathlib import Path

from ebb.owner import find_owner, owner_via_git_blame, owners_from_codeowners


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_returns_none_when_no_codeowners_file_exists(tmp_path: Path) -> None:
    write(tmp_path / "app.py", "x = 1\n")
    assert owners_from_codeowners(tmp_path / "app.py", tmp_path) is None


def test_matches_a_simple_pattern(tmp_path: Path) -> None:
    write(tmp_path / "CODEOWNERS", "*.py @python-team\n")
    write(tmp_path / "app.py", "x = 1\n")
    assert owners_from_codeowners(tmp_path / "app.py", tmp_path) == ["@python-team"]


def test_supports_multiple_owners_on_one_rule(tmp_path: Path) -> None:
    write(tmp_path / "CODEOWNERS", "*.py @owner-one @owner-two\n")
    write(tmp_path / "app.py", "x = 1\n")
    assert owners_from_codeowners(tmp_path / "app.py", tmp_path) == ["@owner-one", "@owner-two"]


def test_later_rule_wins_over_an_earlier_broader_one(tmp_path: Path) -> None:
    write(
        tmp_path / "CODEOWNERS",
        "*.py @python-team\napps/ebb/*.py @ebb-team\n",
    )
    write(tmp_path / "apps" / "ebb" / "cli.py", "x = 1\n")
    owners = owners_from_codeowners(tmp_path / "apps" / "ebb" / "cli.py", tmp_path)
    assert owners == ["@ebb-team"]


def test_comments_and_blank_lines_are_ignored(tmp_path: Path) -> None:
    write(tmp_path / "CODEOWNERS", "# a comment\n\n*.py @python-team\n")
    write(tmp_path / "app.py", "x = 1\n")
    assert owners_from_codeowners(tmp_path / "app.py", tmp_path) == ["@python-team"]


def test_finds_codeowners_under_dot_github(tmp_path: Path) -> None:
    write(tmp_path / ".github" / "CODEOWNERS", "*.py @python-team\n")
    write(tmp_path / "app.py", "x = 1\n")
    assert owners_from_codeowners(tmp_path / "app.py", tmp_path) == ["@python-team"]


def test_a_file_with_no_matching_rule_returns_none(tmp_path: Path) -> None:
    write(tmp_path / "CODEOWNERS", "*.ts @web-team\n")
    write(tmp_path / "app.py", "x = 1\n")
    assert owners_from_codeowners(tmp_path / "app.py", tmp_path) is None


def _init_git_repo_with_one_commit(
    repo: Path, filename: str, content: str, author_email: str
) -> None:
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test Author"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", author_email], cwd=repo, check=True)
    write(repo / filename, content)
    subprocess.run(["git", "add", filename], cwd=repo, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "add file"], cwd=repo, check=True)


def test_git_blame_finds_the_commit_authors_email(tmp_path: Path) -> None:
    _init_git_repo_with_one_commit(
        tmp_path, "app.py", "MODEL = 'gpt-4o-mini'\n", "author@example.com"
    )
    owner = owner_via_git_blame(tmp_path / "app.py", 1, tmp_path)
    assert owner == "author@example.com"


def test_git_blame_returns_none_outside_a_git_repo(tmp_path: Path) -> None:
    write(tmp_path / "app.py", "x = 1\n")
    assert owner_via_git_blame(tmp_path / "app.py", 1, tmp_path) is None


def test_find_owner_prefers_codeowners_over_git_blame(tmp_path: Path) -> None:
    _init_git_repo_with_one_commit(
        tmp_path, "app.py", "MODEL = 'gpt-4o-mini'\n", "blame-author@example.com"
    )
    write(tmp_path / "CODEOWNERS", "*.py @declared-owner\n")

    owner = find_owner(tmp_path / "app.py", 1, tmp_path)

    assert owner == "@declared-owner"


def test_find_owner_falls_back_to_git_blame_without_codeowners(tmp_path: Path) -> None:
    _init_git_repo_with_one_commit(
        tmp_path, "app.py", "MODEL = 'gpt-4o-mini'\n", "blame-author@example.com"
    )

    owner = find_owner(tmp_path / "app.py", 1, tmp_path)

    assert owner == "blame-author@example.com"


def test_find_owner_returns_none_when_neither_source_has_an_answer(tmp_path: Path) -> None:
    write(tmp_path / "app.py", "x = 1\n")
    assert find_owner(tmp_path / "app.py", 1, tmp_path) is None
