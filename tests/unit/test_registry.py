from pathlib import Path

from ebb.detect import dockerfile, json_format, notebook, python, terraform, toml, typescript, yaml
from ebb.detect.registry import get_detector


def test_resolves_every_registered_extension() -> None:
    assert get_detector(Path("app.py")) is python.detect
    assert get_detector(Path("app.ts")) is typescript.detect
    assert get_detector(Path("app.tsx")) is typescript.detect
    assert get_detector(Path("config.yml")) is yaml.detect
    assert get_detector(Path("config.yaml")) is yaml.detect
    assert get_detector(Path("pyproject.toml")) is toml.detect
    assert get_detector(Path("settings.json")) is json_format.detect
    assert get_detector(Path("main.tf")) is terraform.detect
    assert get_detector(Path("analysis.ipynb")) is notebook.detect


def test_resolves_dockerfile_by_exact_and_prefixed_name() -> None:
    assert get_detector(Path("Dockerfile")) is dockerfile.detect
    assert get_detector(Path("Dockerfile.prod")) is dockerfile.detect
    assert get_detector(Path("some/dir/Dockerfile")) is dockerfile.detect


def test_returns_none_for_unregistered_extensions() -> None:
    assert get_detector(Path("README.md")) is None
    assert get_detector(Path("photo.png")) is None
    assert get_detector(Path("no_extension")) is None
