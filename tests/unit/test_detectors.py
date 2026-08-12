from pathlib import Path

from ebb.detect import dockerfile, json_format, notebook, python, terraform, toml, typescript, yaml


def test_python_detector_finds_a_match() -> None:
    matches = python.detect(Path("app.py"), 'MODEL = "gpt-4o-mini"\n')
    assert [m.matched_text for m in matches] == ["gpt-4o-mini"]
    assert matches[0].line == 1


def test_typescript_detector_finds_a_match() -> None:
    matches = typescript.detect(Path("app.ts"), 'const MODEL = "claude-3-opus-20240229";\n')
    assert [m.matched_text for m in matches] == ["claude-3-opus-20240229"]


def test_yaml_detector_finds_a_match() -> None:
    matches = yaml.detect(Path("config.yaml"), "model: gemini-1.5-pro\n")
    assert [m.matched_text for m in matches] == ["gemini-1.5-pro"]


def test_toml_detector_finds_a_match() -> None:
    matches = toml.detect(Path("pyproject.toml"), 'model = "gpt-3.5-turbo"\n')
    assert [m.matched_text for m in matches] == ["gpt-3.5-turbo"]


def test_json_detector_finds_a_match() -> None:
    matches = json_format.detect(Path("settings.json"), '{"model": "text-embedding-3-large"}\n')
    assert [m.matched_text for m in matches] == ["text-embedding-3-large"]


def test_terraform_detector_finds_a_match() -> None:
    matches = terraform.detect(Path("main.tf"), 'default = "claude-3-haiku-20240307"\n')
    assert [m.matched_text for m in matches] == ["claude-3-haiku-20240307"]


def test_dockerfile_detector_finds_a_match() -> None:
    matches = dockerfile.detect(Path("Dockerfile"), "ENV MODEL=o1-preview\n")
    assert [m.matched_text for m in matches] == ["o1-preview"]


def test_notebook_detector_scans_code_and_markdown_cells() -> None:
    content = """
    {
      "cells": [
        {"cell_type": "markdown", "source": ["See `text-bison-001` for baseline."]},
        {"cell_type": "code", "source": ["model = \\"gemini-1.0-pro\\"\\n"]}
      ]
    }
    """
    matches = notebook.detect(Path("nb.ipynb"), content)
    assert {m.matched_text for m in matches} == {"text-bison-001", "gemini-1.0-pro"}


def test_notebook_detector_degrades_on_invalid_json_instead_of_raising() -> None:
    assert notebook.detect(Path("broken.ipynb"), "{not valid json") == []


def test_no_detector_matches_when_content_has_no_model_ids() -> None:
    assert python.detect(Path("empty.py"), "x = 1\n") == []
