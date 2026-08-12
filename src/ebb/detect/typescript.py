from pathlib import Path

from ebb.detect.base import RawMatch
from ebb.detect.scan_text import scan_lines


def detect(path: Path, content: str) -> list[RawMatch]:
    return scan_lines(path, content)
