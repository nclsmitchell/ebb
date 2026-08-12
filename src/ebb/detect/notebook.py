import json
from pathlib import Path

from ebb.detect.base import RawMatch
from ebb.detect.scan_text import scan_lines


def detect(path: Path, content: str) -> list[RawMatch]:
    """Scans every cell's source (code and markdown alike — a model id in a doc cell is still
    worth surfacing; ranking it belongs to later sessions, not detection). A notebook that
    fails to parse as JSON yields no matches rather than crashing the walk — one malformed
    .ipynb must never take down a scan of the other 499 files in the repo."""
    try:
        notebook = json.loads(content)
    except json.JSONDecodeError:
        return []

    matches: list[RawMatch] = []
    for cell in notebook.get("cells", []):
        source = cell.get("source", "")
        cell_text = source if isinstance(source, str) else "".join(source)
        # Line numbers are cell-relative, not file-relative — a notebook has no single
        # meaningful line axis across cells. Informational only, as everywhere in Slice 1.
        matches.extend(scan_lines(path, cell_text))
    return matches
