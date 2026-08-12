import json
from pathlib import Path

from typer.testing import CliRunner

from ebb.cli import app

runner = CliRunner()


def make_registry_dir(tmp_path: Path) -> Path:
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    (registry_dir / "openai.yaml").write_text(
        """
        - canonical_id: gpt-4-turbo
          provider: openai
          shutdown_at: 2020-01-01
          source_url: https://developers.openai.com/api/docs/deprecations
          verified_at: 2026-08-12
        """
    )
    return registry_dir


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text('MODEL = "gpt-4-turbo"\n')
    return repo


def test_default_table_format_exits_zero(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    registry_dir = make_registry_dir(tmp_path)

    result = runner.invoke(app, ["scan", str(repo), "--registry-dir", str(registry_dir)])

    assert result.exit_code == 0
    assert "gpt-4-turbo" in result.stdout
    assert "1 finding(s)" in result.stdout


def test_json_format_is_valid_json(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    registry_dir = make_registry_dir(tmp_path)

    result = runner.invoke(
        app, ["scan", str(repo), "--format", "json", "--registry-dir", str(registry_dir)]
    )

    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert len(parsed) == 1
    assert parsed[0]["subject"] == "gpt-4-turbo"
    assert parsed[0]["verdict"] == "break"


def test_annotations_format_emits_a_github_workflow_command(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    registry_dir = make_registry_dir(tmp_path)

    result = runner.invoke(
        app, ["scan", str(repo), "--format", "annotations", "--registry-dir", str(registry_dir)]
    )

    assert result.exit_code == 0
    assert "::error file=app.py,line=1,title=ebb%3A gpt-4-turbo (break)::" in result.stdout


def test_unknown_format_exits_2_not_0_or_1(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    registry_dir = make_registry_dir(tmp_path)

    result = runner.invoke(
        app, ["scan", str(repo), "--format", "bogus", "--registry-dir", str(registry_dir)]
    )

    assert result.exit_code == 2


def test_fail_on_exits_1_when_a_finding_meets_the_threshold(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    registry_dir = make_registry_dir(tmp_path)

    result = runner.invoke(
        app,
        ["scan", str(repo), "--fail-on", "critical", "--registry-dir", str(registry_dir)],
    )

    assert result.exit_code == 1


def test_fail_on_exits_0_when_no_finding_meets_the_threshold(tmp_path: Path) -> None:
    repo = tmp_path / "clean-repo"
    repo.mkdir()
    (repo / "app.py").write_text("x = 1\n")  # no model references at all
    registry_dir = make_registry_dir(tmp_path)

    result = runner.invoke(
        app,
        ["scan", str(repo), "--fail-on", "critical", "--registry-dir", str(registry_dir)],
    )

    assert result.exit_code == 0


def test_unknown_fail_on_value_exits_2(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    registry_dir = make_registry_dir(tmp_path)

    result = runner.invoke(
        app,
        ["scan", str(repo), "--fail-on", "extremely-critical", "--registry-dir", str(registry_dir)],
    )

    assert result.exit_code == 2


def test_a_registry_dir_with_no_yaml_files_still_runs_everything_resolves_unknown(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path)
    empty_registry_dir = tmp_path / "empty"
    empty_registry_dir.mkdir()

    result = runner.invoke(app, ["scan", str(repo), "--registry-dir", str(empty_registry_dir)])

    assert result.exit_code == 0
    assert "unknown" in result.stdout
