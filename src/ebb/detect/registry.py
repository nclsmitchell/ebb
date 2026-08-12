from pathlib import Path

from ebb.detect import dockerfile, json_format, notebook, python, terraform, toml, typescript, yaml
from ebb.detect.base import Detector

_BY_EXTENSION: dict[str, Detector] = {
    ".py": python.detect,
    ".ts": typescript.detect,
    ".tsx": typescript.detect,
    ".yml": yaml.detect,
    ".yaml": yaml.detect,
    ".toml": toml.detect,
    ".json": json_format.detect,
    ".tf": terraform.detect,
    ".ipynb": notebook.detect,
}


def get_detector(path: Path) -> Detector | None:
    """Adding a language: add one file under detect/, one entry here (or one more filename
    rule below for extension-less formats), and one fixture under tests/fixtures/. Nothing
    else in the walker or CLI needs to change."""
    if path.name == "Dockerfile" or path.name.startswith("Dockerfile."):
        return dockerfile.detect
    return _BY_EXTENSION.get(path.suffix)
